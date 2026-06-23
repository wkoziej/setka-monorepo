use std::path::{Path, PathBuf};
use std::time::Duration;
use tokio::process::Command as AsyncCommand;
use serde::{Serialize, Deserialize};

/// Timeout for pipeline subprocesses that should finish promptly
/// (beatrix analyze, structure brief, medusa upload, tool probes).
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(30 * 60);
/// Longer ceiling for the cymatic/Blender render, which is compute-heavy.
const RENDER_TIMEOUT: Duration = Duration::from_secs(2 * 60 * 60);
/// Short ceiling for the `--help`/`--version` reachability probes in startup
/// validation, so a missing/hung tool fails fast instead of blocking launch.
const PROBE_TIMEOUT: Duration = Duration::from_secs(60);

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

    /// Run beatrix analyze on a whole recording.
    /// beatrix analyze-recording selects audio sources itself (mixed/ master + stems,
    /// extracted/ fallback) and writes one {stem}_analysis.json per file.
    pub async fn run_beatrix_analyze(&self, recording_path: &Path) -> anyhow::Result<ProcessResult> {
        log::info!("🎵 Running beatrix analyze-recording: {}", recording_path.display());

        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.args(&["run", "--package", "beatrix", "beatrix", "analyze-recording"])
            .arg(recording_path)
            .current_dir(&self.workspace_root);

        self.execute_command(cmd).await
    }

    /// Run cymatic structure-brief on a recording (best-effort companion to analyze).
    /// Writes analysis/structure_brief.{json,md,ass} + structure_map.png from the
    /// beatrix analyses, used by the fermata "Structure map" preview and Play + Brief.
    pub async fn run_cymatic_structure_brief(
        &self,
        recording_path: &Path,
    ) -> anyhow::Result<ProcessResult> {
        log::info!(
            "📊 Running cymatic-structure-brief: {}",
            recording_path.display()
        );

        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.args(&["run", "--package", "cymatic", "cymatic-structure-brief"])
            .arg(recording_path)
            .current_dir(&self.workspace_root);

        self.execute_command(cmd).await
    }

    /// Render the 3D Geometry Nodes audio visualizer for a recording.
    ///
    /// Drives `cymatic-render <recording_dir> [--main-audio NAME]`. cymatic
    /// resolves the beatrix `*_analysis.json` itself (auto-detecting the main
    /// audio in `extracted/`, or using `--main-audio` as a hint) and writes the
    /// final mp4 under `blender/render/`. This replaces the retired cinemon VSE
    /// path; there is no separate config-generation step.
    pub async fn run_cymatic_render(
        &self,
        recording_path: &Path,
        main_audio: Option<&str>,
    ) -> anyhow::Result<ProcessResult> {
        log::info!(
            "🎬 Running cymatic-render: {} (main_audio={:?})",
            recording_path.display(),
            main_audio
        );

        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.args(["run", "--package", "cymatic", "cymatic-render"])
            .arg(recording_path);

        if let Some(audio_file) = main_audio {
            cmd.args(["--main-audio", audio_file]);
        }

        cmd.current_dir(&self.workspace_root);
        // Rendering drives Blender and can run for a long time.
        self.execute_command_with_timeout(cmd, RENDER_TIMEOUT).await
    }

    /// Run medusa upload command
    pub async fn run_medusa_upload(&self, video_path: &Path, config_path: &Path) -> anyhow::Result<ProcessResult> {
        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.args(&["run", "medusa", "upload"])
            .arg(video_path)
            .args(&["--config", &config_path.to_string_lossy()])
            .current_dir(&self.workspace_root);

        self.execute_command(cmd).await
    }

    /// Execute a command and capture output, bounded by DEFAULT_TIMEOUT.
    async fn execute_command(&self, cmd: AsyncCommand) -> anyhow::Result<ProcessResult> {
        self.execute_command_with_timeout(cmd, DEFAULT_TIMEOUT).await
    }

    /// Execute a command with an explicit timeout. On timeout the child is killed
    /// and an error is returned, so a hung subprocess never blocks the UI forever.
    ///
    /// stdout/stderr are drained on dedicated tasks while we wait, so a chatty
    /// subprocess (e.g. Blender) can't deadlock by filling a pipe buffer.
    async fn execute_command_with_timeout(
        &self,
        mut cmd: AsyncCommand,
        timeout: Duration,
    ) -> anyhow::Result<ProcessResult> {
        use tokio::io::AsyncReadExt;

        log::info!("Executing command (timeout {:?}): {:?}", timeout, cmd);

        // Spawn with piped output so we can both drain and kill the child.
        cmd.stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped());
        let mut child = cmd.spawn()?;

        // Drain stdout/stderr concurrently to avoid pipe-buffer deadlock.
        let mut child_stdout = child.stdout.take();
        let mut child_stderr = child.stderr.take();
        let stdout_task = tokio::spawn(async move {
            let mut buf = Vec::new();
            if let Some(out) = child_stdout.as_mut() {
                let _ = out.read_to_end(&mut buf).await;
            }
            buf
        });
        let stderr_task = tokio::spawn(async move {
            let mut buf = Vec::new();
            if let Some(err) = child_stderr.as_mut() {
                let _ = err.read_to_end(&mut buf).await;
            }
            buf
        });

        let status = match tokio::time::timeout(timeout, child.wait()).await {
            Ok(res) => res?,
            Err(_elapsed) => {
                // Kill the overrunning child so it doesn't linger.
                let _ = child.kill().await;
                return Err(anyhow::anyhow!("Command timed out after {:?}", timeout));
            }
        };

        let stdout_bytes = stdout_task.await.unwrap_or_default();
        let stderr_bytes = stderr_task.await.unwrap_or_default();
        let stdout = String::from_utf8_lossy(&stdout_bytes).to_string();
        let stderr = String::from_utf8_lossy(&stderr_bytes).to_string();
        let success = status.success();
        let exit_code = status.code();

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

    /// Check if required CLI tools are available. Each probe is bounded by
    /// PROBE_TIMEOUT so a hung tool fails fast at startup instead of blocking.
    pub async fn validate_cli_tools(&self) -> anyhow::Result<()> {
        // Check if uv is available
        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.arg("--version");
        let result = self.execute_command_with_timeout(cmd, PROBE_TIMEOUT).await?;
        if !result.success {
            return Err(anyhow::anyhow!("UV tool not found at: {}", self.uv_path));
        }

        // Check if workspace packages are available
        // beatrix: Python module
        let mut cmd = AsyncCommand::new(&self.uv_path);
        cmd.args(["run", "--package", "beatrix", "python", "-m", "beatrix", "--help"])
            .current_dir(&self.workspace_root);
        let result = self.execute_command_with_timeout(cmd, PROBE_TIMEOUT).await?;
        if !result.success {
            return Err(anyhow::anyhow!("Package 'beatrix' not available in workspace"));
        }

        // cymatic and medusa: CLI entry points (cinemon retired).
        let packages = ["cymatic", "medusa"];
        for package in packages {
            let mut cmd = AsyncCommand::new(&self.uv_path);
            cmd.args(["run", "--package", package, "--help"])
                .current_dir(&self.workspace_root);
            let result = self.execute_command_with_timeout(cmd, PROBE_TIMEOUT).await?;
            if !result.success {
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
    async fn test_execute_command_times_out() {
        let (runner, _temp_dir) = create_test_runner();

        // `sleep 30` far exceeds the 100ms timeout → must Err, not hang.
        let mut cmd = AsyncCommand::new("sleep");
        cmd.arg("30");

        let result = runner
            .execute_command_with_timeout(cmd, std::time::Duration::from_millis(100))
            .await;

        assert!(result.is_err(), "overrunning command must time out");
        assert!(result.unwrap_err().to_string().contains("timed out"));
    }

    #[tokio::test]
    async fn test_beatrix_analyze_command_structure() {
        let (runner, temp_dir) = create_test_runner();

        // Create test directory structure
        let recording_path = temp_dir.path().join("test_recording");
        fs::create_dir_all(&recording_path).unwrap();

        // echo stands in for uv, so stdout echoes the constructed command line.
        let result = runner.run_beatrix_analyze(&recording_path).await;

        // Should not panic and should return some result
        assert!(result.is_ok());
        let process_result = result.unwrap();
        // Uses the directory-mode subcommand on the recording, not the old
        // per-file analyze against extracted/<file>.
        assert!(process_result.stdout.contains("analyze-recording"));
        assert!(!process_result.stdout.contains("extracted"));
    }

    #[tokio::test]
    async fn test_cymatic_render_command_structure() {
        let (runner, temp_dir) = create_test_runner();

        let recording_path = temp_dir.path().join("test_recording");
        fs::create_dir_all(&recording_path).unwrap();

        // echo stands in for uv, so stdout echoes the constructed command line.
        let result = runner.run_cymatic_render(&recording_path, None).await;

        assert!(result.is_ok());
        let process_result = result.unwrap();
        // Drives cymatic-render, not the retired cinemon CLIs.
        assert!(process_result.stdout.contains("cymatic-render"));
        assert!(!process_result.stdout.contains("cinemon"));
    }

    #[tokio::test]
    async fn test_cymatic_render_forwards_main_audio() {
        let (runner, temp_dir) = create_test_runner();

        let recording_path = temp_dir.path().join("test_recording");
        fs::create_dir_all(&recording_path).unwrap();

        let result = runner
            .run_cymatic_render(&recording_path, Some("master.wav"))
            .await
            .unwrap();
        assert!(result.stdout.contains("--main-audio"));
        assert!(result.stdout.contains("master.wav"));
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
