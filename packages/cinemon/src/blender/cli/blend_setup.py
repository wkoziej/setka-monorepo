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
from ..config import CinemonConfigGenerator
from beatrix import AudioValidationError
from setka_common.config import BlenderYAMLConfig, YAMLConfigLoader


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
            
            # Prepare preset overrides from CLI arguments
            preset_overrides = {}
            if args.main_audio:
                preset_overrides["main_audio"] = args.main_audio
            
            # Generate configuration from preset
            generator = CinemonConfigGenerator()
            config_path = generator.generate_preset(
                args.recording_dir, 
                args.preset, 
                **preset_overrides
            )
            
            logger.info(f"Generated configuration: {config_path}")
            
            # Create Blender project manager
            manager = BlenderProjectManager()
            
            # Load generated YAML config
            yaml_config = load_yaml_config(config_path)
            
            # Create VSE project with generated config
            logger.info("Creating Blender VSE project with preset configuration...")
            project_path = manager.create_vse_project_with_config(
                args.recording_dir,
                yaml_config
            )
            
            print(f"✅ Projekt Blender VSE utworzony z presetu {args.preset}: {project_path}")
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
