use crate::models::{Recording, RecordingStatus, NextStep};
use crate::services::{FileScanner, ProcessRunner, ProcessResult};
use crate::commands::recordings::AppConfig;
use tauri::State;
use serde::{Serialize, Deserialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct RenderOptions {
    pub preset: String,
    pub main_audio: Option<String>,
}

impl Default for RenderOptions {
    fn default() -> Self {
        Self {
            preset: "minimal".to_string(),  // Zachowanie kompatybilności
            main_audio: None,
        }
    }
}

/// Resolve the `--main-audio` target for a recording's render.
/// Prefers the polished Bitwig master at `mixed/master.wav` (returned as an absolute
/// path) so cymatic picks `master_analysis.json`. Returns None when the master is
/// absent, letting callers keep their existing audio resolution.
fn resolve_master_main_audio(recording_path: &std::path::Path) -> Option<String> {
    let master = recording_path.join("mixed").join("master.wav");
    if master.exists() {
        Some(master.to_string_lossy().to_string())
    } else {
        None
    }
}

/// Resolve the `--main-audio` to pass to cymatic-render for a recording.
///
/// Precedence: the polished `mixed/master.wav` (absolute path) wins; otherwise,
/// when `extracted/` holds multiple `.m4a` files we require the configured
/// `main_audio_file` to disambiguate (erroring if it is unset/absent); a single
/// audio file (or none) needs no override and returns `Ok(None)`, letting
/// cymatic auto-detect.
fn resolve_render_main_audio(
    recording_path: &std::path::Path,
    config: &AppConfig,
) -> Result<Option<String>, String> {
    if let Some(master_audio) = resolve_master_main_audio(recording_path) {
        log::info!("🎯 Using mixed master as main audio: {}", master_audio);
        return Ok(Some(master_audio));
    }

    let extracted_dir = recording_path.join("extracted");
    if !extracted_dir.exists() {
        return Ok(None);
    }

    let audio_files: Vec<String> = std::fs::read_dir(&extracted_dir)
        .map_err(|e| format!("Failed to read extracted directory: {}", e))?
        .filter_map(|entry| {
            let entry = entry.ok()?;
            let path = entry.path();
            if path.extension()?.to_str()? == "m4a" {
                path.file_name()?.to_str().map(|s| s.to_string())
            } else {
                None
            }
        })
        .collect();

    log::info!("🎵 Found {} audio file(s) for render: {:?}", audio_files.len(), audio_files);

    if audio_files.len() > 1 {
        if !config.main_audio_file.is_empty() && audio_files.contains(&config.main_audio_file) {
            log::info!("🎯 Using configured main audio: {}", config.main_audio_file);
            Ok(Some(config.main_audio_file.clone()))
        } else {
            log::warn!(
                "⚠️ Multiple audio files found but main audio '{}' not available in: {:?}",
                config.main_audio_file,
                audio_files
            );
            Err(format!(
                "Multiple audio files found: {:?}. Configure FERMATA_MAIN_AUDIO environment variable to specify which one to use.",
                audio_files
            ))
        }
    } else {
        // Single audio file or none: let cymatic auto-detect from extracted/.
        Ok(None)
    }
}

/// Run the next step in the pipeline for a specific recording
#[tauri::command]
pub async fn run_next_step(recording_name: String, config: State<'_, AppConfig>) -> Result<String, String> {
    log::info!("🚀 [run_next_step] Called for recording: {}", recording_name);

    // Get the recording details first
    log::info!("📁 [run_next_step] Scanning recordings from: {}", config.recordings_path.display());
    let recordings = FileScanner::scan_recordings(&config.recordings_path);
    log::info!("🔍 [run_next_step] Found {} recordings total", recordings.len());

    let recording = recordings
        .into_iter()
        .find(|r| r.name == recording_name)
        .ok_or_else(|| {
            log::error!("❌ [run_next_step] Recording '{}' not found", recording_name);
            format!("Recording '{}' not found", recording_name)
        })?;

    log::info!("✅ [run_next_step] Found recording: {}, status: {:?}", recording.name, recording.status);

    // Determine next step
    let next_step = recording
        .get_next_step()
        .ok_or_else(|| format!("No next step available for recording '{}'", recording_name))?;

    log::info!("Next step for '{}': {:?}", recording_name, next_step);

    // Execute the step
    let result = execute_step(&recording, &next_step, &config).await?;

    if result.success {
        Ok(format!("Successfully completed {} for {}", next_step.to_string().to_lowercase(), recording_name))
    } else {
        Err(format!("Failed to execute {}: {}", next_step.to_string().to_lowercase(), result.stderr))
    }
}

/// Run a specific step for a recording
#[tauri::command]
pub async fn run_specific_step(
    recording_name: String,
    step: String,
    config: State<'_, AppConfig>
) -> Result<String, String> {
    log::info!("🚀 [run_specific_step] Called for recording: {}, step: {}", recording_name, step);

    // Get the recording details first
    let recordings = FileScanner::scan_recordings(&config.recordings_path);
    let recording = recordings
        .into_iter()
        .find(|r| r.name == recording_name)
        .ok_or_else(|| format!("Recording '{}' not found", recording_name))?;

    // Validate that the step can be run
    if !recording.can_run_step(&step) {
        return Err(format!("Step '{}' cannot be run for recording '{}' in current status: {:?}",
                          step, recording_name, recording.status));
    }

    // Parse step to NextStep enum
    let next_step = match step.to_lowercase().as_str() {
        "analyze" => NextStep::Analyze,
        "setup_render" | "setup-render" => NextStep::SetupRender,
        "render" => NextStep::Render,
        "upload" => NextStep::Upload,
        "retry" => {
            // For retry, determine what step to retry based on current status
            match recording.status {
                RecordingStatus::Failed(_) => {
                    // Try to determine what step failed and retry it
                    if recording.path.join("blender").join("render").exists() {
                        NextStep::Render
                    } else if recording.path.join("blender").exists() {
                        NextStep::SetupRender
                    } else if recording.path.join("analysis").exists() {
                        NextStep::SetupRender
                    } else if recording.path.join("extracted").exists() {
                        NextStep::Analyze
                    } else {
                        return Err("Cannot determine retry step".to_string());
                    }
                }
                _ => return Err("Retry only available for failed recordings".to_string()),
            }
        }
        _ => return Err(format!("Unknown step: {}", step)),
    };

    log::info!("Executing step {:?} for '{}'", next_step, recording_name);

    // Execute the step
    let result = execute_step(&recording, &next_step, &config).await?;

    if result.success {
        Ok(format!("Successfully completed {} for {}", step, recording_name))
    } else {
        Err(format!("Failed to execute {}: {}", step, result.stderr))
    }
}

/// Execute a specific pipeline step
async fn execute_step(
    recording: &Recording,
    step: &NextStep,
    config: &AppConfig
) -> Result<ProcessResult, String> {
    let runner = ProcessRunner::new(
        config.cli_paths.workspace_root.clone(),
        config.cli_paths.uv_path.clone()
    );

    let result = match step {
        NextStep::Extract => {
            // Note: Extract step is typically done by obsession, not part of fermata scope
            return Err("Extract step not implemented in fermata - use obsession package".to_string());
        }
        NextStep::Analyze => {
            // beatrix analyze-recording resolves audio sources itself (mixed/ master +
            // stems, extracted/ fallback) and reports missing audio or stem-name
            // collisions via a non-zero exit + stderr, which the caller surfaces as Err.
            log::info!("🎵 Running analyze for recording: {}", recording.path.display());
            let analyze_result = runner.run_beatrix_analyze(&recording.path).await;

            // Best-effort: generate the structure brief once analysis succeeded so the
            // recording gets its brief/heatmap/ASS automatically. A brief failure must
            // NOT fail the analyze step — beatrix's analyses are the primary result.
            if let Ok(ref r) = analyze_result {
                if r.success {
                    match runner.run_cymatic_structure_brief(&recording.path).await {
                        Ok(b) if b.success => {
                            log::info!("📊 Structure brief generated")
                        }
                        Ok(b) => log::warn!(
                            "Structure brief skipped (best-effort): exit {:?}: {}",
                            b.exit_code,
                            b.stderr
                        ),
                        Err(e) => {
                            log::warn!("Structure brief skipped (best-effort): {}", e)
                        }
                    }
                }
            }

            analyze_result
        }
        NextStep::SetupRender | NextStep::Render => {
            // cymatic-render does setup + render in one shot (no separate cinemon
            // config/blend step), so SetupRender and Render both drive cymatic.
            if !recording.path.join("analysis").exists() {
                return Err("Analysis directory not found - run analyze step first".to_string());
            }

            let main_audio = resolve_render_main_audio(&recording.path, config)?;
            log::info!("🎬 cymatic-render main_audio: {:?}", main_audio);
            runner.run_cymatic_render(&recording.path, main_audio.as_deref()).await
        }
        NextStep::Upload => {
            // Check if render output exists
            let render_dir = recording.path.join("blender").join("render");
            if !render_dir.exists() {
                return Err("Render directory not found - run render step first".to_string());
            }

            // Find video file
            let video_files: Vec<_> = std::fs::read_dir(&render_dir)
                .map_err(|e| format!("Failed to read render directory: {}", e))?
                .filter_map(|entry| {
                    let entry = entry.ok()?;
                    let path = entry.path();
                    if path.extension()?.to_str()? == "mp4" {
                        Some(path)
                    } else {
                        None
                    }
                })
                .collect();

            if video_files.is_empty() {
                return Err("No video file (.mp4) found in render directory".to_string());
            }

            // For MVP, use a default config - in future this should be configurable
            let config_path = config.cli_paths.workspace_root.join("packages/medusa/examples/config_example.json");
            if !config_path.exists() {
                return Err("Medusa config not found - check medusa package setup".to_string());
            }

            runner.run_medusa_upload(&video_files[0], &config_path).await
        }
        NextStep::Retry => {
            return Err("Retry step should be resolved to specific step before execution".to_string());
        }
    }
    .map_err(|e| format!("Command execution failed: {}", e))?;

    Ok(result)
}

#[tauri::command]
pub async fn run_specific_step_with_options(
    recording_name: String,
    step: String,
    options: Option<RenderOptions>,
    config: State<'_, AppConfig>
) -> Result<String, String> {
    log::info!("🚀 [run_specific_step_with_options] Called for recording: {}, step: {}, options: {:?}", recording_name, step, options);

    // Get the recording details first
    let recordings = FileScanner::scan_recordings(&config.recordings_path);
    let recording = recordings
        .into_iter()
        .find(|r| r.name == recording_name)
        .ok_or_else(|| format!("Recording '{}' not found", recording_name))?;

    match step.as_str() {
        "setuprender" => {
            let opts = options.unwrap_or_default();
            let result = execute_step_with_preset(&recording, &NextStep::SetupRender, &config, &opts.preset, opts.main_audio.as_deref()).await?;

            if result.success {
                Ok(format!("✅ Render setup completed with preset: {}", opts.preset))
            } else {
                Err(format!("❌ Render setup failed: {}", result.stderr))
            }
        },
        _ => {
            // Zachować istniejące step handling dla innych kroków
            run_specific_step(recording_name, step, config).await
        }
    }
}

/// Execute a render step with an explicit main-audio override.
///
/// `preset` is retained for UI/back-compat but is a no-op for cymatic (the GN
/// visualizer has no preset concept); only the audio selection is honored.
async fn execute_step_with_preset(
    recording: &Recording,
    step: &NextStep,
    config: &AppConfig,
    preset: &str,
    main_audio: Option<&str>
) -> Result<ProcessResult, String> {
    let runner = ProcessRunner::new(
        config.cli_paths.workspace_root.clone(),
        config.cli_paths.uv_path.clone()
    );

    match step {
        NextStep::SetupRender | NextStep::Render => {
            // Check if analysis exists
            if !recording.path.join("analysis").exists() {
                return Err("Analysis directory not found - run analyze step first".to_string());
            }

            // Prefer an explicit main_audio; otherwise resolve as the default render
            // path does (mixed master, configured multi-audio, or auto-detect).
            let resolved_audio = match main_audio {
                Some(a) => Some(a.to_string()),
                None => resolve_render_main_audio(&recording.path, config)?,
            };

            log::info!(
                "🎬 cymatic-render (preset '{}' ignored by GN visualizer), main_audio: {:?}",
                preset,
                resolved_audio
            );
            runner.run_cymatic_render(&recording.path, resolved_audio.as_deref()).await
                .map_err(|e| format!("Command execution failed: {}", e))
        }
        _ => {
            // Fallback to regular execute_step for other steps
            execute_step(recording, step, config).await
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    fn create_test_config(temp_dir: &TempDir) -> AppConfig {
        AppConfig {
            recordings_path: temp_dir.path().to_path_buf(),
            cli_paths: crate::commands::recordings::CliPaths {
                uv_path: "echo".to_string(), // Use echo for testing
                workspace_root: temp_dir.path().to_path_buf(),
            },
            main_audio_file: "".to_string(), // Default to empty for testing
        }
    }

    fn create_test_recording(temp_dir: &TempDir, name: &str, status: RecordingStatus) -> Recording {
        let recording_path = temp_dir.path().join(name);
        fs::create_dir_all(&recording_path).unwrap();

        // Create appropriate directory structure based on status
        match status {
            RecordingStatus::Extracted => {
                fs::create_dir_all(recording_path.join("extracted")).unwrap();
                fs::write(recording_path.join("extracted").join("audio.m4a"), "test audio").unwrap();
            }
            RecordingStatus::Analyzed => {
                fs::create_dir_all(recording_path.join("extracted")).unwrap();
                fs::write(recording_path.join("extracted").join("audio.m4a"), "test audio").unwrap();
                fs::create_dir_all(recording_path.join("analysis")).unwrap();
                fs::write(recording_path.join("analysis").join("analysis.json"), "{}").unwrap();
            }
            RecordingStatus::Rendered => {
                fs::create_dir_all(recording_path.join("extracted")).unwrap();
                fs::write(recording_path.join("extracted").join("audio.m4a"), "test audio").unwrap();
                fs::create_dir_all(recording_path.join("analysis")).unwrap();
                fs::write(recording_path.join("analysis").join("analysis.json"), "{}").unwrap();
                fs::create_dir_all(recording_path.join("blender").join("render")).unwrap();
                fs::write(recording_path.join("blender").join("render").join("final.mp4"), "test video").unwrap();
            }
            _ => {
                // Just create basic recording directory
                fs::write(recording_path.join("recording.mp4"), "test video").unwrap();
            }
        }

        Recording {
            name: name.to_string(),
            path: recording_path,
            status,
            last_updated: std::time::SystemTime::now().duration_since(std::time::SystemTime::UNIX_EPOCH).unwrap().as_secs(),
            file_sizes: std::collections::HashMap::new(),
        }
    }

    #[tokio::test]
    async fn test_run_next_step_for_extracted_recording() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_test_config(&temp_dir);

        // Create extracted recording
        create_test_recording(&temp_dir, "test_recording", RecordingStatus::Extracted);

        // This will use echo instead of real uv, so it should succeed
        let result = execute_step(
            &Recording {
                name: "test_recording".to_string(),
                path: temp_dir.path().join("test_recording"),
                status: RecordingStatus::Extracted,
                last_updated: std::time::SystemTime::now().duration_since(std::time::SystemTime::UNIX_EPOCH).unwrap().as_secs(),
                file_sizes: std::collections::HashMap::new(),
            },
            &NextStep::Analyze,
            &config
        ).await;

        assert!(result.is_ok());
        let process_result = result.unwrap();
        assert!(process_result.success);
    }

    #[tokio::test]
    async fn test_run_specific_step_validation() {
        let temp_dir = TempDir::new().unwrap();
        let _config = create_test_config(&temp_dir);

        let recording = create_test_recording(&temp_dir, "test_recording", RecordingStatus::Recorded);

        // Should not be able to run render on recorded status
        assert!(!recording.can_run_step("render"));

        // Should be able to run analyze on extracted status
        let extracted_recording = create_test_recording(&temp_dir, "test_recording2", RecordingStatus::Extracted);
        assert!(extracted_recording.can_run_step("analyze"));
    }

    #[tokio::test]
    async fn test_setup_render_requires_analysis_dir() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_test_config(&temp_dir);

        // SetupRender still guards on the analysis directory existing first.
        let recording = create_test_recording(&temp_dir, "test_recording", RecordingStatus::Recorded);

        let result = execute_step(&recording, &NextStep::SetupRender, &config).await;
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Analysis directory not found"));
    }

    #[tokio::test]
    async fn test_analyze_step_invokes_analyze_recording_subcommand() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_test_config(&temp_dir);

        // No extracted/ directory: source selection now lives in beatrix, so the Rust
        // side no longer pre-checks extracted/ nor filters .m4a.
        let recording = create_test_recording(&temp_dir, "test_recording", RecordingStatus::Recorded);

        let result = execute_step(&recording, &NextStep::Analyze, &config).await;
        assert!(result.is_ok());
        let process_result = result.unwrap();
        assert!(process_result.success);
        // echo stub: stdout echoes the constructed command line.
        assert!(process_result.stdout.contains("analyze-recording"));
        assert!(!process_result.stdout.contains("extracted"));
    }

    #[tokio::test]
    async fn test_analyze_step_surfaces_beatrix_failure() {
        let temp_dir = TempDir::new().unwrap();
        // `false` stands in for a beatrix run that exits non-zero (e.g. no audio).
        let config = AppConfig {
            recordings_path: temp_dir.path().to_path_buf(),
            cli_paths: crate::commands::recordings::CliPaths {
                uv_path: "false".to_string(),
                workspace_root: temp_dir.path().to_path_buf(),
            },
            main_audio_file: "".to_string(),
        };

        let recording = create_test_recording(&temp_dir, "test_recording", RecordingStatus::Extracted);

        let result = execute_step(&recording, &NextStep::Analyze, &config).await;
        // execute_step returns Ok with the failed ProcessResult; run_specific_step turns
        // !success into Err(stderr) for the UI.
        assert!(result.is_ok());
        assert!(!result.unwrap().success);
    }

    #[test]
    fn test_resolve_master_main_audio_prefers_mixed_master() {
        let temp_dir = TempDir::new().unwrap();
        let recording_path = temp_dir.path().join("rec");
        let mixed_dir = recording_path.join("mixed");
        fs::create_dir_all(&mixed_dir).unwrap();
        fs::write(mixed_dir.join("master.wav"), "wav").unwrap();

        let resolved = resolve_master_main_audio(&recording_path);
        assert_eq!(resolved, Some(mixed_dir.join("master.wav").to_string_lossy().to_string()));
    }

    #[test]
    fn test_resolve_master_main_audio_none_when_absent() {
        let temp_dir = TempDir::new().unwrap();
        let recording_path = temp_dir.path().join("rec");
        fs::create_dir_all(&recording_path).unwrap();

        assert_eq!(resolve_master_main_audio(&recording_path), None);
    }

    #[tokio::test]
    async fn test_setup_render_uses_mixed_master_when_present() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_test_config(&temp_dir);

        // Analyzed recording plus a polished master in mixed/.
        let recording = create_test_recording(&temp_dir, "test_recording", RecordingStatus::Analyzed);
        let mixed_dir = recording.path.join("mixed");
        fs::create_dir_all(&mixed_dir).unwrap();
        fs::write(mixed_dir.join("master.wav"), "wav").unwrap();

        // No explicit main_audio: should resolve to the master and not error out.
        let result = execute_step_with_preset(
            &recording,
            &NextStep::SetupRender,
            &config,
            "minimal",
            None,
        ).await;

        assert!(result.is_ok());
    }

    #[test]
    fn test_render_options_default_has_preset() {
        // cymatic (the GN visualizer) has no preset concept, so the value is
        // informational only — but the default must still be a stable, non-empty
        // string matching the UI's AVAILABLE_PRESETS for the "Setup" button.
        let supported = ["minimal", "multi_pip"];
        assert!(supported.contains(&RenderOptions::default().preset.as_str()));
    }

    #[tokio::test]
    async fn test_render_step_drives_cymatic() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_test_config(&temp_dir);

        // Analyzed recording: Render now drives cymatic-render (no manual-Blender stub).
        let recording = create_test_recording(&temp_dir, "test_recording", RecordingStatus::Analyzed);

        let result = execute_step(&recording, &NextStep::Render, &config).await;
        assert!(result.is_ok());
        let process_result = result.unwrap();
        // echo stub: stdout echoes the constructed command line.
        assert!(process_result.stdout.contains("cymatic-render"));
        assert!(!process_result.stdout.contains("cinemon"));
    }
}
