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
from typing import Optional

import yaml
from beatrix import AudioValidationError
from setka_common.config import BlenderYAMLConfig, YAMLConfigLoader

from ..config.media_discovery import MediaDiscovery
from ..project_manager import BlenderProjectManager


def open_blender_with_video_editing(blend_file_path: Path, preset_name: str = None) -> None:
    """
    Open Blender GUI with the blend file using Video_Editing app template.
    Preset auto-loading is handled by the addon via metadata JSON.

    Args:
        blend_file_path: Path to .blend file to open
        preset_name: Ignored - kept for backward compatibility
    """
    try:
        # Simple Blender execution - .blend file now has Video Editing workspace built-in
        cmd = [
            "snap", "run", "blender",
            str(blend_file_path)
        ]

        print("🎬 Otwieranie Blender z wbudowanym workspace Video Editing...")
        print(f"📁 Plik: {blend_file_path}")
        print("🎯 Built-in Video Editing workspace + auto-loading presetu")

        # Start Blender in background (non-blocking)
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
  %(prog)s ./recording_20250105_143022 --preset vintage
  %(prog)s ./recording_20250105_143022 --preset music-video --verbose
  %(prog)s ./recording_20250105_143022 --preset beat-switch --main-audio "main_audio.m4a"
  %(prog)s ./recording_20250105_143022 --config custom_config.yaml
  %(prog)s ./recording_20250105_143022 --config path/to/config.yaml --force
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
        help="Nazwa głównego pliku audio (używane z presetami)",
    )

    parser.add_argument(
        "--open-blender",
        action="store_true",
        help="Automatycznie otwórz Blender po utworzeniu projektu",
    )

    # Mutually exclusive group for config sources (required)
    config_group = parser.add_mutually_exclusive_group(required=True)

    config_group.add_argument(
        "--config",
        type=Path,
        help="Ścieżka do pliku konfiguracji YAML",
    )

    config_group.add_argument(
        "--preset",
        type=str,
        help="Nazwa presetu konfiguracji (vintage, music-video, minimal, beat-switch)",
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
        raise ValueError(f"❌ Stare nagranie bez metadata.json: {recording_dir}\n"
                        f"💡 To nagranie pochodzi sprzed aktualizacji OBS script.\n"
                        f"🔧 Przenieś je do osobnego katalogu lub wygeneruj metadata.json ręcznie.")

    # Check for extracted directory
    extracted_dir = recording_dir / "extracted"
    if not extracted_dir.exists():
        raise ValueError(f"Brak katalogu extracted/ w katalogu: {recording_dir}")

    if not extracted_dir.is_dir():
        raise ValueError(f"extracted/ nie jest katalogiem w: {recording_dir}")

    # Check if extracted directory has any files
    if not any(extracted_dir.iterdir()):
        raise ValueError(f"Katalog extracted/ jest pusty w: {recording_dir}")






def load_yaml_config(config_path: Path) -> BlenderYAMLConfig:
    """
    Load and validate YAML configuration.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        BlenderYAMLConfig: Loaded configuration

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If config validation fails
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        loader = YAMLConfigLoader()
        config = loader.load_config(config_path)
        return config
    except Exception as e:
        raise ValueError(f"Failed to load YAML configuration: {e}")




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
        # Handle preset configuration if provided
        if args.preset:
            logger.info(f"Generating configuration from preset: {args.preset}")

            # Use addon preset files directly (new strip_animations format)
            config_path = generate_config_from_addon_preset(
                args.recording_dir,
                args.preset,
                args.main_audio
            )

            logger.info(f"Generated configuration: {config_path}")

            # Create Blender project manager
            manager = BlenderProjectManager()

            # Load generated YAML config
            yaml_loader = YAMLConfigLoader()
            yaml_config = yaml_loader.load_config(config_path)

            # Create VSE project with generated config (use original config file path)
            logger.info("Creating Blender VSE project with preset configuration...")
            project_path = manager.create_vse_project_with_config(
                args.recording_dir,
                yaml_config,
                preset_name=args.preset,
                original_config_path=config_path  # Pass original config file
            )

            print(f"✅ Projekt Blender VSE utworzony z presetu {args.preset}: {project_path}")

            # Auto-open Blender if requested
            if args.open_blender:
                logger.info("Opening Blender...")
                open_blender_with_video_editing(project_path, args.preset)

            return 0

        # Handle YAML configuration if provided
        elif args.config:
            logger.info(f"Loading YAML configuration: {args.config}")
            yaml_config = load_yaml_config(args.config)

            # Create Blender project manager
            manager = BlenderProjectManager()

            # Create VSE project with YAML config
            logger.info("Creating Blender VSE project with YAML configuration...")
            project_path = manager.create_vse_project_with_config(
                args.recording_dir,
                yaml_config
            )

            print(f"✅ Projekt Blender VSE utworzony z YAML config: {project_path}")

            # Auto-open Blender if requested
            if args.open_blender:
                logger.info("Opening Blender...")
                open_blender_with_video_editing(project_path, None)  # No preset for YAML config

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


def generate_config_from_addon_preset(recording_dir: Path, preset_name: str, main_audio: Optional[str] = None) -> Path:
    """
    Generate configuration from addon preset file (new strip_animations format).

    Args:
        recording_dir: Path to recording directory
        preset_name: Name of preset (e.g., 'vintage')
        main_audio: Optional main audio override

    Returns:
        Path to generated configuration file

    Raises:
        ValueError: If preset not found or validation fails
    """
    # Find addon preset file
    addon_presets_dir = Path(__file__).parent.parent.parent.parent / "blender_addon" / "example_presets"
    preset_file = addon_presets_dir / f"{preset_name}.yaml"

    if not preset_file.exists():
        raise ValueError(f"Preset '{preset_name}' not found at: {preset_file}")

    # Load preset template
    with open(preset_file, 'r', encoding='utf-8') as f:
        preset_data = yaml.safe_load(f)

    # Discover and validate media files
    discovery = MediaDiscovery(recording_dir)
    validation_result = discovery.validate_structure()

    if not validation_result.is_valid:
        error_message = "; ".join(validation_result.errors)
        raise ValueError(f"Invalid recording directory: {error_message}")

    # Auto-discover media files
    video_files = discovery.discover_video_files()
    audio_files = discovery.discover_audio_files()

    # Determine main audio
    if not main_audio:
        main_audio = discovery.detect_main_audio()
        if not main_audio:
            if len(audio_files) > 1:
                raise ValueError(
                    f"Multiple audio files found, specify --main-audio: {[f.name for f in audio_files]}"
                )
            elif len(audio_files) == 1:
                main_audio = audio_files[0].name

    # Update preset with actual project data
    config_data = preset_data.copy()

    # Update project section
    config_data["project"]["video_files"] = [f.name if hasattr(f, 'name') else str(f) for f in video_files]
    if main_audio:
        config_data["project"]["main_audio"] = main_audio if isinstance(main_audio, str) else main_audio.name

    # Update audio analysis file path
    if main_audio and "audio_analysis" in config_data:
        audio_stem = Path(main_audio).stem
        config_data["audio_analysis"]["file"] = f"analysis/{audio_stem}_analysis.json"

    # Map Video_X to actual filename stems in strip_animations
    if "strip_animations" in config_data and video_files:
        new_strip_animations = {}

        # Create mapping from Video_X to filename stems
        for i, video_file in enumerate(video_files):
            video_key = f"Video_{i + 1}"
            filename_stem = Path(video_file).stem

            # If there's animation config for this Video_X, map it to filename
            if video_key in config_data["strip_animations"]:
                new_strip_animations[filename_stem] = config_data["strip_animations"][video_key]

        # Replace with mapped animations
        config_data["strip_animations"] = new_strip_animations

    # Add preset name to config for VSE script
    config_data["preset_name"] = preset_name

    # Generate output path
    output_path = recording_dir / f"animation_config_{preset_name}.yaml"

    # Write generated config
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return output_path


if __name__ == "__main__":
    sys.exit(main())
