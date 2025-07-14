"""
OBS Studio script for Canvas Recording metadata collection.
This script integrates with OBS Studio to automatically collect scene metadata
when recording stops.
"""

import os
import json
import time
import shutil
from pathlib import Path
from typing import Dict, Any

try:
    import obspython as obs
except ImportError:
    # For testing purposes when OBS is not available
    obs = None

# Import capabilities detection from metadata module
try:
    from src.core.metadata import determine_source_capabilities
except ImportError:
    # Fallback for when running in OBS without proper Python path
    def determine_source_capabilities(obs_source) -> Dict[str, bool]:
        """Fallback implementation for OBS environment."""
        if obs_source is None or obs is None:
            return {"has_audio": False, "has_video": False}

        flags = obs.obs_source_get_output_flags(obs_source)

        # OBS source flags constants
        OBS_SOURCE_VIDEO = 0x001
        OBS_SOURCE_AUDIO = 0x002

        return {
            "has_audio": bool(flags & OBS_SOURCE_AUDIO),
            "has_video": bool(flags & OBS_SOURCE_VIDEO),
        }


# Import file structure manager
# Direct import for OBS environment
import sys

# Add the core directory to sys.path
core_dir = Path(__file__).parent.parent / "core"
if str(core_dir) not in sys.path:
    sys.path.insert(0, str(core_dir))

from setka_common.file_structure.specialized import RecordingStructureManager


# Global variables for script state
script_enabled = False
current_scene_data = {}
recording_output_path = None


def script_description():
    """Return script description for OBS Studio."""
    return """
    <h2>Canvas Recording Metadata Collector</h2>
    <p>Automatically collects scene metadata when recording stops.</p>
    <p>This data is used for automatic source extraction from recordings.</p>
    """


def script_properties():
    """Define script properties for OBS Studio UI."""
    if obs is None:
        return None

    props = obs.obs_properties_create()

    # Enable/disable script
    obs.obs_properties_add_bool(props, "enabled", "Enable metadata collection")

    # Add info text
    obs.obs_properties_add_text(props, "info", "Info", obs.OBS_TEXT_INFO)

    return props


def script_defaults(settings):
    """Set default values for script properties."""
    if obs is None:
        return

    obs.obs_data_set_default_bool(settings, "enabled", True)
    obs.obs_data_set_default_string(
        settings,
        "info",
        "Metadata will be saved when recording stops. Files are automatically reorganized.",
    )


def script_update(settings):
    """Called when script properties are updated."""
    global script_enabled

    if obs is None:
        return

    script_enabled = obs.obs_data_get_bool(settings, "enabled")

    print(f"[Canvas Recorder] Script enabled: {script_enabled}")


def script_load(settings):
    """Called when script is loaded."""
    global script_enabled

    if obs is None:
        print("[Canvas Recorder] OBS Python API not available")
        return

    print("[Canvas Recorder] Script loaded")

    # Register frontend event callback
    obs.obs_frontend_add_event_callback(on_event)

    # Initialize settings
    script_update(settings)


def script_unload():
    """Called when script is unloaded."""
    if obs is None:
        return

    print("[Canvas Recorder] Script unloaded")

    # Remove frontend event callback
    obs.obs_frontend_remove_event_callback(on_event)


def on_event(event):
    """Handle OBS frontend events."""
    if obs is None or not script_enabled:
        return

    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STARTED:
        print("[Canvas Recorder] Recording started - preparing metadata collection")
        prepare_metadata_collection()

    elif event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        print("[Canvas Recorder] Recording stopped - collecting metadata")
        collect_and_save_metadata()


def prepare_metadata_collection():
    """Prepare for metadata collection when recording starts."""
    global current_scene_data, recording_output_path

    if obs is None:
        return

    # Get recording path while recording is active
    recording_output_path = get_recording_output_path()
    if recording_output_path:
        print(f"[Canvas Recorder] Recording path captured: {recording_output_path}")
    else:
        print("[Canvas Recorder] Could not get recording path during recording")

    # Get current scene
    current_scene = obs.obs_frontend_get_current_scene()
    if current_scene is None:
        print("[Canvas Recorder] No current scene found")
        return

    # Get video info
    video_info = obs.obs_video_info()
    obs.obs_get_video_info(video_info)

    # Store basic info
    current_scene_data = {
        "canvas_size": [video_info.base_width, video_info.base_height],
        "fps": video_info.fps_num / video_info.fps_den
        if video_info.fps_den > 0
        else 30.0,
        "recording_start_time": time.time(),
        "scene_name": obs.obs_source_get_name(current_scene),
    }

    print(
        f"[Canvas Recorder] Prepared metadata for scene: {current_scene_data['scene_name']}"
    )
    print(f"[Canvas Recorder] Canvas size: {current_scene_data['canvas_size']}")
    print(f"[Canvas Recorder] FPS: {current_scene_data['fps']}")

    # Release source reference
    obs.obs_source_release(current_scene)


