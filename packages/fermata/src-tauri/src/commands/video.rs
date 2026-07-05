use crate::commands::recordings::AppConfig;
use base64::Engine;
use std::path::{Path, PathBuf};
use std::process::Command;
use tauri::State;

/// Resolve the best playable video file for a recording directory.
///
/// Priority: a rendered `blender/render/*final.mp4`, then a video file whose
/// stem matches the recording name, then any video file in the recording root.
fn resolve_video_path(recording_path: &Path, recording_name: &str) -> Result<String, String> {
    // Priority 1: Check for rendered final.mp4 or *_final.mp4
    let render_dir = recording_path.join("blender").join("render");
    if render_dir.exists() {
        if let Ok(entries) = std::fs::read_dir(&render_dir) {
            for entry in entries.flatten() {
                let file_path = entry.path();
                if file_path.is_file() {
                    if let Some(file_name) = file_path.file_name().and_then(|n| n.to_str()) {
                        if file_name == "final.mp4" || file_name.ends_with("_final.mp4") {
                            return Ok(file_path.to_string_lossy().to_string());
                        }
                    }
                }
            }
        }
    }

    // Priority 2: Look for main OBS recording file (.mkv, .mp4, .avi, .mov)
    let video_extensions = ["mkv", "mp4", "avi", "mov"];
    if let Ok(entries) = std::fs::read_dir(recording_path) {
        let mut video_files = Vec::new();

        // Collect all video files
        for entry in entries.flatten() {
            let file_path = entry.path();
            if let Some(extension) = file_path.extension() {
                if let Some(ext_str) = extension.to_str() {
                    if video_extensions.contains(&ext_str) && file_path.is_file() {
                        video_files.push(file_path);
                    }
                }
            }
        }

        // First priority: files that match the recording name
        for file_path in &video_files {
            if let Some(file_stem) = file_path.file_stem() {
                if file_stem == recording_name {
                    return Ok(file_path.to_string_lossy().to_string());
                }
            }
        }

        // Second priority: any video file found
        if let Some(first_video) = video_files.first() {
            return Ok(first_video.to_string_lossy().to_string());
        }
    }

    Err(format!(
        "No playable video file found for recording '{}'",
        recording_name
    ))
}

/// Resolve the brief ASS overlay path, erroring clearly when it is absent.
///
/// The overlay is produced by `cymatic-structure-brief` at
/// `<recording>/analysis/structure_brief.ass`.
fn resolve_subtitle_path(recording_path: &Path) -> Result<PathBuf, String> {
    let ass = recording_path
        .join("analysis")
        .join("structure_brief.ass");
    if !ass.exists() {
        return Err(format!(
            "Brief overlay not found: {}. Run the structure brief (cymatic-structure-brief) first.",
            ass.display()
        ));
    }
    Ok(ass)
}

/// Read the structure-map heatmap PNG and encode it as a `data:` URL.
///
/// The heatmap is produced by `cymatic-structure-brief` at
/// `<recording>/analysis/structure_map.png`. Returned as a base64 data URL so
/// the webview can render it without an asset-protocol scope.
fn heatmap_data_url(recording_path: &Path) -> Result<String, String> {
    let png = recording_path.join("analysis").join("structure_map.png");
    if !png.exists() {
        return Err(format!(
            "Structure map not found: {}. Run the structure brief (cymatic-structure-brief) first.",
            png.display()
        ));
    }
    let bytes = std::fs::read(&png).map_err(|e| format!("Failed to read structure map: {}", e))?;
    let b64 = base64::engine::general_purpose::STANDARD.encode(&bytes);
    Ok(format!("data:image/png;base64,{}", b64))
}

/// Get the path to the main video file to play for a recording
#[tauri::command]
pub fn get_playable_video_path(
    recording_name: String,
    config: State<AppConfig>,
) -> Result<String, String> {
    let recording_path =
        crate::commands::path_guard::resolve_recording_dir(&config.recordings_path, &recording_name)?;

    resolve_video_path(&recording_path, &recording_name)
}

