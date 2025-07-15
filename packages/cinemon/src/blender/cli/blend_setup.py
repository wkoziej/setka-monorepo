"""
CLI interface for Blender VSE project setup.

This module provides command-line interface for creating Blender VSE projects
from extracted OBS Canvas recordings.
"""

import argparse
import logging
import sys
from pathlib import Path

from ..project_manager import BlenderProjectManager
from setka_common.audio import AudioValidationError, analyze_audio_command
from setka_common.file_structure.specialized import RecordingStructureManager
from setka_common.utils.files import find_files_by_type, MediaType


def setup_logging(verbose: bool = False) -> None:
    """
    Setup logging configuration.

    Args:
        verbose: Enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Tworzy projekt Blender VSE z nagrania OBS Canvas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s ./recording_20250105_143022
  %(prog)s ./recording_20250105_143022 --verbose
  %(prog)s ./recording_20250105_143022 --main-audio "main_audio.m4a"
  %(prog)s ./recording_20250105_143022 --analyze-audio --animation-mode beat-switch
  %(prog)s ./recording_20250105_143022 --animation-mode energy-pulse --beat-division 4
  %(prog)s ./recording_20250105_143022 --force
        """,
    )

    parser.add_argument("recording_dir", type=Path, help="Katalog nagrania OBS Canvas")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Szczegółowe logowanie"
    )

    parser.add_argument(
        "--force", "-f", action="store_true", help="Nadpisz istniejący plik .blend"
    )

    parser.add_argument(
        "--main-audio",
        type=str,
        help="Nazwa głównego pliku audio (wymagane gdy jest więcej niż jeden plik audio)",
    )

    parser.add_argument(
        "--analyze-audio",
        action="store_true",
        help="Uruchom analizę audio przed stworzeniem projektu",
    )

    parser.add_argument(
        "--animation-mode",
        type=str,
        default="none",
        choices=[
            "none",
            "beat-switch",
            "energy-pulse",
            "section-transition",
            "multi-pip",
        ],
        help="Tryb animacji dla VSE (default: none)",
    )

    parser.add_argument(
        "--beat-division",
        type=int,
        default=8,
        choices=[1, 2, 4, 8, 16],
        help="Podział beatów dla animacji (default: 8)",
    )

    return parser.parse_args()


def validate_recording_directory(recording_dir: Path) -> None:
    """
    Validate recording directory structure.

    Args:
        recording_dir: Path to recording directory

    Raises:
        ValueError: If directory structure is invalid
    """
    if not recording_dir.exists():
        raise ValueError(f"Katalog nagrania nie istnieje: {recording_dir}")

    if not recording_dir.is_dir():
        raise ValueError(f"Ścieżka nie jest katalogiem: {recording_dir}")

    # Check for metadata.json
    metadata_path = recording_dir / "metadata.json"
    if not metadata_path.exists():
        raise ValueError(f"Brak pliku metadata.json w katalogu: {recording_dir}")

    # Check for extracted directory
    extracted_dir = recording_dir / "extracted"
    if not extracted_dir.exists():
        raise ValueError(f"Brak katalogu extracted/ w katalogu: {recording_dir}")

    if not extracted_dir.is_dir():
        raise ValueError(f"extracted/ nie jest katalogiem w: {recording_dir}")

    # Check if extracted directory has any files
    if not any(extracted_dir.iterdir()):
        raise ValueError(f"Katalog extracted/ jest pusty w: {recording_dir}")


def validate_animation_parameters(animation_mode: str, beat_division: int) -> None:
    """
    Validate animation parameters.

    Args:
        animation_mode: Animation mode string
        beat_division: Beat division value

    Raises:
        ValueError: If parameters are invalid
    """
    valid_modes = {
        "none",
        "beat-switch",
        "energy-pulse",
        "section-transition",
        "multi-pip",
    }
    valid_divisions = {1, 2, 4, 8, 16}

    if animation_mode not in valid_modes:
        raise ValueError(
            f"Invalid animation mode: {animation_mode}. "
            f"Valid modes: {', '.join(sorted(valid_modes))}"
        )

    if beat_division not in valid_divisions:
        raise ValueError(
            f"Invalid beat division: {beat_division}. "
            f"Valid divisions: {', '.join(map(str, sorted(valid_divisions)))}"
        )


