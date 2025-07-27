use crate::models::{Recording, RecordingStatus};
use std::collections::HashMap;
use std::path::Path;

pub struct StatusDetector;

impl StatusDetector {
    /// Detect the status of a recording based on file system structure
    pub fn detect_status(recording_path: &Path) -> RecordingStatus {
        // Check for failure indicators first
        if let Some(error) = Self::check_for_errors(recording_path) {
            return RecordingStatus::Failed(error);
        }

        // Check for completion indicators in reverse order (most advanced first)
        if Self::has_uploads(recording_path) {
            return RecordingStatus::Uploaded;
        }

        if Self::has_rendered_video(recording_path) {
            return RecordingStatus::Rendered;
        }

        if Self::has_render_setup(recording_path) {
            return RecordingStatus::SetupRendered;
        }

        if Self::has_analysis_files(recording_path) {
            return RecordingStatus::Analyzed;
        }

        if Self::has_extracted_files(recording_path) {
            return RecordingStatus::Extracted;
        }

        // Default to recorded if directory exists
        RecordingStatus::Recorded
    }

    /// Get file size information for a recording
    pub fn get_file_info(recording_path: &Path) -> HashMap<String, u64> {
        let mut file_sizes = HashMap::new();

        // Recursively scan all files in the recording directory
        if let Ok(entries) = walkdir::WalkDir::new(recording_path).into_iter().collect::<Result<Vec<_>, _>>() {
            for entry in entries {
                if entry.file_type().is_file() {
                    if let Ok(metadata) = entry.metadata() {
                        // Get relative path from recording directory
                        if let Ok(relative_path) = entry.path().strip_prefix(recording_path) {
                            let path_str = relative_path.to_string_lossy().to_string();
                            file_sizes.insert(path_str, metadata.len());
                        }
                    }
                }
            }
        }

        file_sizes
    }

    /// Validate that a recording has the expected structure
    pub fn validate_recording_structure(path: &Path) -> Result<(), String> {
        if !path.exists() {
            return Err(format!("Recording directory does not exist: {}", path.display()));
        }

        if !path.is_dir() {
            return Err(format!("Recording path is not a directory: {}", path.display()));
        }

        // Check if it looks like a recording directory (has video file or extracted content)
        let has_video = Self::get_video_file_size(path).is_some();
        let has_extracted = path.join("extracted").exists();

        if !has_video && !has_extracted {
            return Err("Directory does not appear to be a recording (no video file or extracted directory)".to_string());
        }

        Ok(())
    }

    // Private helper methods
    fn has_extracted_files(path: &Path) -> bool {
        let extracted_path = path.join("extracted");
        extracted_path.exists() && extracted_path.is_dir()
    }

    fn has_analysis_files(path: &Path) -> bool {
        let analysis_path = path.join("analysis");
        if !analysis_path.exists() || !analysis_path.is_dir() {
            return false;
        }

        // Check for any .json files in analysis directory
        if let Ok(entries) = std::fs::read_dir(&analysis_path) {
            for entry in entries.flatten() {
                if let Some(extension) = entry.path().extension() {
                    if extension == "json" {
                        return true;
                    }
                }
            }
        }
        false
    }

    fn has_render_setup(path: &Path) -> bool {
        let blender_path = path.join("blender");
        if !blender_path.exists() || !blender_path.is_dir() {
            return false;
        }

        // Check for .blend file in blender directory (setup complete)
        if let Ok(entries) = std::fs::read_dir(&blender_path) {
            for entry in entries.flatten() {
                if let Some(extension) = entry.path().extension() {
                    if extension == "blend" {
                        return true;
                    }
                }
            }
        }

        false
    }