def collect_and_save_metadata():
    """Collect scene metadata and save to file."""
    global current_scene_data, recording_output_path

    if obs is None:
        return

    if not current_scene_data:
        print("[Canvas Recorder] No scene data prepared")
        return

    # Use recording path captured during recording
    output_directory = recording_output_path
    if output_directory:
        print(f"[Canvas Recorder] Using captured output directory: {output_directory}")
        # Znajdź najnowszy plik nagrania w katalogu
        recording_path = find_latest_recording_file(output_directory)
        if recording_path:
            print(f"[Canvas Recorder] Found latest recording: {recording_path}")
        else:
            print(
                "[Canvas Recorder] No recent recording file found in output directory"
            )
            recording_path = None
    else:
        print("[Canvas Recorder] No output directory captured, using fallback")
        recording_path = None

    # Get current scene
    current_scene = obs.obs_frontend_get_current_scene()
    if current_scene is None:
        print("[Canvas Recorder] No current scene found")
        return

    try:
        # Convert source to scene
        scene = obs.obs_scene_from_source(current_scene)
        if scene is None:
            print("[Canvas Recorder] Failed to get scene from source")
            return

        # Collect scene items - in Python API, this returns a list
        scene_items = obs.obs_scene_enum_items(scene)
        if scene_items is None:
            print("[Canvas Recorder] No scene items found")
            return

        sources = {}

        # Process each scene item
        for scene_item in scene_items:
            if scene_item is None:
                continue

            # Get source from scene item
            source = obs.obs_sceneitem_get_source(scene_item)
            if source is None:
                continue

            # Get source info
            source_name = obs.obs_source_get_name(source)
            source_id = obs.obs_source_get_id(source)

            # Get position, scale and bounds
            pos = obs.vec2()
            scale = obs.vec2()
            bounds = obs.vec2()
            obs.obs_sceneitem_get_pos(scene_item, pos)
            obs.obs_sceneitem_get_scale(scene_item, scale)
            obs.obs_sceneitem_get_bounds(scene_item, bounds)
            bounds_type = obs.obs_sceneitem_get_bounds_type(scene_item)

            # Get source dimensions
            source_width = obs.obs_source_get_width(source)
            source_height = obs.obs_source_get_height(source)

            # Calculate final dimensions - priorytet dla bounds
            if (
                bounds.x > 0 and bounds.y > 0 and bounds_type != 0
            ):  # 0 = OBS_BOUNDS_NONE
                final_width = int(bounds.x)
                final_height = int(bounds.y)
            else:
                final_width = int(source_width * scale.x)
                final_height = int(source_height * scale.y)

            # Determine source capabilities (has_audio/has_video)
            capabilities = determine_source_capabilities(source)

            # Store source data
            sources[source_name] = {
                "name": source_name,
                "id": source_id,
                "position": {"x": int(pos.x), "y": int(pos.y)},
                "scale": {"x": scale.x, "y": scale.y},
                "bounds": {"x": bounds.x, "y": bounds.y, "type": bounds_type},
                "dimensions": {
                    "source_width": source_width,
                    "source_height": source_height,
                    "final_width": final_width,
                    "final_height": final_height,
                },
                "visible": obs.obs_sceneitem_visible(scene_item),
                # Add capabilities for new extractor
                "has_audio": capabilities["has_audio"],
                "has_video": capabilities["has_video"],
            }

        # Release scene items list
        obs.sceneitem_list_release(scene_items)

        # Complete metadata
        metadata = {
            **current_scene_data,
            "sources": sources,
            "recording_stop_time": time.time(),
            "total_sources": len(sources),
        }

        # Save metadata to file and reorganize
        if recording_path and os.path.exists(recording_path):
            # Save metadata to temporary file first
            temp_metadata_path = os.path.join(
                os.path.dirname(recording_path), "temp_metadata.json"
            )
            try:
                with open(temp_metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

                # Reorganize files
                reorganized_dir = reorganize_files_after_recording(
                    recording_path, temp_metadata_path
                )
                if reorganized_dir:
                    print(f"[Canvas Recorder] Files reorganized to: {reorganized_dir}")
                else:
                    print(
                        "[Canvas Recorder] File reorganization failed, using fallback"
                    )
                    # Remove temp file and use normal save
                    if os.path.exists(temp_metadata_path):
                        os.remove(temp_metadata_path)
                    save_metadata_to_file(metadata)
            except Exception as e:
                print(f"[Canvas Recorder] Error during reorganization: {e}")
                # Clean up temp file if it exists
                if os.path.exists(temp_metadata_path):
                    os.remove(temp_metadata_path)
                # Fall back to normal save
                save_metadata_to_file(metadata)
        else:
            # Use normal metadata saving
            save_metadata_to_file(metadata)

        print(f"[Canvas Recorder] Collected metadata for {len(sources)} sources")

    except Exception as e:
        print(f"[Canvas Recorder] Error collecting metadata: {e}")

    finally:
        # Release source reference
        obs.obs_source_release(current_scene)


def save_metadata_to_file(metadata: Dict[str, Any]):
    """Save metadata to JSON file as fallback when reorganization fails."""
    global recording_output_path

    # Use recording output path if available, otherwise use default
    if recording_output_path:
        output_dir = recording_output_path
    else:
        output_dir = os.path.expanduser("~/obs-canvas-metadata")

    # Ensure directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Always use timestamp for fallback saves (when reorganization fails)
    timestamp = time.strftime("%Y-%m-%d %H-%M-%S")
    filename = f"{timestamp}_metadata.json"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"[Canvas Recorder] Metadata saved to: {filepath}")

    except Exception as e:
        print(f"[Canvas Recorder] Error saving metadata: {e}")


