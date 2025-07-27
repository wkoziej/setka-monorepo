use std::path::Path;
use std::fs;
use tauri::State;
use crate::commands::recordings::AppConfig;

/// Tauri command to rename a recording
#[tauri::command]
pub fn rename_recording(old_name: String, new_name: String, config: State<AppConfig>) -> Result<(), String> {
    log::info!("Renaming recording '{}' to '{}'", old_name, new_name);
    rename_recording_impl(&old_name, &new_name, &config.recordings_path)
}

/// Internal implementation for renaming recording directory
pub fn rename_recording_impl(
    old_name: &str,
    new_name: &str,
    recordings_path: &Path
) -> Result<(), String> {
    // Validation
    if old_name.is_empty() {
        return Err("Recording name cannot be empty".to_string());
    }

    if new_name.is_empty() {
        return Err("New recording name cannot be empty".to_string());
    }

    if old_name == new_name {
        return Err("Cannot rename to the same name".to_string());
    }

    let old_dir = recordings_path.join(old_name);
    let new_dir = recordings_path.join(new_name);

    // Check if source exists
    if !old_dir.exists() {
        return Err(format!("Recording '{}' not found", old_name));
    }

    if !old_dir.is_dir() {
        return Err(format!("Recording '{}' is not a directory", old_name));
    }

    // Check if target already exists
    if new_dir.exists() {
        return Err(format!("Recording with name '{}' already exists", new_name));
    }

    // Atomic rename operation
    fs::rename(&old_dir, &new_dir)
        .map_err(|e| format!("Failed to rename recording directory: {}", e))?;

    // Rename main recording file if it exists and matches directory name
    if let Err(e) = rename_main_recording_file(&old_dir, &new_dir, old_name, new_name) {
        // If file rename fails, try to rollback directory rename
        if let Err(rollback_err) = fs::rename(&new_dir, &old_dir) {
            return Err(format!("Failed to rename recording file: {} (rollback also failed: {})", e, rollback_err));
        }
        return Err(format!("Failed to rename recording file: {}", e));
    }

    log::info!("Successfully renamed recording '{}' to '{}'", old_name, new_name);
    Ok(())
}

