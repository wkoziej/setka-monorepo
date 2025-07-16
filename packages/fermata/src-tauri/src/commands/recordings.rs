use crate::models::Recording;
use crate::services::FileScanner;
use std::path::PathBuf;
use tauri::State;

/// Configuration state for the app
#[derive(Debug)]
pub struct AppConfig {
    pub recordings_path: PathBuf,
    pub cli_paths: CliPaths,
}

#[derive(Debug)]
pub struct CliPaths {
    pub uv_path: String,
    pub workspace_root: PathBuf,
}

impl Default for AppConfig {
    fn default() -> Self {
        // Default configuration - can be overridden by user settings
        AppConfig {
            recordings_path: PathBuf::from(
                std::env::var("FERMATA_RECORDINGS_PATH")
                    .unwrap_or_else(|_| std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string()) + "/recordings")
            ),
            cli_paths: CliPaths {
                uv_path: "uv".to_string(),
                workspace_root: PathBuf::from(
                    std::env::var("FERMATA_WORKSPACE_ROOT")
                        .unwrap_or_else(|_| std::env::current_dir().unwrap_or_default().to_string_lossy().to_string())
                ),
            },
        }
    }
}

/// Get all recordings from the configured directory
#[tauri::command]
pub fn get_recordings(config: State<AppConfig>) -> Result<Vec<Recording>, String> {
    log::info!("Scanning recordings from: {}", config.recordings_path.display());
    
    let recordings = FileScanner::scan_recordings(&config.recordings_path);
    
    log::info!("Found {} recordings", recordings.len());
    Ok(recordings)
}

/// Get details for a specific recording by name
#[tauri::command]
pub fn get_recording_details(name: String, config: State<AppConfig>) -> Result<Recording, String> {
    log::info!("Getting details for recording: {}", name);
    
    let recording_path = config.recordings_path.join(&name);
    
    if !recording_path.exists() {
        return Err(format!("Recording '{}' not found", name));
    }
    
    let mut recording = Recording::from_path(recording_path)
        .map_err(|e| format!("Failed to load recording '{}': {}", name, e))?;
    
    // Update with current status
    crate::services::update_recording_status(&mut recording);
    
    Ok(recording)
}

/// Get recordings filtered by status
#[tauri::command]
pub fn get_recordings_by_status(status_filter: String, config: State<AppConfig>) -> Result<Vec<Recording>, String> {
    log::info!("Getting recordings filtered by status: {}", status_filter);
    
    let all_recordings = FileScanner::scan_recordings(&config.recordings_path);
    let filtered = FileScanner::filter_by_status(&all_recordings, &status_filter);
    
    Ok(filtered)
}

/// Get recordings that need attention (failed or incomplete)
#[tauri::command]
pub fn get_recordings_needing_attention(config: State<AppConfig>) -> Result<Vec<Recording>, String> {
    log::info!("Getting recordings that need attention");
    
    let all_recordings = FileScanner::scan_recordings(&config.recordings_path);
    let needing_attention = FileScanner::get_recordings_needing_attention(&all_recordings);
    
    Ok(needing_attention)
}

/// Update the recordings path configuration
#[tauri::command]
pub fn update_recordings_path(new_path: String, config: State<AppConfig>) -> Result<String, String> {
    // Note: In a real app, this would persist the configuration
    // For MVP, we'll just validate the path
    let path = PathBuf::from(&new_path);
    
    if !path.exists() {
        return Err(format!("Path does not exist: {}", new_path));
    }
    
    if !path.is_dir() {
        return Err(format!("Path is not a directory: {}", new_path));
    }
    
    log::info!("Recordings path would be updated to: {}", new_path);
    Ok(format!("Path validation successful: {}", new_path))
}

/// Get current app configuration
#[tauri::command]
pub fn get_app_config(config: State<AppConfig>) -> Result<AppConfigDto, String> {
    Ok(AppConfigDto {
        recordings_path: config.recordings_path.to_string_lossy().to_string(),
        cli_paths: CliPathsDto {
            uv_path: config.cli_paths.uv_path.clone(),
            workspace_root: config.cli_paths.workspace_root.to_string_lossy().to_string(),
        },
    })
}

/// DTO for sending config to frontend
#[derive(serde::Serialize)]
pub struct AppConfigDto {
    pub recordings_path: String,
    pub cli_paths: CliPathsDto,
}

#[derive(serde::Serialize)]
pub struct CliPathsDto {
    pub uv_path: String,
    pub workspace_root: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::services::StatusDetector;
    use std::fs;
    use tempfile::TempDir;

    fn create_test_config(recordings_path: PathBuf) -> AppConfig {
        AppConfig {
            recordings_path,
            cli_paths: CliPaths {
                uv_path: "uv".to_string(),
                workspace_root: PathBuf::from("/tmp"),
            },
        }
    }

    fn create_test_recordings() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let root_path = temp_dir.path();

        // Create test recordings
        for name in ["recording_001", "recording_002"] {
            let recording_path = root_path.join(name);
            fs::create_dir_all(&recording_path).unwrap();
            fs::write(recording_path.join(format!("{}.mkv", name)), b"dummy").unwrap();
        }

        temp_dir
    }

    #[test]
    fn test_get_recordings_command() {
        let temp_dir = create_test_recordings();
        let config = create_test_config(temp_dir.path().to_path_buf());
        
        let recordings = get_recordings(State::from(&config)).unwrap();
        assert_eq!(recordings.len(), 2);
    }

    #[test]
    fn test_get_recording_details_command() {
        let temp_dir = create_test_recordings();
        let config = create_test_config(temp_dir.path().to_path_buf());
        
        let recording = get_recording_details(
            "recording_001".to_string(),
            State::from(&config)
        ).unwrap();
        
        assert_eq!(recording.name, "recording_001");
        assert!(matches!(recording.status, crate::models::RecordingStatus::Recorded));
    }

    #[test]
    fn test_get_recording_details_not_found() {
        let temp_dir = create_test_recordings();
        let config = create_test_config(temp_dir.path().to_path_buf());
        
        let result = get_recording_details(
            "nonexistent".to_string(),
            State::from(&config)
        );
        
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("not found"));
    }

    #[test]
    fn test_get_recordings_by_status_command() {
        let temp_dir = create_test_recordings();
        let config = create_test_config(temp_dir.path().to_path_buf());
        
        let recordings = get_recordings_by_status(
            "recorded".to_string(),
            State::from(&config)
        ).unwrap();
        
        assert_eq!(recordings.len(), 2); // Both should be in "recorded" status
    }

    #[test]
    fn test_update_recordings_path_valid() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_test_config(PathBuf::from("/tmp"));
        
        let result = update_recordings_path(
            temp_dir.path().to_string_lossy().to_string(),
            State::from(&config)
        );
        
        assert!(result.is_ok());
    }

    #[test]
    fn test_update_recordings_path_invalid() {
        let config = create_test_config(PathBuf::from("/tmp"));
        
        let result = update_recordings_path(
            "/nonexistent/path".to_string(),
            State::from(&config)
        );
        
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("does not exist"));
    }

    #[test]
    fn test_get_app_config_command() {
        let config = AppConfig::default();
        let config_dto = get_app_config(State::from(&config)).unwrap();
        
        assert!(!config_dto.recordings_path.is_empty());
        assert!(!config_dto.cli_paths.uv_path.is_empty());
        assert!(!config_dto.cli_paths.workspace_root.is_empty());
    }
} 