/// Open a recording's video in the external system player.
///
/// The contract takes a `recording_name` (not a raw path): the playable video is
/// resolved server-side under the canonicalized recordings root, so a malicious
/// `invoke('open_video_external', { filePath: '/etc/...' })` can no longer make
/// the host open an arbitrary file.
#[tauri::command]
pub fn open_video_external(
    recording_name: String,
    config: State<AppConfig>,
) -> Result<(), String> {
    let recording_path =
        crate::commands::path_guard::resolve_recording_dir(&config.recordings_path, &recording_name)?;
    let file_path = resolve_video_path(&recording_path, &recording_name)?;

    let path = Path::new(&file_path);
    if !path.exists() {
        return Err(format!("Video file not found: {}", file_path));
    }

    println!("🔗 [Rust] Opening video in external player: {}", file_path);

    #[cfg(target_os = "linux")]
    {
        match Command::new("xdg-open").arg(&file_path).spawn() {
            Ok(_) => {
                println!("✅ [Rust] Successfully opened video in external player");
                Ok(())
            }
            Err(e) => {
                let error_msg = format!("Failed to open video: {}", e);
                println!("🚨 [Rust] {}", &error_msg);
                Err(error_msg)
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        match Command::new("cmd").args(&["/C", "start", "", &file_path]).spawn() {
            Ok(_) => {
                println!("✅ [Rust] Successfully opened video in external player");
                Ok(())
            }
            Err(e) => {
                let error_msg = format!("Failed to open video: {}", e);
                println!("🚨 [Rust] {}", &error_msg);
                Err(error_msg)
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        match Command::new("open").arg(&file_path).spawn() {
            Ok(_) => {
                println!("✅ [Rust] Successfully opened video in external player");
                Ok(())
            }
            Err(e) => {
                let error_msg = format!("Failed to open video: {}", e);
                println!("🚨 [Rust] {}", &error_msg);
                Err(error_msg)
            }
        }
    }

    #[cfg(not(any(target_os = "linux", target_os = "windows", target_os = "macos")))]
    {
        Err("External player not supported on this platform".to_string())
    }
}

/// Play the recording's video in VLC with the brief ASS overlay loaded.
///
/// Resolves the playable video and the `structure_brief.ass` overlay, then
/// launches VLC with the subtitle file attached so the structure brief
/// (energy levels, stem activity, ENTER/EXIT/DROP markers) is overlaid live on
/// the source footage. Errors clearly when the overlay has not been generated.
#[tauri::command]
pub fn play_video_with_subtitles(
    recording_name: String,
    config: State<AppConfig>,
) -> Result<(), String> {
    let recording_path =
        crate::commands::path_guard::resolve_recording_dir(&config.recordings_path, &recording_name)?;

    let video_path = resolve_video_path(&recording_path, &recording_name)?;
    let subtitle_path = resolve_subtitle_path(&recording_path)?;

    println!(
        "🔗 [Rust] Playing with brief overlay: {} + {}",
        video_path,
        subtitle_path.display()
    );

    match Command::new("vlc")
        .arg(&video_path)
        .arg("--sub-file")
        .arg(&subtitle_path)
        .spawn()
    {
        Ok(_) => {
            println!("✅ [Rust] Launched VLC with brief overlay");
            Ok(())
        }
        Err(e) => {
            let error_msg = format!("Failed to launch VLC: {}. Is VLC installed?", e);
            println!("🚨 [Rust] {}", &error_msg);
            Err(error_msg)
        }
    }
}

/// Get the recording's structure-map heatmap as a base64 PNG data URL.
#[tauri::command]
pub fn get_structure_heatmap(
    recording_name: String,
    config: State<AppConfig>,
) -> Result<String, String> {
    let recording_path =
        crate::commands::path_guard::resolve_recording_dir(&config.recordings_path, &recording_name)?;

    heatmap_data_url(&recording_path)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    /// Create a clean, uniquely-named temp recording directory for a test.
    fn make_recording_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("fermata_video_test_{}", tag));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn resolve_video_prefers_rendered_final() {
        let dir = make_recording_dir("final");
        let render = dir.join("blender").join("render");
        fs::create_dir_all(&render).unwrap();
        fs::write(render.join("final.mp4"), b"x").unwrap();
        fs::write(dir.join("rec.mkv"), b"x").unwrap();

        let got = resolve_video_path(&dir, "rec").unwrap();
        assert!(got.ends_with("final.mp4"));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn resolve_video_falls_back_to_root_recording() {
        let dir = make_recording_dir("root");
        fs::write(dir.join("rec.mkv"), b"x").unwrap();

        let got = resolve_video_path(&dir, "rec").unwrap();
        assert!(got.ends_with("rec.mkv"));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn resolve_video_errors_when_none() {
        let dir = make_recording_dir("empty");
        assert!(resolve_video_path(&dir, "rec").is_err());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn subtitle_path_errors_when_missing() {
        let dir = make_recording_dir("no_ass");
        let err = resolve_subtitle_path(&dir).unwrap_err();
        assert!(err.contains("structure_brief.ass"));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn subtitle_path_resolves_when_present() {
        let dir = make_recording_dir("with_ass");
        let analysis = dir.join("analysis");
        fs::create_dir_all(&analysis).unwrap();
        fs::write(analysis.join("structure_brief.ass"), b"[Events]\n").unwrap();

        let got = resolve_subtitle_path(&dir).unwrap();
        assert!(got.ends_with("structure_brief.ass"));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn heatmap_data_url_errors_when_missing() {
        let dir = make_recording_dir("no_heatmap");
        assert!(heatmap_data_url(&dir).is_err());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn heatmap_data_url_encodes_png() {
        let dir = make_recording_dir("with_heatmap");
        let analysis = dir.join("analysis");
        fs::create_dir_all(&analysis).unwrap();
        // minimal PNG signature bytes are enough for encoding
        fs::write(analysis.join("structure_map.png"), b"\x89PNG\r\n\x1a\n").unwrap();

        let url = heatmap_data_url(&dir).unwrap();
        assert!(url.starts_with("data:image/png;base64,"));
        let _ = fs::remove_dir_all(&dir);
    }
}
