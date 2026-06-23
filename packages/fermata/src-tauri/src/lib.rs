mod models;
mod services;
mod commands;

use commands::recordings::{
    AppConfig, get_recordings, get_recording_details, get_recordings_by_status,
    get_recordings_needing_attention, update_recordings_path, get_app_config, delete_recording
};
use commands::operations::{run_next_step, run_specific_step, run_specific_step_with_options};
use commands::rename::rename_recording;
use commands::video::{get_playable_video_path, get_structure_heatmap, open_video_external, play_video_with_subtitles};
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .manage(AppConfig::default())
    .invoke_handler(tauri::generate_handler![
      get_recordings,
      get_recording_details,
      get_recordings_by_status,
      get_recordings_needing_attention,
      update_recordings_path,
      get_app_config,
      delete_recording,
      run_next_step,
      run_specific_step,
      run_specific_step_with_options,
      rename_recording,
      get_playable_video_path,
      open_video_external,
      play_video_with_subtitles,
      get_structure_heatmap
    ])
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      // Fail-fast CLI tool validation: probe uv + the workspace packages
      // (beatrix/cymatic/medusa) at startup so a missing toolchain surfaces in
      // the log immediately rather than on the first pipeline action. Runs in
      // the background so a slow probe doesn't delay the window appearing; a
      // failure is logged (non-fatal) since the GUI is still useful read-only.
      let config = app.state::<AppConfig>();
      let runner = services::ProcessRunner::new(
        config.cli_paths.workspace_root.clone(),
        config.cli_paths.uv_path.clone(),
      );
      tauri::async_runtime::spawn(async move {
        match runner.validate_cli_tools().await {
          Ok(()) => log::info!("✅ CLI tools validated (uv + beatrix/cymatic/medusa)"),
          Err(e) => log::warn!("⚠️ CLI tool validation failed: {}", e),
        }
      });

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
