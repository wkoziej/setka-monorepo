//! Server-side path validation for IPC commands.
//!
//! The frontend is untrusted: any command reachable via `invoke` can be called
//! with arbitrary arguments, so a `recording_name` like `../../etc/passwd` or an
//! absolute path must never be allowed to escape the recordings root. These
//! helpers resolve names *relative to the canonicalized recordings root* and
//! reject traversal lexically before any filesystem op, then re-assert
//! containment after canonicalization to defend against symlink escapes.

use std::path::{Component, Path, PathBuf};

/// Validate that `name` is a single, safe path component.
///
/// Rejects empty strings, `.`/`..`, anything containing a path separator, and
/// absolute or prefix (Windows drive) components — i.e. anything that is not a
/// plain `Component::Normal` single segment.
fn validate_component(name: &str) -> Result<(), String> {
    if name.is_empty() {
        return Err("Recording name cannot be empty".to_string());
    }

    // Reject separators outright so e.g. "a/b" or "a\\b" never slip through.
    if name.contains('/') || name.contains('\\') {
        return Err(format!("Invalid recording name (path separators not allowed): {}", name));
    }

    let mut comps = Path::new(name).components();
    match (comps.next(), comps.next()) {
        // Exactly one Normal component and nothing else.
        (Some(Component::Normal(c)), None) if c == std::ffi::OsStr::new(name) => Ok(()),
        _ => Err(format!("Invalid recording name (path traversal rejected): {}", name)),
    }
}

/// Resolve a recording directory under `recordings_root`, rejecting traversal.
///
/// The recording must already exist (delete / details / video playback all
/// operate on existing recordings). Returns the canonicalized directory, which
/// is guaranteed to live inside the canonicalized `recordings_root`.
pub fn resolve_recording_dir(recordings_root: &Path, name: &str) -> Result<PathBuf, String> {
    validate_component(name)?;

    let canonical_root = recordings_root
        .canonicalize()
        .map_err(|e| format!("Recordings root unavailable: {}", e))?;

    let candidate = canonical_root.join(name);
    let canonical = candidate
        .canonicalize()
        .map_err(|_| format!("Recording '{}' not found", name))?;

    if !canonical.starts_with(&canonical_root) {
        return Err(format!("Invalid recording name (escapes recordings root): {}", name));
    }

    Ok(canonical)
}

/// Resolve a *target* recording directory that does NOT yet exist (e.g. the new
/// name in a rename). Validates the component and that the lexical join stays
/// under the canonicalized root, without requiring the path to exist.
pub fn resolve_new_recording_dir(recordings_root: &Path, name: &str) -> Result<PathBuf, String> {
    validate_component(name)?;

    let canonical_root = recordings_root
        .canonicalize()
        .map_err(|e| format!("Recordings root unavailable: {}", e))?;

    // `name` is a validated single Normal component, so the join cannot escape.
    Ok(canonical_root.join(name))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn root_with(name: &str) -> (TempDir, PathBuf) {
        let tmp = TempDir::new().unwrap();
        let rec = tmp.path().join(name);
        fs::create_dir_all(&rec).unwrap();
        (tmp, rec)
    }

    #[test]
    fn validate_component_accepts_plain_names() {
        assert!(validate_component("stream_20240115_120000").is_ok());
        assert!(validate_component("my recording").is_ok());
    }

    #[test]
    fn validate_component_rejects_traversal_and_separators() {
        assert!(validate_component("..").is_err());
        assert!(validate_component(".").is_err());
        assert!(validate_component("").is_err());
        assert!(validate_component("../../etc/passwd").is_err());
        assert!(validate_component("a/b").is_err());
        assert!(validate_component("a\\b").is_err());
        assert!(validate_component("/etc/passwd").is_err());
    }

    #[test]
    fn resolve_recording_dir_happy_path() {
        let (tmp, _rec) = root_with("rec1");
        let resolved = resolve_recording_dir(tmp.path(), "rec1").unwrap();
        assert!(resolved.ends_with("rec1"));
        assert!(resolved.starts_with(tmp.path().canonicalize().unwrap()));
    }

    #[test]
    fn resolve_recording_dir_rejects_traversal() {
        let (tmp, _rec) = root_with("rec1");
        assert!(resolve_recording_dir(tmp.path(), "../../etc/passwd").is_err());
        assert!(resolve_recording_dir(tmp.path(), "..").is_err());
        // Absolute path embedded as the "name".
        assert!(resolve_recording_dir(tmp.path(), "/etc/passwd").is_err());
    }

    #[test]
    fn resolve_recording_dir_rejects_missing() {
        let (tmp, _rec) = root_with("rec1");
        assert!(resolve_recording_dir(tmp.path(), "does_not_exist").is_err());
    }

    #[test]
    fn resolve_recording_dir_rejects_symlink_escape() {
        // A symlink inside the root pointing outside must not pass containment.
        let tmp = TempDir::new().unwrap();
        let outside = TempDir::new().unwrap();
        let outside_secret = outside.path().join("secret");
        fs::create_dir_all(&outside_secret).unwrap();

        #[cfg(unix)]
        {
            let link = tmp.path().join("evil");
            std::os::unix::fs::symlink(&outside_secret, &link).unwrap();
            // Canonicalization follows the symlink out of the root → rejected.
            assert!(resolve_recording_dir(tmp.path(), "evil").is_err());
        }
    }

    #[test]
    fn resolve_new_recording_dir_allows_nonexistent_but_blocks_traversal() {
        let tmp = TempDir::new().unwrap();
        let ok = resolve_new_recording_dir(tmp.path(), "brand_new").unwrap();
        assert!(ok.ends_with("brand_new"));
        assert!(resolve_new_recording_dir(tmp.path(), "../escape").is_err());
        assert!(resolve_new_recording_dir(tmp.path(), "a/b").is_err());
    }
}