def get_recording_output_path():
    """Pobiera ścieżkę aktualnego nagrania z OBS API"""
    if obs is None:
        return None

    try:
        recording_path = obs.obs_frontend_get_current_record_output_path()
        if recording_path:
            # obs_frontend_get_current_record_output_path() zwraca string, nie pointer
            # Nie trzeba używać bfree() - to zwraca kopię stringa
            return str(recording_path) if recording_path else None
        return None
    except Exception as e:
        print(f"[Canvas Recorder] Error getting recording path: {e}")
        return None


def find_latest_recording_file(output_dir):
    """Znajduje najnowszy plik nagrania w katalogu wyjściowym"""
    if not output_dir or not os.path.exists(output_dir):
        return None

    try:
        # Szukaj plików wideo w katalogu
        video_extensions = [".mp4", ".mkv", ".flv", ".mov", ".avi"]
        video_files = []

        for file in os.listdir(output_dir):
            if any(file.lower().endswith(ext) for ext in video_extensions):
                file_path = os.path.join(output_dir, file)
                if os.path.isfile(file_path):
                    # Sprawdź czy plik jest świeży (utworzony w ciągu ostatnich 30 sekund)
                    file_age = time.time() - os.path.getmtime(file_path)
                    if file_age < 30:  # 30 sekund
                        video_files.append((file_path, os.path.getmtime(file_path)))

        if not video_files:
            return None

        # Zwróć najnowszy plik
        latest_file = max(video_files, key=lambda x: x[1])
        return latest_file[0]

    except Exception as e:
        print(f"[Canvas Recorder] Error finding latest recording: {e}")
        return None


def reorganize_files_after_recording(recording_path, metadata_path):
    """Reorganizuje pliki po nagraniu - tworzy strukturę katalogów używając FileStructureManager"""
    try:
        # Sprawdź czy pliki istnieją
        if not os.path.exists(recording_path):
            print(f"[Canvas Recorder] Recording file not found: {recording_path}")
            return None

        if not os.path.exists(metadata_path):
            print(f"[Canvas Recorder] Metadata file not found: {metadata_path}")
            return None

        # Pobierz nazwę pliku bez rozszerzenia
        recording_file = Path(recording_path)
        directory_name = recording_file.stem

        # Utwórz katalog docelowy w tym samym miejscu co nagranie
        target_dir = recording_file.parent / directory_name
        target_dir.mkdir(exist_ok=True)

        # Przenieś plik nagrania do katalogu docelowego
        target_recording_path = target_dir / recording_file.name
        if not target_recording_path.exists():
            shutil.move(recording_path, target_recording_path)

            # Użyj FileStructureManager do utworzenia struktury
        structure = RecordingStructureManager.create_structure(target_recording_path)

        # Przenieś plik metadanych do właściwego miejsca
        if not structure.metadata_file.exists():
            shutil.move(metadata_path, structure.metadata_file)

        print(f"[Canvas Recorder] Files reorganized to: {structure.project_dir}")
        return str(structure.project_dir)

    except Exception as e:
        print(f"[Canvas Recorder] Error reorganizing files: {e}")
        return None


# For testing purposes when running outside OBS
if __name__ == "__main__":
    print("Canvas Recording Metadata Collector")
    print("This script should be loaded in OBS Studio")
    print("Testing mode - OBS API not available")