/// Rename the main recording file if it matches the directory name
fn rename_main_recording_file(
    _old_dir: &Path,
    new_dir: &Path,
    old_name: &str,
    new_name: &str
) -> Result<(), String> {
    // Look for main recording file that matches old directory name
    let old_recording_file = new_dir.join(format!("{}.mkv", old_name));
    let new_recording_file = new_dir.join(format!("{}.mkv", new_name));

    // If the old recording file exists, rename it
    if old_recording_file.exists() {
        fs::rename(&old_recording_file, &new_recording_file)
            .map_err(|e| format!("Failed to rename recording file from '{}' to '{}': {}",
                old_recording_file.display(), new_recording_file.display(), e))?;

        log::info!("Renamed recording file from '{}' to '{}'",
            old_recording_file.display(), new_recording_file.display());
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn setup_test_recording(temp_dir: &Path, name: &str) -> std::path::PathBuf {
        let recording_dir = temp_dir.join(name);
        fs::create_dir_all(&recording_dir).unwrap();

        // Create main recording file with same name as directory
        let recording_file = recording_dir.join(format!("{}.mkv", name));
        fs::write(&recording_file, "fake video content").unwrap();

        // Create metadata.json
        let metadata_file = recording_dir.join("metadata.json");
        fs::write(&metadata_file, r#"{"obs_data": "test"}"#).unwrap();

        // Create extracted directory
        let extracted_dir = recording_dir.join("extracted");
        fs::create_dir_all(&extracted_dir).unwrap();
        fs::write(extracted_dir.join("audio.m4a"), "fake audio").unwrap();

        recording_dir
    }

    #[test]
    fn test_rename_recording_success() {
        let temp_dir = std::env::temp_dir().join("fermata_rename_test_success");
        fs::create_dir_all(&temp_dir).unwrap();

        // Setup test recording
        setup_test_recording(&temp_dir, "old_recording");

        // Test rename operation
        let result = rename_recording_impl("old_recording", "new_recording", &temp_dir);

        assert!(result.is_ok(), "Rename should succeed");

        // Verify old directory doesn't exist
        assert!(!temp_dir.join("old_recording").exists());

        // Verify new directory exists
        assert!(temp_dir.join("new_recording").exists());

        // Verify main recording file was renamed
        assert!(temp_dir.join("new_recording").join("new_recording.mkv").exists());
        assert!(!temp_dir.join("new_recording").join("old_recording.mkv").exists());

        // Verify other files remain
        assert!(temp_dir.join("new_recording").join("metadata.json").exists());
        assert!(temp_dir.join("new_recording").join("extracted").join("audio.m4a").exists());

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_rename_recording_source_not_exists() {
        let temp_dir = std::env::temp_dir().join("fermata_rename_test_no_source");
        fs::create_dir_all(&temp_dir).unwrap();

        let result = rename_recording_impl("nonexistent", "new_name", &temp_dir);

        assert!(result.is_err());
        assert!(result.unwrap_err().contains("not found"));

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_rename_recording_target_exists() {
        let temp_dir = std::env::temp_dir().join("fermata_rename_test_target_exists");
        fs::create_dir_all(&temp_dir).unwrap();

        // Setup both source and target recordings
        setup_test_recording(&temp_dir, "source_recording");
        setup_test_recording(&temp_dir, "target_recording");

        let result = rename_recording_impl("source_recording", "target_recording", &temp_dir);

        assert!(result.is_err());
        assert!(result.unwrap_err().contains("already exists"));

        // Verify source still exists (no partial operation)
        assert!(temp_dir.join("source_recording").exists());
        assert!(temp_dir.join("target_recording").exists());

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_rename_recording_empty_names() {
        let temp_dir = std::env::temp_dir().join("fermata_rename_test_empty");
        fs::create_dir_all(&temp_dir).unwrap();

        setup_test_recording(&temp_dir, "test_recording");

        // Test empty old name
        let result = rename_recording_impl("", "new_name", &temp_dir);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("cannot be empty"));

        // Test empty new name
        let result = rename_recording_impl("test_recording", "", &temp_dir);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("cannot be empty"));

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_rename_recording_same_name() {
        let temp_dir = std::env::temp_dir().join("fermata_rename_test_same");
        fs::create_dir_all(&temp_dir).unwrap();

        setup_test_recording(&temp_dir, "test_recording");

        let result = rename_recording_impl("test_recording", "test_recording", &temp_dir);

        assert!(result.is_err());
        assert!(result.unwrap_err().contains("same name"));

        // Verify recording still exists
        assert!(temp_dir.join("test_recording").exists());

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_rename_recording_no_main_file() {
        let temp_dir = std::env::temp_dir().join("fermata_rename_test_no_main");
        fs::create_dir_all(&temp_dir).unwrap();

        // Create recording without main .mkv file
        let recording_dir = temp_dir.join("test_recording");
        fs::create_dir_all(&recording_dir).unwrap();
        fs::write(recording_dir.join("metadata.json"), r#"{"obs_data": "test"}"#).unwrap();

        let result = rename_recording_impl("test_recording", "new_recording", &temp_dir);

        // Should still succeed even without main recording file
        assert!(result.is_ok());

        // Verify directory was renamed
        assert!(!temp_dir.join("test_recording").exists());
        assert!(temp_dir.join("new_recording").exists());
        assert!(temp_dir.join("new_recording").join("metadata.json").exists());

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_rename_main_recording_file() {
        let temp_dir = std::env::temp_dir().join("fermata_rename_file_test");
        fs::create_dir_all(&temp_dir).unwrap();

        let old_dir = temp_dir.join("old_name");
        let new_dir = temp_dir.join("new_name");
        fs::create_dir_all(&new_dir).unwrap(); // Create new_dir first

        // Create main recording file in NEW directory with OLD name (simulates after directory rename)
        let old_named_file = new_dir.join("old_name.mkv");
        fs::write(&old_named_file, "video content").unwrap();

        let result = rename_main_recording_file(&old_dir, &new_dir, "old_name", "new_name");

        assert!(result.is_ok());

        // File should be renamed to new name in new directory
        assert!(!old_named_file.exists());
        assert!(new_dir.join("new_name.mkv").exists());

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_rename_main_recording_file_not_exists() {
        let temp_dir = std::env::temp_dir().join("fermata_rename_file_not_exists");
        fs::create_dir_all(&temp_dir).unwrap();

        let old_dir = temp_dir.join("old_name");
        let new_dir = temp_dir.join("new_name");
        fs::create_dir_all(&old_dir).unwrap();
        fs::create_dir_all(&new_dir).unwrap();

        // No main recording file exists
        let result = rename_main_recording_file(&old_dir, &new_dir, "old_name", "new_name");

        // Should succeed (not all recordings have matching .mkv files)
        assert!(result.is_ok());

        // Cleanup
        let _ = fs::remove_dir_all(&temp_dir);
    }
}
