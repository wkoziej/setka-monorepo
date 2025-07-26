use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::time::SystemTime;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Recording {
    pub name: String,
    pub path: PathBuf,
    pub status: RecordingStatus,
    pub last_updated: u64, // Unix timestamp in seconds
    pub file_sizes: HashMap<String, u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RecordingStatus {
    Recorded,       // .mkv exists
    Extracted,      // extracted/ exists
    Analyzed,       // analysis/ exists
    SetupRendered,  // blender/*.blend exists (cinemon done)
    Rendered,       // blender/render/*.mp4 exists (blender rendering done)
    Uploaded,       // uploads/ exists
    Failed(String),
}

impl Recording {
    /// Create a new Recording from a directory path
    pub fn from_path(path: PathBuf) -> anyhow::Result<Self> {
        let name = path
            .file_name()
            .and_then(|n| n.to_str())
            .ok_or_else(|| anyhow::anyhow!("Invalid recording directory name"))?
            .to_string();

        // Get last modified time of the directory
        let metadata = std::fs::metadata(&path)?;
        let last_updated = metadata.modified()?;

        Ok(Recording {
            name,
            path: path.clone(),
            status: RecordingStatus::Recorded, // Will be updated by status detection
            last_updated: last_updated.duration_since(SystemTime::UNIX_EPOCH)?.as_secs(),
            file_sizes: HashMap::new(), // Will be populated by file scanner
        })
    }

    /// Get the next step in the pipeline based on current status
    pub fn get_next_step(&self) -> Option<NextStep> {
        match &self.status {
            RecordingStatus::Recorded => Some(NextStep::Extract),
            RecordingStatus::Extracted => Some(NextStep::Analyze),
            RecordingStatus::Analyzed => Some(NextStep::SetupRender),
            RecordingStatus::SetupRendered => Some(NextStep::Render),
            RecordingStatus::Rendered => Some(NextStep::Upload),
            RecordingStatus::Uploaded => None,
            RecordingStatus::Failed(_) => Some(NextStep::Retry),
        }
    }

    /// Check if a specific step can be run for this recording
    pub fn can_run_step(&self, step: &str) -> bool {
        match step.to_lowercase().as_str() {
            "extract" => matches!(self.status, RecordingStatus::Recorded | RecordingStatus::Failed(_)),
            "analyze" => matches!(self.status, RecordingStatus::Extracted | RecordingStatus::Failed(_)),
            "setup_render" | "setup-render" => matches!(self.status, RecordingStatus::Analyzed | RecordingStatus::Failed(_)),
            "render" => matches!(self.status, RecordingStatus::SetupRendered | RecordingStatus::Failed(_)),
            "upload" => matches!(self.status, RecordingStatus::Rendered | RecordingStatus::Failed(_)),
            "retry" => matches!(self.status, RecordingStatus::Failed(_)),
            _ => false,
        }
    }

    /// Get list of available steps for this recording
    pub fn get_available_steps(&self) -> Vec<String> {
        let mut steps = Vec::new();

        if let Some(next_step) = self.get_next_step() {
            steps.push(next_step.to_string());
        }

        // Add manual step options based on current status
        match &self.status {
            RecordingStatus::Extracted => {
                steps.push("extract".to_string()); // Re-extract if needed
            }
            RecordingStatus::Analyzed => {
                steps.extend(["extract".to_string(), "analyze".to_string()]);
            }
            RecordingStatus::Rendered => {
                steps.extend(["extract".to_string(), "analyze".to_string(), "render".to_string()]);
            }
            RecordingStatus::Uploaded => {
                steps.extend(["extract".to_string(), "analyze".to_string(), "render".to_string(), "upload".to_string()]);
            }
            _ => {}
        }

        steps
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum NextStep {
    Extract,
    Analyze,
    SetupRender,
    Render,
    Upload,
    Retry,
}

impl NextStep {
    pub fn to_string(&self) -> String {
        match self {
            NextStep::Extract => "Extract".to_string(),
            NextStep::Analyze => "Analyze".to_string(),
            NextStep::SetupRender => "Setup Render".to_string(),
            NextStep::Render => "Render".to_string(),
            NextStep::Upload => "Upload".to_string(),
            NextStep::Retry => "Retry".to_string(),
        }
    }
}

impl std::fmt::Display for NextStep {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            NextStep::Extract => write!(f, "extract"),
            NextStep::Analyze => write!(f, "analyze"),
            NextStep::SetupRender => write!(f, "setup_render"),
            NextStep::Render => write!(f, "render"),
            NextStep::Upload => write!(f, "upload"),
            NextStep::Retry => write!(f, "retry"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    #[test]
    fn test_recording_creation_from_valid_path() {
        let path = PathBuf::from("/test/stream_20240115_120000");
        let recording = Recording::from_path(path.clone()).unwrap();

        assert_eq!(recording.name, "stream_20240115_120000");
        assert_eq!(recording.path, path);
        assert_eq!(recording.status, RecordingStatus::Recorded);
        assert!(recording.file_sizes.is_empty());
    }

    #[test]
    fn test_recording_creation_from_invalid_path() {
        let path = PathBuf::from("/");
        let result = Recording::from_path(path);

        assert!(result.is_err());
    }

    #[test]
    fn test_get_next_step_for_each_status() {
        let base_recording = Recording {
            name: "test".to_string(),
            path: PathBuf::from("/test"),
            status: RecordingStatus::Recorded,
            last_updated: SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs(),
            file_sizes: HashMap::new(),
        };

        // Test each status transition
        let mut recording = base_recording.clone();
        recording.status = RecordingStatus::Recorded;
        assert_eq!(recording.get_next_step(), Some(NextStep::Extract));

        recording.status = RecordingStatus::Extracted;
        assert_eq!(recording.get_next_step(), Some(NextStep::Analyze));

        recording.status = RecordingStatus::Analyzed;
        assert_eq!(recording.get_next_step(), Some(NextStep::SetupRender));

        recording.status = RecordingStatus::SetupRendered;
        assert_eq!(recording.get_next_step(), Some(NextStep::Render));

        recording.status = RecordingStatus::Rendered;
        assert_eq!(recording.get_next_step(), Some(NextStep::Upload));

        recording.status = RecordingStatus::Uploaded;
        assert_eq!(recording.get_next_step(), None);

        recording.status = RecordingStatus::Failed("test error".to_string());
        assert_eq!(recording.get_next_step(), Some(NextStep::Retry));
    }

    #[test]
    fn test_can_run_step() {
        let mut recording = Recording {
            name: "test".to_string(),
            path: PathBuf::from("/test"),
            status: RecordingStatus::Extracted,
            last_updated: SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs(),
            file_sizes: HashMap::new(),
        };

        // Test valid step for current status
        assert!(recording.can_run_step("analyze"));
        assert!(!recording.can_run_step("render"));

        // Test failed status can retry any previous step
        recording.status = RecordingStatus::Failed("error".to_string());
        assert!(recording.can_run_step("extract"));
        assert!(recording.can_run_step("analyze"));
        assert!(recording.can_run_step("render"));
        assert!(recording.can_run_step("upload"));
        assert!(recording.can_run_step("retry"));
    }

    #[test]
    fn test_get_available_steps() {
        let mut recording = Recording {
            name: "test".to_string(),
            path: PathBuf::from("/test"),
            status: RecordingStatus::Analyzed,
            last_updated: SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs(),
            file_sizes: HashMap::new(),
        };

        let steps = recording.get_available_steps();
        assert!(steps.contains(&"render".to_string())); // Next step
        assert!(steps.contains(&"extract".to_string())); // Manual re-run
        assert!(steps.contains(&"analyze".to_string())); // Manual re-run
    }

    #[test]
    fn test_recording_status_serialization() {
        // Test serialization of different status variants
        let status_recorded = RecordingStatus::Recorded;
        let status_failed = RecordingStatus::Failed("Test error message".to_string());

        // These should not panic
        let _serialized_recorded = serde_json::to_string(&status_recorded).unwrap();
        let _serialized_failed = serde_json::to_string(&status_failed).unwrap();
    }

    #[test]
    fn test_next_step_display() {
        assert_eq!(NextStep::Extract.to_string(), "Extract");
        assert_eq!(NextStep::Analyze.to_string(), "Analyze");
        assert_eq!(NextStep::SetupRender.to_string(), "Setup Render");
        assert_eq!(NextStep::Render.to_string(), "Render");
        assert_eq!(NextStep::Upload.to_string(), "Upload");
        assert_eq!(NextStep::Retry.to_string(), "Retry");
    }
}
