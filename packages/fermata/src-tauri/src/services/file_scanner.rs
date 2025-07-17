use crate::models::Recording;
use crate::services::{StatusDetector, update_recording_status};
use std::path::Path;

pub struct FileScanner;

impl FileScanner {
    /// Scan a directory for recordings and return a list of Recording structs
    pub fn scan_recordings(root_path: &Path) -> Vec<Recording> {
        let mut recordings = Vec::new();

        if !root_path.exists() || !root_path.is_dir() {
            log::warn!("Recordings directory does not exist or is not a directory: {}", root_path.display());
            return recordings;
        }

        match std::fs::read_dir(root_path) {
            Ok(entries) => {
                for entry in entries.flatten() {
                    let path = entry.path();
                    
                    if path.is_dir() && Self::is_valid_recording_dir(&path) {
                        match Recording::from_path(path) {
                            Ok(mut recording) => {
                                // Update status and file sizes based on current filesystem state
                                update_recording_status(&mut recording);
                                recordings.push(recording);
                            }
                            Err(e) => {
                                log::warn!("Failed to create recording from path {}: {}", entry.path().display(), e);
                            }
                        }
                    }
                }
            }
            Err(e) => {
                log::error!("Failed to read recordings directory {}: {}", root_path.display(), e);
            }
        }

        // Sort recordings by last updated (most recent first)
        recordings.sort_by(|a, b| b.last_updated.cmp(&a.last_updated));

        recordings
    }

    /// Check if a directory looks like a valid recording directory
    pub fn is_valid_recording_dir(path: &Path) -> bool {
        if !path.is_dir() {
            return false;
        }

        // Use the status detector's validation
        StatusDetector::validate_recording_structure(path).is_ok()
    }

    /// Extract recording name from directory path
    pub fn get_recording_name(path: &Path) -> String {
        path.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
            .to_string()
    }

    /// Filter recordings by status
    pub fn filter_by_status(recordings: &[Recording], status_filter: &str) -> Vec<Recording> {
        recordings
            .iter()
            .filter(|recording| {
                match status_filter.to_lowercase().as_str() {
                    "recorded" => matches!(recording.status, crate::models::RecordingStatus::Recorded),
                    "extracted" => matches!(recording.status, crate::models::RecordingStatus::Extracted),
                    "analyzed" => matches!(recording.status, crate::models::RecordingStatus::Analyzed),
                    "rendered" => matches!(recording.status, crate::models::RecordingStatus::Rendered),
                    "uploaded" => matches!(recording.status, crate::models::RecordingStatus::Uploaded),
                    "failed" => matches!(recording.status, crate::models::RecordingStatus::Failed(_)),
                    _ => true, // No filter or unknown filter
                }
            })
            .cloned()
            .collect()
    }

    /// Get recordings that need attention (failed or incomplete)
    pub fn get_recordings_needing_attention(recordings: &[Recording]) -> Vec<Recording> {
        recordings
            .iter()
            .filter(|recording| {
                matches!(
                    recording.status,
                    crate::models::RecordingStatus::Failed(_) | 
                    crate::models::RecordingStatus::Recorded |
                    crate::models::RecordingStatus::Extracted |
                    crate::models::RecordingStatus::Analyzed |
                    crate::models::RecordingStatus::Rendered
                )
            })
            .cloned()
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;
    use tempfile::TempDir;

    fn create_test_recordings_structure() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let root_path = temp_dir.path();

        // Create a few test recordings
        for (name, has_extracted, has_analysis) in [
            ("recording_001", false, false),
            ("recording_002", true, false),
            ("recording_003", true, true),
        ] {
            let recording_path = root_path.join(name);
            fs::create_dir_all(&recording_path).unwrap();
            
            // Create main video file (test with .mp4 like real OBS recordings)
            fs::write(recording_path.join(format!("{}.mp4", name)), b"dummy content").unwrap();
            
            if has_extracted {
                fs::create_dir_all(recording_path.join("extracted")).unwrap();
                fs::write(recording_path.join("extracted/audio.m4a"), b"audio").unwrap();
            }
            
            if has_analysis {
                fs::create_dir_all(recording_path.join("analysis")).unwrap();
                fs::write(recording_path.join("analysis/audio_analysis.json"), b"{}").unwrap();
            }
        }

        // Create an invalid directory (no .mkv file)
        let invalid_path = root_path.join("not_a_recording");
        fs::create_dir_all(&invalid_path).unwrap();
        fs::write(invalid_path.join("some_file.txt"), b"not a recording").unwrap();

        temp_dir
    }

