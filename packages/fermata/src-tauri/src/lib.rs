mod models;
mod services;
mod commands;

use commands::recordings::{
    AppConfig, get_recordings, get_recording_details, get_recordings_by_status,
    get_recordings_needing_attention, update_recordings_path, get_app_config, delete_recording
};
use commands::operations::{run_next_step, run_specific_step, run_specific_step_with_options, list_animation_presets};
use commands::rename::rename_recording;
use commands::video::{get_playable_video_path, open_video_external};

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
      list_animation_presets,
      rename_recording,
      get_playable_video_path,
      open_video_external
    ])
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