def find_main_audio_file(recording_dir: Path) -> Path:
    """
    Find main audio file in recording directory.

    Args:
        recording_dir: Path to recording directory

    Returns:
        Path: Path to main audio file

    Raises:
        ValueError: If no audio file found
    """
    structure = RecordingStructureManager.find_recording_structure(recording_dir)
    if not structure:
        raise ValueError(f"Invalid recording structure in: {recording_dir}")

    audio_files = find_files_by_type(structure.extracted_dir, MediaType.AUDIO)
    if not audio_files:
        raise ValueError(f"No audio files found in: {structure.extracted_dir}")

    # Use the first audio file (sorted by name)
    return audio_files[0]


def _has_existing_audio_analysis(recording_dir: Path, main_audio: str = None) -> bool:
    """
    Check if audio analysis already exists for the recording.

    Args:
        recording_dir: Path to recording directory
        main_audio: Main audio filename (optional)

    Returns:
        bool: True if analysis exists
    """
    try:
        # Find main audio file if not specified
        if not main_audio:
            main_audio_file = find_main_audio_file(recording_dir)
        else:
            main_audio_file = recording_dir / "extracted" / main_audio

        # Check if analysis file exists using correct API
        analysis_file = RecordingStructureManager.find_audio_analysis(main_audio_file)
        return analysis_file is not None

    except Exception:
        # If any error occurs, assume no analysis exists
        return False


def perform_audio_analysis(recording_dir: Path, main_audio: Path) -> Path:
    """
    Perform audio analysis on main audio file.

    Args:
        recording_dir: Path to recording directory
        main_audio: Path to main audio file

    Returns:
        Path: Path to analysis file

    Raises:
        RuntimeError: If analysis fails
    """
    try:
        # Ensure analysis directory exists
        analysis_dir = RecordingStructureManager.ensure_analysis_dir(recording_dir)

        # Perform analysis
        analysis_file = analyze_audio_command(main_audio, analysis_dir)

        logging.getLogger(__name__).info(f"Audio analysis completed: {analysis_file}")
        return analysis_file

    except Exception as e:
        raise RuntimeError(f"Audio analysis failed: {e}")


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    try:
        # Validate recording directory
        logger.info(f"Validating recording directory: {args.recording_dir}")
        validate_recording_directory(args.recording_dir)

        # Validate animation parameters
        validate_animation_parameters(args.animation_mode, args.beat_division)

        # Determine if audio analysis is needed
        needs_audio_analysis = args.analyze_audio or (
            args.animation_mode != "none"
            and not _has_existing_audio_analysis(args.recording_dir, args.main_audio)
        )

        # Perform audio analysis if requested or automatically needed
        if needs_audio_analysis:
            if args.analyze_audio:
                logger.info("Audio analysis requested...")
            else:
                logger.info(
                    f"Audio analysis needed for animation mode: {args.animation_mode}"
                )

            # Find main audio file if not specified
            if not args.main_audio:
                main_audio_file = find_main_audio_file(args.recording_dir)
                logger.info(f"Auto-detected main audio file: {main_audio_file}")
            else:
                # Use specified main audio file
                main_audio_file = args.recording_dir / "extracted" / args.main_audio
                if not main_audio_file.exists():
                    raise ValueError(
                        f"Specified main audio file not found: {main_audio_file}"
                    )

            # Perform analysis
            analysis_file = perform_audio_analysis(args.recording_dir, main_audio_file)
            print(f"🎵 Analiza audio ukończona: {analysis_file}")

        # Create Blender project manager
        manager = BlenderProjectManager()

        # Create VSE project
        logger.info("Creating Blender VSE project...")
        project_path = manager.create_vse_project(
            args.recording_dir,
            args.main_audio,
            animation_mode=args.animation_mode,
            beat_division=args.beat_division,
        )

        print(f"✅ Projekt Blender VSE utworzony: {project_path}")
        return 0

    except AudioValidationError as e:
        logger.error(f"Audio validation error: {e}")
        print(f"❌ Błąd audio: {e}", file=sys.stderr)
        return 1

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(f"❌ Błąd walidacji: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Nieoczekiwany błąd: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
