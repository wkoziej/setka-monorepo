use tauri::State;
use crate::commands::recordings::AppConfig;
use std::process::Command;
use std::path::Path;

/// Get the path to the main video file to play for a recording
#[tauri::command]
pub fn get_playable_video_path(recording_name: String, config: State<AppConfig>) -> Result<String, String> {
    let recording_path = config.recordings_path.join(&recording_name);
    
    if !recording_path.exists() {
        return Err(format!("Recording '{}' not found", recording_name));
    }
    
    // Priority 1: Check for rendered final.mp4 or *_final.mp4
    let render_dir = recording_path.join("blender").join("render");
    if render_dir.exists() {
        if let Ok(entries) = std::fs::read_dir(&render_dir) {
            for entry in entries.flatten() {
                let file_path = entry.path();
                if file_path.is_file() {
                    if let Some(file_name) = file_path.file_name().and_then(|n| n.to_str()) {
                        if file_name == "final.mp4" || file_name.ends_with("_final.mp4") {
                            return Ok(file_path.to_string_lossy().to_string());
                        }
                    }
                }
            }
        }
    }
    
    // Priority 2: Look for main OBS recording file (.mkv, .mp4, .avi)
    let video_extensions = ["mkv", "mp4", "avi", "mov"];
    if let Ok(entries) = std::fs::read_dir(&recording_path) {
        let mut video_files = Vec::new();
        
        // Collect all video files
        for entry in entries.flatten() {
            let file_path = entry.path();
            if let Some(extension) = file_path.extension() {
                if let Some(ext_str) = extension.to_str() {
                    if video_extensions.contains(&ext_str) && file_path.is_file() {
                        video_files.push(file_path);
                    }
                }
            }
        }
        
        // First priority: files that match the recording name
        for file_path in &video_files {
            if let Some(file_stem) = file_path.file_stem() {
                if file_stem == recording_name.as_str() {
                    return Ok(file_path.to_string_lossy().to_string());
                }
            }
        }
        
        // Second priority: any video file found
        if let Some(first_video) = video_files.first() {
            return Ok(first_video.to_string_lossy().to_string());
        }
    }
    
    Err(format!("No playable video file found for recording '{}'", recording_name))
}

/// Open video file in external system player
#[tauri::command]
pub fn open_video_external(file_path: String) -> Result<(), String> {
    let path = Path::new(&file_path);
    if !path.exists() {
        return Err(format!("Video file not found: {}", file_path));
    }
    
    println!("🔗 [Rust] Opening video in external player: {}", file_path);
    
    #[cfg(target_os = "linux")]
    {
        match Command::new("xdg-open").arg(&file_path).spawn() {
            Ok(_) => {
                println!("✅ [Rust] Successfully opened video in external player");
                Ok(())
            }
            Err(e) => {
                let error_msg = format!("Failed to open video: {}", e);
                println!("🚨 [Rust] {}", &error_msg);
                Err(error_msg)
            }
        }
    }
    
    #[cfg(target_os = "windows")]
    {
        match Command::new("cmd").args(&["/C", "start", "", &file_path]).spawn() {
            Ok(_) => {
                println!("✅ [Rust] Successfully opened video in external player");
                Ok(())
            }
            Err(e) => {
                let error_msg = format!("Failed to open video: {}", e);
                println!("🚨 [Rust] {}", &error_msg);
                Err(error_msg)
            }
        }
    }
    
    #[cfg(target_os = "macos")]
    {
        match Command::new("open").arg(&file_path).spawn() {
            Ok(_) => {
                println!("✅ [Rust] Successfully opened video in external player");
                Ok(())
            }
            Err(e) => {
                let error_msg = format!("Failed to open video: {}", e);
                println!("🚨 [Rust] {}", &error_msg);
                Err(error_msg)
            }
        }
    }
    
    #[cfg(not(any(target_os = "linux", target_os = "windows", target_os = "macos")))]
    {
        Err("External player not supported on this platform".to_string())
    }
} 