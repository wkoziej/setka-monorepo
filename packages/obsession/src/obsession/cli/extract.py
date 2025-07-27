"""
CLI interface for extracting sources from OBS canvas recordings.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

from obsession.core.extractor import extract_sources
from setka_common.file_structure.specialized import RecordingStructureManager


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments.

    Args:
        args: Optional list of arguments (for testing)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Extract individual sources from OBS canvas recording",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s recording.mp4 recording.mp4.json
  %(prog)s recording.mp4 metadata.json --output-dir extracted/
  %(prog)s recording.mp4 metadata.json --verbose
  %(prog)s recording.mp4 --auto --verbose
  %(prog)s recording.mp4 --auto --delay 5
  %(prog)s recording.mp4 metadata.json --skip-audio-pattern "RPI.*"
  %(prog)s recording.mp4 --auto --skip-audio-pattern "^(RPI|Camera).*"
        """,
    )

    parser.add_argument("video_file", help="Path to the input video file")

    parser.add_argument(
        "metadata_file",
        nargs="?",
        help="Path to the metadata JSON file (optional with --auto)",
    )

    parser.add_argument(
        "--output-dir",
        help="Custom output directory (default: <video_name>_extracted/)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto mode: wait for file to be ready and auto-detect metadata",
    )

    parser.add_argument(
        "--delay",
        type=int,
        default=3,
        help="Delay in seconds before processing (default: 3)",
    )

    parser.add_argument(
        "--skip-audio-pattern",
        type=str,
        default="RPI.*",
        help="Skip audio extraction for sources matching regex pattern (default: 'RPI.*')",
    )

    return parser.parse_args(args)


def wait_for_file_ready(file_path: Path, max_wait: int = 30) -> bool:
    """
    Wait for file to be ready for processing.

    Args:
        file_path: Path to the video file
        max_wait: Maximum wait time in seconds

    Returns:
        True if file is ready, False if timeout
    """
    print(f"Waiting for file to be ready: {file_path}")

    for attempt in range(max_wait):
        try:
            # Check if file exists
            if not file_path.exists():
                time.sleep(1)
                continue

            # Check if file size is stable (not growing)
            size1 = file_path.stat().st_size
            time.sleep(1)
            size2 = file_path.stat().st_size

            if size1 == size2 and size1 > 1024:  # File stable and > 1KB
                # Try to open file exclusively to check if it's locked
                try:
                    with open(file_path, "r+b") as f:
                        f.seek(0, 2)  # Go to end
                        if f.tell() > 1024:  # File has content
                            print(f"File ready after {attempt + 1} seconds")
                            return True
                except (IOError, OSError, PermissionError):
                    pass  # File still locked

        except Exception as e:
            print(f"Error checking file: {e}")

        time.sleep(1)

    print(f"Timeout waiting for file to be ready after {max_wait} seconds")
    return False