    fn has_rendered_video(path: &Path) -> bool {
        let render_path = path.join("blender").join("render");
        if !render_path.exists() || !render_path.is_dir() {
            return false;
        }

        // Check for actual video files in render directory (fully rendered)
        if let Ok(entries) = std::fs::read_dir(&render_path) {
            for entry in entries.flatten() {
                if let Some(extension) = entry.path().extension() {
                    if matches!(extension.to_str(), Some("mp4") | Some("mkv") | Some("avi")) {
                        return true;
                    }
                }
            }
        }

        false
    }

    fn has_uploads(path: &Path) -> bool {
        let uploads_path = path.join("uploads");
        if !uploads_path.exists() || !uploads_path.is_dir() {
            return false;
        }

        // Check for upload results
        uploads_path.join("upload_results.json").exists()
    }

    fn check_for_errors(path: &Path) -> Option<String> {
        // Check for common error indicators
        let error_log = path.join("error.log");
        if error_log.exists() {
            if let Ok(content) = std::fs::read_to_string(&error_log) {
                if !content.trim().is_empty() {
                    return Some(content.lines().last().unwrap_or("Unknown error").to_string());
                }
            }
        }

        // Check for failed process indicators
        let failed_marker = path.join(".failed");
        if failed_marker.exists() {
            if let Ok(content) = std::fs::read_to_string(&failed_marker) {
                return Some(content.trim().to_string());
            }
            return Some("Process failed".to_string());
        }

        None
    }

    fn get_video_file_size(path: &Path) -> Option<u64> {
        if let Ok(entries) = std::fs::read_dir(path) {
            for entry in entries.flatten() {
                if let Some(extension) = entry.path().extension() {
                    // Support both .mkv and .mp4 files for OBS recordings
                    if matches!(extension.to_str(), Some("mkv") | Some("mp4")) {
                        if let Ok(metadata) = entry.metadata() {
                            return Some(metadata.len());
                        }
                    }
                }
            }
        }
        None
    }

    fn get_directory_size(path: &Path) -> Option<u64> {
        if !path.exists() || !path.is_dir() {
            return None;
        }

        let mut total_size = 0u64;
        if let Ok(entries) = walkdir::WalkDir::new(path).into_iter().collect::<Result<Vec<_>, _>>() {
            for entry in entries {
                if entry.file_type().is_file() {
                    if let Ok(metadata) = entry.metadata() {
                        total_size += metadata.len();
                    }
                }
            }
            Some(total_size)
        } else {
            None
        }
    }
}

