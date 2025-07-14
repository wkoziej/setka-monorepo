#!/usr/bin/env python3
"""
Advanced Scene Switcher integration script for OBSession auto-extraction.
Automatically finds the latest recording and triggers extraction.
"""

import sys
import os
import datetime
import subprocess
import time
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from setka_common.file_structure.specialized import RecordingStructureManager
except ImportError:
    # Fallback if import fails
    class FileStructureManager:
        @staticmethod
        def find_recording_structure(base_path):
            """Fallback implementation."""
            metadata_file = base_path / "metadata.json"
            if metadata_file.exists():
                # Find video file in the same directory
                video_extensions = [
                    ".mkv",
                    ".mp4",
                    ".avi",
                    ".mov",
                    ".flv",
                    ".wmv",
                    ".webm",
                ]
                for file_path in base_path.iterdir():
                    if (
                        file_path.is_file()
                        and file_path.suffix.lower() in video_extensions
                    ):
                        return type(
                            "Structure",
                            (),
                            {
                                "video_file": file_path,
                                "metadata_file": metadata_file,
                                "recording_dir": base_path,
                            },
                        )()
            return None


def log_message(message):
    """Log message with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def find_latest_recording():
    """
    Find the most recent OBS recording file using FileStructureManager.
    Looks for recording files inside recording_name/ directories with metadata.json.
    """
    # Common OBS recording directories
    possible_dirs = [
        Path.home() / "Wideo" / "obs",  # Polish Videos/obs subdirectory
        Path.home() / "Videos" / "obs",  # Videos/obs subdirectory
    ]

    all_structures = []

    for directory in possible_dirs:
        if directory.exists():
            log_message(f"Checking directory: {directory}")

            # Look for recording structures using FileStructureManager
            for item in directory.iterdir():
                if item.is_dir():
                    log_message(f"  Checking subdirectory: {item}")

                    # Use FileStructureManager to find valid recording structure
                    try:
                        structure = RecordingStructureManager.find_recording_structure(item)
                        if structure:
                            log_message(
                                f"    Found valid recording structure: {structure.media_file}"
                            )
                            all_structures.append(structure)
                        else:
                            log_message("    No valid recording structure found")
                    except Exception as e:
                        log_message(f"    Error checking structure: {e}")

        else:
            log_message(f"Directory does not exist: {directory}")

    log_message(f"Total recording structures found: {len(all_structures)}")

    if not all_structures:
        log_message("No recording structures found")
        return None

    # Find the newest recording file
    latest_structure = max(all_structures, key=lambda s: os.path.getmtime(s.media_file))

    # Check if file was created in the last 30 seconds (fresh recording)
    file_age = time.time() - os.path.getmtime(latest_structure.media_file)

    log_message(f"Latest recording: {latest_structure.media_file}")
    log_message(f"File age: {file_age:.1f} seconds")

    if file_age > 30:
        log_message("File too old, probably not the recording we want")
        return None

    return str(latest_structure.media_file)


def run_extraction(recording_file):
    """
    Run OBSession extraction on the recording file.
    """
    log_message(f"Starting extraction for: {recording_file}")

    # Path to OBSession CLI
    cli_path = Path("/home/wojtas/dev/obsession/src/cli/extract.py")

    if not cli_path.exists():
        log_message(f"ERROR: CLI not found at {cli_path}")
        return False

    # Build command with uv run
    cmd = [
        "uv",
        "run",
        "python",
        str(cli_path),
        recording_file,
        "--auto",
        "--verbose",
        "--delay",
        "0",
    ]

    log_message(f"Running command: {' '.join(cmd)}")

    try:
        # Run extraction
        result = subprocess.run(
            cmd,
            cwd="/home/wojtas/dev/obsession",
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minutes max
        )

        # Log output
        if result.stdout:
            log_message(f"STDOUT: {result.stdout}")

        if result.stderr:
            log_message(f"STDERR: {result.stderr}")

        if result.returncode == 0:
            log_message("✅ Extraction completed successfully")
            return True
        else:
            log_message(f"❌ Extraction failed with code: {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        log_message("❌ Extraction timeout (30 minutes)")
        return False
    except Exception as e:
        log_message(f"❌ Extraction error: {e}")
        return False


def main():
    """Main function"""
    log_message("=== OBSession Auto-Extraction Started ===")
    log_message(f"Arguments: {sys.argv}")
    log_message(f"Working directory: {os.getcwd()}")

    # Find latest recording
    recording_file = find_latest_recording()

    if not recording_file:
        log_message("❌ No recent recording file found")
        return 1

    # Run extraction
    success = run_extraction(recording_file)

    if success:
        log_message("🎉 Auto-extraction completed successfully!")
        return 0
    else:
        log_message("💥 Auto-extraction failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