def find_metadata_file(video_path: Path) -> Optional[Path]:
    """
    Try to find corresponding metadata file for the video using FileStructureManager.

    Args:
        video_path: Path to the video file

    Returns:
        Path to metadata file if found, None otherwise
    """
    print(f"Searching for metadata file for: {video_path}")

    # First, try to find metadata file using FileStructureManager
    # This handles the new structure where metadata.json is in the same directory as video
    try:
        structure = RecordingStructureManager.find_recording_structure(
            video_path.parent
        )
        if structure and structure.metadata_file.exists():
            print(
                f"Found metadata file using FileStructureManager: {structure.metadata_file}"
            )
            return structure.metadata_file
    except Exception as e:
        print(f"Error using FileStructureManager: {e}")

    # Fallback to legacy patterns for backward compatibility
    video_stem = video_path.stem
    video_dir = video_path.parent

    print("Falling back to legacy pattern matching...")
    print(f"Video stem: {video_stem}")
    print(f"Video directory: {video_dir}")

    # Common metadata file patterns (legacy)
    patterns = [
        f"{video_stem}.json",
        f"{video_stem}_metadata.json",
        f"{video_stem}.mp4.json",
        f"{video_stem}.mkv.json",
        f"{video_stem}.flv.json",
        f"{video_stem}.mov.json",
        f"{video_stem}.avi.json",
        f"{video_stem}_meta.json",
        f"metadata_{video_stem}.json",
        f"meta_{video_stem}.json",
    ]

    print(f"Checking patterns: {patterns}")

    for pattern in patterns:
        metadata_path = video_dir / pattern
        print(f"  Checking: {metadata_path}")
        if metadata_path.exists():
            print(f"Found metadata file: {metadata_path}")
            return metadata_path

    print("No exact pattern match found, checking all JSON files...")

    # Look for any .json file with similar timestamp
    json_files = list(video_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files in directory")

    for json_file in json_files:
        print(f"  Checking JSON file: {json_file}")
        try:
            # Simple heuristic: if JSON file was created around the same time
            video_mtime = video_path.stat().st_mtime
            json_mtime = json_file.stat().st_mtime
            time_diff = abs(video_mtime - json_mtime)

            print(f"    Time difference: {time_diff:.1f} seconds")

            if time_diff < 60:  # Within 1 minute
                print(f"Found potential metadata file: {json_file}")
                return json_file
        except Exception as e:
            print(f"    Error checking file {json_file}: {e}")

    print("No metadata file found")
    return None


def apply_audio_pattern_filter(metadata: dict, pattern: str) -> dict:
    """
    Apply audio filtering based on source name pattern.

    Args:
        metadata: The loaded metadata dictionary
        pattern: Regex pattern to match source names

    Returns:
        Modified metadata dictionary with has_audio=False for matching sources
    """
    import re

    if not pattern:
        return metadata

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        print(f"Error: Invalid regex pattern '{pattern}': {e}", file=sys.stderr)
        return metadata

    modified_count = 0

    # Create a copy to avoid modifying original
    new_metadata = metadata.copy()
    new_sources = {}

    for source_name, source_info in metadata.get("sources", {}).items():
        source_copy = source_info.copy()

        if regex.match(source_name):
            if source_copy.get("has_audio", False):
                print(
                    f"Skipping audio extraction for source matching pattern: {source_name}"
                )
                source_copy["has_audio"] = False
                modified_count += 1

        new_sources[source_name] = source_copy

    new_metadata["sources"] = new_sources

    if modified_count > 0:
        print(f"Applied audio filtering to {modified_count} source(s)")

    return new_metadata


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        args = parse_args()

        # Handle auto mode
        if args.auto:
            # Create log file for auto mode
            log_path = Path(args.video_file).parent / "extraction.log"

            def log_message(msg: str):
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                log_line = f"[{timestamp}] {msg}\n"
                print(msg)  # Also print to console
                try:
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(log_line)
                except Exception:
                    pass  # Ignore log write errors

            log_message(f"Auto mode: processing {args.video_file}")
            log_message(f"Delay: {args.delay} seconds")

            # Wait for delay period
            time.sleep(args.delay)

        # Validate input files exist
        video_path = Path(args.video_file)

        if args.auto:
            # Wait for file to be ready
            if not wait_for_file_ready(video_path):
                print(f"Error: Video file not ready: {video_path}", file=sys.stderr)
                return 1

            # Auto-detect metadata file
            if args.metadata_file:
                metadata_path = Path(args.metadata_file)
            else:
                metadata_path = find_metadata_file(video_path)
                if not metadata_path:
                    print(
                        f"Error: Could not find metadata file for: {video_path}",
                        file=sys.stderr,
                    )
                    return 1
        else:
            # Normal mode - require both arguments
            if not args.metadata_file:
                print(
                    "Error: metadata_file is required in normal mode", file=sys.stderr
                )
                return 1
            metadata_path = Path(args.metadata_file)

        if not video_path.exists():
            print(f"Error: Video file not found: {video_path}", file=sys.stderr)
            return 1

        if not metadata_path.exists():
            print(f"Error: Metadata file not found: {metadata_path}", file=sys.stderr)
            return 1

        # Load metadata
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in metadata file: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error: Failed to read metadata file: {e}", file=sys.stderr)
            return 1

        # Apply audio pattern filter if specified
        if args.skip_audio_pattern:
            metadata = apply_audio_pattern_filter(metadata, args.skip_audio_pattern)

        # Print verbose info if requested
        if args.verbose:
            print(f"Input video: {video_path}")
            print(f"Metadata file: {metadata_path}")
            print(f"Canvas size: {metadata.get('canvas_size', 'Unknown')}")
            print(f"Number of sources: {len(metadata.get('sources', {}))}")
            print()

        # Extract sources
        if args.verbose:
            print("Starting extraction...")

        result = extract_sources(str(video_path), metadata, args.output_dir)

        if result.success:
            print(f"Successfully extracted {len(result.extracted_files)} sources:")
            for file_path in result.extracted_files:
                print(f"  - {file_path}")

            if args.verbose:
                print("\nExtraction completed successfully!")

            return 0
        else:
            print(f"Extraction failed: {result.error_message}", file=sys.stderr)
            return 1

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