/// Update a recording's status and file sizes
pub fn update_recording_status(recording: &mut Recording) {
    recording.status = StatusDetector::detect_status(&recording.path);
    recording.file_sizes = StatusDetector::get_file_info(&recording.path);
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;
    use tempfile::TempDir;

    fn create_test_recording_structure() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let recording_path = temp_dir.path().join("test_recording");
        fs::create_dir_all(&recording_path).unwrap();

        // Create a dummy video file (test with .mp4 like real OBS recordings)
        fs::write(recording_path.join("test_recording.mp4"), b"dummy mp4 content").unwrap();

        temp_dir
    }

    #[test]
    fn test_detect_status_recorded() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        let status = StatusDetector::detect_status(&recording_path);
        assert_eq!(status, RecordingStatus::Recorded);
    }

    #[test]
    fn test_detect_status_extracted() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        // Create extracted directory
        fs::create_dir_all(recording_path.join("extracted")).unwrap();

        let status = StatusDetector::detect_status(&recording_path);
        assert_eq!(status, RecordingStatus::Extracted);
    }

    #[test]
    fn test_detect_status_analyzed() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        // Create extracted and analysis directories
        fs::create_dir_all(recording_path.join("extracted")).unwrap();
        fs::create_dir_all(recording_path.join("analysis")).unwrap();
        fs::write(recording_path.join("analysis/audio_analysis.json"), b"{}").unwrap();

        let status = StatusDetector::detect_status(&recording_path);
        assert_eq!(status, RecordingStatus::Analyzed);
    }

    #[test]
    fn test_detect_status_setup_rendered() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        // Create pipeline up to setup rendered (blend file exists)
        fs::create_dir_all(recording_path.join("extracted")).unwrap();
        fs::create_dir_all(recording_path.join("analysis")).unwrap();
        fs::write(recording_path.join("analysis/audio_analysis.json"), b"{}").unwrap();
        fs::create_dir_all(recording_path.join("blender")).unwrap();
        fs::write(recording_path.join("blender/project.blend"), b"dummy blend").unwrap();

        let status = StatusDetector::detect_status(&recording_path);
        assert_eq!(status, RecordingStatus::SetupRendered);
    }

    #[test]
    fn test_detect_status_rendered() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        // Create full pipeline up to render (video file exists)
        fs::create_dir_all(recording_path.join("extracted")).unwrap();
        fs::create_dir_all(recording_path.join("analysis")).unwrap();
        fs::write(recording_path.join("analysis/audio_analysis.json"), b"{}").unwrap();
        fs::create_dir_all(recording_path.join("blender")).unwrap();
        fs::write(recording_path.join("blender/project.blend"), b"dummy blend").unwrap();
        fs::create_dir_all(recording_path.join("blender/render")).unwrap();
        fs::write(recording_path.join("blender/render/output.mp4"), b"dummy video").unwrap();

        let status = StatusDetector::detect_status(&recording_path);
        assert_eq!(status, RecordingStatus::Rendered);
    }

    #[test]
    fn test_detect_status_uploaded() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        // Create full pipeline
        fs::create_dir_all(recording_path.join("extracted")).unwrap();
        fs::create_dir_all(recording_path.join("analysis")).unwrap();
        fs::write(recording_path.join("analysis/audio_analysis.json"), b"{}").unwrap();
        fs::create_dir_all(recording_path.join("blender/render")).unwrap();
        fs::write(recording_path.join("blender/render/output.mp4"), b"dummy video").unwrap();
        fs::create_dir_all(recording_path.join("uploads")).unwrap();
        fs::write(recording_path.join("uploads/upload_results.json"), b"{}").unwrap();

        let status = StatusDetector::detect_status(&recording_path);
        assert_eq!(status, RecordingStatus::Uploaded);
    }

    #[test]
    fn test_detect_status_failed() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        // Create error indicator
        fs::write(recording_path.join("error.log"), b"Audio analysis failed").unwrap();

        let status = StatusDetector::detect_status(&recording_path);
        if let RecordingStatus::Failed(error) = status {
            assert_eq!(error, "Audio analysis failed");
        } else {
            panic!("Expected Failed status");
        }
    }

    #[test]
    fn test_get_file_info() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        let file_info = StatusDetector::get_file_info(&recording_path);

        assert!(file_info.contains_key("recording.video"));
        assert!(file_info["recording.video"] > 0); // Should have size from dummy content
    }

    #[test]
    fn test_validate_recording_structure_valid() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        let result = StatusDetector::validate_recording_structure(&recording_path);
        assert!(result.is_ok());
    }

    #[test]
    fn test_validate_recording_structure_invalid() {
        let temp_dir = TempDir::new().unwrap();
        let invalid_path = temp_dir.path().join("nonexistent");

        let result = StatusDetector::validate_recording_structure(&invalid_path);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("does not exist"));
    }

    #[test]
    fn test_update_recording_status() {
        let temp_dir = create_test_recording_structure();
        let recording_path = temp_dir.path().join("test_recording");

        let mut recording = Recording {
            name: "test_recording".to_string(),
            path: recording_path,
            status: RecordingStatus::Failed("old error".to_string()),
            last_updated: std::time::SystemTime::now().duration_since(std::time::SystemTime::UNIX_EPOCH).unwrap().as_secs(),
            file_sizes: HashMap::new(),
        };

        update_recording_status(&mut recording);

        assert_eq!(recording.status, RecordingStatus::Recorded);
        assert!(!recording.file_sizes.is_empty());
    }
}