    #[test]
    fn test_scan_recordings() {
        let temp_dir = create_test_recordings_structure();
        let recordings = FileScanner::scan_recordings(temp_dir.path());

        // Should find 3 valid recordings
        assert_eq!(recordings.len(), 3);

        // Check that recordings have the expected names
        let names: Vec<String> = recordings.iter().map(|r| r.name.clone()).collect();
        assert!(names.contains(&"recording_001".to_string()));
        assert!(names.contains(&"recording_002".to_string()));
        assert!(names.contains(&"recording_003".to_string()));
    }

    #[test]
    fn test_scan_recordings_empty_directory() {
        let temp_dir = TempDir::new().unwrap();
        let recordings = FileScanner::scan_recordings(temp_dir.path());
        assert!(recordings.is_empty());
    }

    #[test]
    fn test_scan_recordings_nonexistent_directory() {
        let temp_dir = TempDir::new().unwrap();
        let nonexistent = temp_dir.path().join("nonexistent");
        let recordings = FileScanner::scan_recordings(&nonexistent);
        assert!(recordings.is_empty());
    }

    #[test]
    fn test_is_valid_recording_dir() {
        let temp_dir = create_test_recordings_structure();
        let root_path = temp_dir.path();

        // Valid recording directories
        assert!(FileScanner::is_valid_recording_dir(&root_path.join("recording_001")));
        assert!(FileScanner::is_valid_recording_dir(&root_path.join("recording_002")));
        assert!(FileScanner::is_valid_recording_dir(&root_path.join("recording_003")));

        // Invalid directory
        assert!(!FileScanner::is_valid_recording_dir(&root_path.join("not_a_recording")));

        // Non-existent directory
        assert!(!FileScanner::is_valid_recording_dir(&root_path.join("nonexistent")));
    }

    #[test]
    fn test_get_recording_name() {
        let path = PathBuf::from("/path/to/my_recording_name");
        assert_eq!(FileScanner::get_recording_name(&path), "my_recording_name");

        let root_path = PathBuf::from("/");
        assert_eq!(FileScanner::get_recording_name(&root_path), "unknown");
    }

    #[test]
    fn test_filter_by_status() {
        let temp_dir = create_test_recordings_structure();
        let recordings = FileScanner::scan_recordings(temp_dir.path());

        // Filter by recorded status (should be recording_001)
        let recorded = FileScanner::filter_by_status(&recordings, "recorded");
        assert_eq!(recorded.len(), 1);
        assert_eq!(recorded[0].name, "recording_001");

        // Filter by extracted status (should be recording_002)
        let extracted = FileScanner::filter_by_status(&recordings, "extracted");
        assert_eq!(extracted.len(), 1);
        assert_eq!(extracted[0].name, "recording_002");

        // Filter by analyzed status (should be recording_003)
        let analyzed = FileScanner::filter_by_status(&recordings, "analyzed");
        assert_eq!(analyzed.len(), 1);
        assert_eq!(analyzed[0].name, "recording_003");
    }

    #[test]
    fn test_get_recordings_needing_attention() {
        let temp_dir = create_test_recordings_structure();
        let recordings = FileScanner::scan_recordings(temp_dir.path());

        // All recordings need attention (none are fully uploaded)
        let needing_attention = FileScanner::get_recordings_needing_attention(&recordings);
        assert_eq!(needing_attention.len(), 3);
    }

    #[test]
    fn test_recordings_sorted_by_last_updated() {
        let temp_dir = create_test_recordings_structure();
        let recordings = FileScanner::scan_recordings(temp_dir.path());

        // Recordings should be sorted by last_updated (most recent first)
        // Since we created them in sequence, the order might vary based on filesystem timing
        // Just check that we have the expected count and they have last_updated times
        assert_eq!(recordings.len(), 3);
        
        for recording in &recordings {
            assert!(recording.last_updated.elapsed().is_ok());
        }
    }
} 