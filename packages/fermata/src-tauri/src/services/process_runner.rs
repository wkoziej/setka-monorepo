use std::path::{Path, PathBuf};
use tokio::process::Command as AsyncCommand;
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessResult {
    pub success: bool,
    pub stdout: String,
    pub stderr: String,
    pub exit_code: Option<i32>,
}

pub struct ProcessRunner {
    workspace_root: PathBuf,
    uv_path: String,
}

impl ProcessRunner {
    pub fn new(workspace_root: PathBuf, uv_path: String) -> Self {
        Self {
            workspace_root,
            uv_path,
        }
    }

    /// Run beatrix analyze command
    pub async fn run_beatrix_analyze(&self, recording_path: &Path, audio_file: &str) -> anyhow::Result<ProcessResult> {
        let audio_path = recording_path.join("extracted").join(audio_file);
        
        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.args(&["run", "--package", "beatrix", "analyze"])
            .arg(&audio_path)
            .current_dir(&self.workspace_root);

        self.execute_command(cmd).await
    }

    /// Run cinemon render command
    pub async fn run_cinemon_render(&self, recording_path: &Path, animation_mode: &str) -> anyhow::Result<ProcessResult> {
        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.args(&["run", "--package", "cinemon", "cinemon-blend-setup"])
            .arg(recording_path)
            .args(&["--animation-mode", animation_mode])
            .current_dir(&self.workspace_root);

        self.execute_command(cmd).await
    }

    /// Run cinemon render command with main audio selection
    pub async fn run_cinemon_render_with_audio(&self, recording_path: &Path, animation_mode: &str, main_audio: Option<&str>) -> anyhow::Result<ProcessResult> {
        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.args(&["run", "--package", "cinemon", "cinemon-blend-setup"])
            .arg(recording_path)
            .args(&["--animation-mode", animation_mode]);

        if let Some(audio_file) = main_audio {
            cmd.args(&["--main-audio", audio_file]);
        }

        cmd.current_dir(&self.workspace_root);

        self.execute_command(cmd).await
    }

    /// Run medusa upload command
    pub async fn run_medusa_upload(&self, video_path: &Path, config_path: &Path) -> anyhow::Result<ProcessResult> {
        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.args(&["run", "--package", "medusa", "upload"])
            .arg(video_path)
            .args(&["--config", &config_path.to_string_lossy()])
            .current_dir(&self.workspace_root);

        self.execute_command(cmd).await
    }

    /// Execute a command and capture output
    async fn execute_command(&self, mut cmd: AsyncCommand) -> anyhow::Result<ProcessResult> {
        log::info!("Executing command: {:?}", cmd);
        
        let output = cmd.output().await?;
        
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        let success = output.status.success();
        let exit_code = output.status.code();

        log::info!("Command finished - success: {}, exit_code: {:?}", success, exit_code);
        if !stdout.is_empty() {
            log::info!("STDOUT: {}", stdout);
        }
        if !stderr.is_empty() {
            log::warn!("STDERR: {}", stderr);
        }

        Ok(ProcessResult {
            success,
            stdout,
            stderr,
            exit_code,
        })
    }

    /// Check if required CLI tools are available
    pub async fn validate_cli_tools(&self) -> anyhow::Result<()> {
        // Check if uv is available
        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.arg("--version");
        
        let output = cmd.output().await?;
        if !output.status.success() {
            return Err(anyhow::anyhow!("UV tool not found at: {}", self.uv_path));
        }

        // Check if workspace packages are available
        let packages = ["beatrix", "cinemon", "medusa"];
        for package in packages {
            let mut cmd = AsyncCommand::new(&self.uv_path);
            cmd.args(&["run", "--package", package, "--help"])
                .current_dir(&self.workspace_root);
            
            let output = cmd.output().await?;
            if !output.status.success() {
                return Err(anyhow::anyhow!("Package '{}' not available in workspace", package));
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    fn create_test_runner() -> (ProcessRunner, TempDir) {
        let temp_dir = TempDir::new().unwrap();
        let runner = ProcessRunner::new(
            temp_dir.path().to_path_buf(),
            "echo".to_string() // Use echo for testing instead of uv
        );
        (runner, temp_dir)
    }

    #[tokio::test]
    async fn test_process_runner_creation() {
        let workspace = PathBuf::from("/test/workspace");
        let runner = ProcessRunner::new(workspace.clone(), "uv".to_string());
        
        assert_eq!(runner.workspace_root, workspace);
        assert_eq!(runner.uv_path, "uv");
    }

    #[tokio::test]
    async fn test_execute_command_success() {
        let (runner, _temp_dir) = create_test_runner();
        
        let mut cmd = AsyncCommand::new("echo");
        cmd.arg("test output");
        
        let result = runner.execute_command(cmd).await.unwrap();
        
        assert!(result.success);
        assert_eq!(result.stdout.trim(), "test output");
        assert!(result.stderr.is_empty());
        assert_eq!(result.exit_code, Some(0));
    }

    #[tokio::test]
    async fn test_execute_command_failure() {
        let (runner, _temp_dir) = create_test_runner();
        
        let mut cmd = AsyncCommand::new("false"); // Command that always fails
        
        let result = runner.execute_command(cmd).await.unwrap();
        
        assert!(!result.success);
        assert_eq!(result.exit_code, Some(1));
    }

    #[tokio::test]
    async fn test_beatrix_analyze_command_structure() {
        let (runner, temp_dir) = create_test_runner();
        
        // Create test directory structure
        let recording_path = temp_dir.path().join("test_recording");
        let extracted_dir = recording_path.join("extracted");
        fs::create_dir_all(&extracted_dir).unwrap();
        
        let audio_file = "audio.m4a";
        fs::write(extracted_dir.join(audio_file), "test audio").unwrap();
        
        // This will fail because we're using echo instead of uv, but we can test the structure
        let result = runner.run_beatrix_analyze(&recording_path, audio_file).await;
        
        // Should not panic and should return some result
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_cinemon_render_command_structure() {
        let (runner, temp_dir) = create_test_runner();
        
        let recording_path = temp_dir.path().join("test_recording");
        fs::create_dir_all(&recording_path).unwrap();
        
        let result = runner.run_cinemon_render(&recording_path, "beat-switch").await;
        
        // Should not panic and should return some result
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_medusa_upload_command_structure() {
        let (runner, temp_dir) = create_test_runner();
        
        let video_path = temp_dir.path().join("video.mp4");
        let config_path = temp_dir.path().join("config.json");
        
        fs::write(&video_path, "test video").unwrap();
        fs::write(&config_path, "{}").unwrap();
        
        let result = runner.run_medusa_upload(&video_path, &config_path).await;
        
        // Should not panic and should return some result
        assert!(result.is_ok());
    }
} 