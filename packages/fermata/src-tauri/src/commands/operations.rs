use crate::models::{Recording, RecordingStatus, NextStep};
use crate::services::{FileScanner, ProcessRunner, ProcessResult};
use crate::commands::recordings::AppConfig;
use tauri::State;

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
            // Look for audio file in extracted directory
            let extracted_dir = recording.path.join("extracted");
            if !extracted_dir.exists() {
                return Err("Extracted directory not found - run extract step first".to_string());
            }

            log::info!("🔍 Searching for audio files in: {}", extracted_dir.display());

            // Find audio file (typically .m4a)
            let audio_files: Vec<_> = std::fs::read_dir(&extracted_dir)
                .map_err(|e| format!("Failed to read extracted directory: {}", e))?
                .filter_map(|entry| {
                    let entry = entry.ok()?;
                    let path = entry.path();
                    log::info!("📁 Found file: {:?}", path);
                    if path.extension()?.to_str()? == "m4a" {
                        path.file_name()?.to_str().map(|s| s.to_string())
                    } else {
                        None
                    }
                })
                .collect();

            log::info!("🎵 Found {} audio files: {:?}", audio_files.len(), audio_files);

            if audio_files.is_empty() {
                // List all files in directory for debugging
                if let Ok(entries) = std::fs::read_dir(&extracted_dir) {
                    let all_files: Vec<_> = entries
                        .filter_map(|e| e.ok())
                        .map(|e| e.file_name().to_string_lossy().to_string())
                        .collect();
                    log::warn!("❌ No .m4a files found. All files in directory: {:?}", all_files);
                    return Err(format!("No audio file (.m4a) found in extracted directory. Found files: {:?}", all_files));
                } else {
                    return Err("No audio file (.m4a) found in extracted directory".to_string());
                }
            }

            let audio_file = &audio_files[0]; // Take first audio file
            log::info!("🎯 Using audio file: {}", audio_file);
            runner.run_beatrix_analyze(&recording.path, audio_file).await
        }
        NextStep::SetupRender => {
            // Check if analysis exists
            if !recording.path.join("analysis").exists() {
                return Err("Analysis directory not found - run analyze step first".to_string());
            }

            // Check if we have multiple audio files and use configured main audio
            let extracted_dir = recording.path.join("extracted");
            if extracted_dir.exists() {
                let audio_files: Vec<_> = std::fs::read_dir(&extracted_dir)
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

                log::info!("🎵 Found {} audio files for setup render: {:?}", audio_files.len(), audio_files);

                if audio_files.len() > 1 {
                    // Use configured main audio file if available
                    if !config.main_audio_file.is_empty() && audio_files.contains(&config.main_audio_file) {
                        log::info!("🎯 Using configured main audio: {}", config.main_audio_file);
                        runner.run_cinemon_render_with_audio(&recording.path, "beat-switch", Some(&config.main_audio_file)).await
                    } else {
                        log::warn!("⚠️ Multiple audio files found but main audio '{}' not available in: {:?}", config.main_audio_file, audio_files);
                        return Err(format!("Multiple audio files found: {:?}. Configure FERMATA_MAIN_AUDIO environment variable to specify which one to use.", audio_files));
                    }
                } else {
                    // Single audio file, use without --main-audio parameter
                    runner.run_cinemon_render(&recording.path, "beat-switch").await
                }
            } else {
                // No extracted directory, use basic render
                runner.run_cinemon_render(&recording.path, "beat-switch").await
            }
        }
        NextStep::Render => {
            // Check if blender project exists
            let blender_dir = recording.path.join("blender");
            if !blender_dir.exists() {
                return Err("Blender project not found - run setup render step first".to_string());
            }

            // Find .blend file
            let blend_files: Vec<_> = std::fs::read_dir(&blender_dir)
                .map_err(|e| format!("Failed to read blender directory: {}", e))?
                .filter_map(|entry| {
                    let entry = entry.ok()?;
                    let path = entry.path();
                    if path.extension()?.to_str()? == "blend" {
                        Some(path)
                    } else {
                        None
                    }
                })
                .collect();

            if blend_files.is_empty() {
                return Err("No .blend file found in blender directory".to_string());
            }

            // For now, return error asking user to render manually
            // TODO: Implement automatic Blender rendering
            return Err("Manual Blender rendering required. Open the .blend file and render manually, or implement automatic rendering.".to_string());
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
    async fn test_missing_dependencies() {
        let temp_dir = TempDir::new().unwrap();
        let config = create_test_config(&temp_dir);
        
        // Try to analyze without extracted directory
        let recording = create_test_recording(&temp_dir, "test_recording", RecordingStatus::Recorded);
        
        let result = execute_step(&recording, &NextStep::Analyze, &config).await;
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("Extracted directory not found"));
    }
} 