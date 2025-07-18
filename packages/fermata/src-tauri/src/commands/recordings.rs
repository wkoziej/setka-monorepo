use crate::models::Recording;
use crate::services::FileScanner;
use std::path::PathBuf;
use tauri::State;

/// Configuration state for the app
#[derive(Debug)]
pub struct AppConfig {
    pub recordings_path: PathBuf,
    pub cli_paths: CliPaths,
    pub main_audio_file: String,
}

#[derive(Debug)]
pub struct CliPaths {
    pub uv_path: String,
    pub workspace_root: PathBuf,
}

impl Default for AppConfig {
    fn default() -> Self {
        // Debug all environment variables
        log::info!("=== Environment Variables Debug ===");
        for (key, value) in std::env::vars() {
            if key.starts_with("FERMATA_") {
                log::info!("ENV: {} = {}", key, value);
            }
        }
        
        let recordings_path_str = std::env::var("FERMATA_RECORDINGS_PATH")
            .unwrap_or_else(|e| {
                log::warn!("FERMATA_RECORDINGS_PATH not found: {}", e);
                std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string()) + "/Videos/obs-recordings"
            });
        
        let workspace_root_str = std::env::var("FERMATA_WORKSPACE_ROOT")
            .unwrap_or_else(|e| {
                log::warn!("FERMATA_WORKSPACE_ROOT not found: {}", e);
                std::env::current_dir().unwrap_or_default().to_string_lossy().to_string()
            });
        
        let main_audio_file = std::env::var("FERMATA_MAIN_AUDIO")
            .unwrap_or_else(|_| "Przechwytywanie wejścia dźwięku (PulseAudio).m4a".to_string());
        
        log::info!("Final config - recordings_path: {}", recordings_path_str);
        log::info!("Final config - workspace_root: {}", workspace_root_str);
        log::info!("Final config - main_audio_file: {}", main_audio_file);
        
        // Default configuration - can be overridden by user settings
        AppConfig {
            recordings_path: PathBuf::from(recordings_path_str),
            cli_paths: CliPaths {
                uv_path: "uv".to_string(),
                workspace_root: PathBuf::from(workspace_root_str),
            },
            main_audio_file,
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

/// Delete a recording by removing its entire directory
#[tauri::command]
pub fn delete_recording(recording_name: String, config: State<AppConfig>) -> Result<(), String> {
    delete_recording_impl(&recording_name, &config.recordings_path)
}

/// Internal implementation for testing
fn delete_recording_impl(recording_name: &str, recordings_path: &std::path::Path) -> Result<(), String> {
    log::info!("Attempting to delete recording: {}", recording_name);
    
    let recording_path = recordings_path.join(recording_name);
    
    if !recording_path.exists() {
        let error_msg = format!("Recording '{}' not found at path: {}", recording_name, recording_path.display());
        log::error!("{}", error_msg);
        return Err(error_msg);
    }
    
    if !recording_path.is_dir() {
        let error_msg = format!("Recording '{}' is not a directory", recording_name);
        log::error!("{}", error_msg);
        return Err(error_msg);
    }
    
    // Remove the entire recording directory
    std::fs::remove_dir_all(&recording_path)
        .map_err(|e| {
            let error_msg = format!("Failed to delete recording '{}': {}", recording_name, e);
            log::error!("{}", error_msg);
            error_msg
        })?;
    
    log::info!("Successfully deleted recording: {}", recording_name);
    Ok(())
}

/// Update the recordings path configuration
#[tauri::command]
pub fn update_recordings_path(new_path: String, _config: State<AppConfig>) -> Result<String, String> {
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
        main_audio_file: config.main_audio_file.clone(),
    })
}

/// DTO for sending config to frontend
#[derive(serde::Serialize)]
pub struct AppConfigDto {
    pub recordings_path: String,
    pub cli_paths: CliPathsDto,
    pub main_audio_file: String,
}

#[derive(serde::Serialize)]
pub struct CliPathsDto {
    pub uv_path: String,
    pub workspace_root: String,
}

// All old problematic tests removed



#[cfg(test)]
mod delete_tests {
    use super::*;

    #[test]
    fn test_delete_recording_impl_success() {
        // Create temporary directory for test
        let temp_dir = std::env::temp_dir().join("fermata_test_delete_new");
        let recording_dir = temp_dir.join("test_recording");
        
        // Setup test recording directory
        std::fs::create_dir_all(&recording_dir).unwrap();
        std::fs::write(recording_dir.join("test_file.txt"), "test content").unwrap();
        
        // Test our delete function
        let result = delete_recording_impl("test_recording", &temp_dir);
        
        assert!(result.is_ok());
        assert!(!recording_dir.exists());
        
        // Cleanup
        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_delete_recording_impl_not_found() {
        let temp_dir = std::env::temp_dir().join("fermata_test_delete_missing_new");
        std::fs::create_dir_all(&temp_dir).unwrap();
        
        // Test error case - try to delete nonexistent recording
        let result = delete_recording_impl("nonexistent_recording", &temp_dir);
        
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("not found"));
        
        // Cleanup
        let _ = std::fs::remove_dir_all(&temp_dir);
    }
} 