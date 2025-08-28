"""
CLI interface for Blender VSE project setup.

This module provides command-line interface for creating Blender VSE projects
from extracted OBS Canvas recordings.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from beatrix import AudioValidationError
from setka_common.config import BlenderYAMLConfig, YAMLConfigLoader

from ..config import CinemonConfigGenerator
from ..config.preset_manager import PresetManager
from ..project_manager import BlenderProjectManager


def load_yaml_config(config_path: Path) -> BlenderYAMLConfig:
    """
    Load and validate YAML configuration.

    This function provides backward compatibility for tests.
    It's a wrapper around YAMLConfigLoader.load_from_file().

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Parsed and validated configuration

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If YAML is invalid or validation fails
    """
    loader = YAMLConfigLoader()
    try:
        return loader.load_from_file(config_path)
    except FileNotFoundError:
        # Let FileNotFoundError pass through for test compatibility
        raise
    except Exception as e:
        raise ValueError(f"Failed to load YAML configuration: {e}") from e


def open_blender_with_video_editing(blend_file_path: Path) -> None:
    """
    Open Blender GUI with the blend file (should already be in Video Editing workspace).

    Args:
        blend_file_path: Path to .blend file to open
    """
    try:
        # Simple Blender open - project was created with Video Editing template
        cmd = ["snap", "run", "blender", str(blend_file_path)]

        print("🎬 Otwieranie Blender (projekt utworzony z Video Editing template)...")
        print(f"📁 Plik: {blend_file_path}")

        # Start Blender in background (non-blocking) with output visible
        subprocess.Popen(cmd)

    except Exception as e:
        print(f"⚠ Nie udało się otworzyć Blender: {e}")
        print(f"💡 Otwórz ręcznie: snap run blender '{blend_file_path}'")


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


def get_available_presets() -> list[str]:
    """
    Get list of available presets dynamically.

    Returns:
        List of available preset names
    """
    try:
        manager = PresetManager()
        return manager.list_presets()
    except Exception:
        # Fallback to known presets if PresetManager fails
        return ["minimal", "multi_pip"]


def validate_preset(preset_name: str) -> None:
    """
    Validate that preset exists.

    Args:
        preset_name: Name of preset to validate

    Raises:
        SystemExit: If preset doesn't exist
    """
    try:
        manager = PresetManager()
        available = manager.list_presets()

        if preset_name not in available:
            print(f"❌ Preset '{preset_name}' nie istnieje")
            print(f"📋 Dostępne presety: {', '.join(available)}")
            print("💡 Użyj --list-presets aby zobaczyć wszystkie dostępne presety")
            sys.exit(1)

    except Exception as e:
        print(f"⚠ Nie można sprawdzić presetów: {e}")
        # Continue with execution - let PresetManager handle the error later


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
  %(prog)s ./recording_20250105_143022 --preset minimal
  %(prog)s ./recording_20250105_143022 --preset multi_pip --verbose
  %(prog)s ./recording_20250105_143022 --preset minimal --main-audio "main_audio.m4a"
  %(prog)s ./recording_20250105_143022 --config custom_config.yaml
  %(prog)s ./recording_20250105_143022 --config path/to/config.yaml --force
  %(prog)s --list-presets
        """,
    )

    parser.add_argument(
        "recording_dir",
        nargs="?",  # Make optional
        type=Path,
        help="Katalog nagrania OBS Canvas",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Szczegółowe logowanie"
    )

    parser.add_argument(
        "--force", "-f", action="store_true", help="Nadpisz istniejący plik .blend"
    )

    parser.add_argument(
        "--main-audio",
        type=str,
        help="Nazwa głównego pliku audio (używane z presetami)",
    )

    parser.add_argument(
        "--open-blender",
        action="store_true",
        help="Automatycznie otwórz Blender po utworzeniu projektu",
    )

    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="Wyświetl listę dostępnych presetów i zakończ",
    )

    # Mutually exclusive group for config sources (required unless --list-presets)
    config_group = parser.add_mutually_exclusive_group(required=False)

    config_group.add_argument(
        "--config",
        type=Path,
        help="Ścieżka do pliku konfiguracji YAML",
    )

    # Get available presets dynamically for help text
    available_presets = get_available_presets()
    preset_list = ", ".join(available_presets)

    config_group.add_argument(
        "--preset",
        type=str,
        help=f"Nazwa presetu konfiguracji ({preset_list})",
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
        raise ValueError(
            f"❌ Stare nagranie bez metadata.json: {recording_dir}\n"
            f"💡 To nagranie pochodzi sprzed aktualizacji OBS script.\n"
            f"🔧 Przenieś je do osobnego katalogu lub wygeneruj metadata.json ręcznie."
        )

    # Check for extracted directory
    extracted_dir = recording_dir / "extracted"
    if not extracted_dir.exists():
        raise ValueError(f"Brak katalogu extracted/ w katalogu: {recording_dir}")

    if not extracted_dir.is_dir():
        raise ValueError(f"extracted/ nie jest katalogiem w: {recording_dir}")

    # Check if extracted directory has any files
    if not any(extracted_dir.iterdir()):
        raise ValueError(f"Katalog extracted/ jest pusty w: {recording_dir}")


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    args = parse_args()

    # Handle --list-presets first, before any validation
    if args.list_presets:
        try:
            manager = PresetManager()
            presets = manager.list_presets()
            print("📋 Dostępne presety:")
            for preset in presets:
                print(f"  • {preset}")
            return 0
        except Exception as e:
            print(f"❌ Błąd podczas ładowania presetów: {e}")
            return 1

    # Validate required arguments when not using --list-presets
    if not args.recording_dir:
        print("❌ Błąd: Wymagany jest recording_dir")
        print("💡 Użyj --help aby zobaczyć dostępne opcje")
        return 1

    if not args.config and not args.preset:
        print("❌ Błąd: Wymagany jest --config lub --preset")
        print("💡 Użyj --help aby zobaczyć dostępne opcje")
        print("📋 Użyj --list-presets aby zobaczyć dostępne presety")
        return 1

    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    try:
        # Handle preset configuration if provided
        if args.preset:
            # Validate preset exists before proceeding
            validate_preset(args.preset)

            logger.info(f"Generating configuration from preset: {args.preset}")

            # Prepare preset overrides from CLI arguments
            preset_overrides = {}
            if args.main_audio:
                preset_overrides["main_audio"] = args.main_audio

            # Generate configuration from preset
            generator = CinemonConfigGenerator()
            config_path = generator.generate_config_from_preset(
                args.recording_dir, args.preset, **preset_overrides
            )

            logger.info(f"Generated configuration: {config_path}")

            # Create Blender project manager
            manager = BlenderProjectManager()

            # Create VSE project with generated YAML file directly
            logger.info("Creating Blender VSE project with preset configuration...")
            project_path = manager.create_vse_project_with_yaml_file(
                args.recording_dir, config_path
            )

            print(
                f"✅ Projekt Blender VSE utworzony z presetu {args.preset}: {project_path}"
            )

            # Auto-open Blender if requested
            if args.open_blender:
                logger.info("Opening Blender with Video Editing workspace...")
                open_blender_with_video_editing(project_path)

            return 0

        # Handle YAML configuration if provided
        elif args.config:
            logger.info(f"Using YAML configuration file: {args.config}")

            # Create Blender project manager
            manager = BlenderProjectManager()

            # Create VSE project with YAML config file directly
            logger.info("Creating Blender VSE project with YAML configuration...")
            project_path = manager.create_vse_project_with_yaml_file(
                args.recording_dir, args.config
            )

            print(f"✅ Projekt Blender VSE utworzony z YAML config: {project_path}")

            # Auto-open Blender if requested
            if args.open_blender:
                logger.info("Opening Blender with Video Editing workspace...")
                open_blender_with_video_editing(project_path)

            return 0

        # This should never happen due to required=True, but just in case
        else:
            raise ValueError("Must specify either --preset or --config parameter")

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
