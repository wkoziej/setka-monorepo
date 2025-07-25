# ABOUTME: CLI for generating YAML configuration files using CinemonConfigGenerator
# ABOUTME: Provides commands for preset-based config generation and preset listing

"""CLI for generating cinemon YAML configuration files."""

import argparse
import sys
from pathlib import Path

from ..config import CinemonConfigGenerator, PresetManager


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for cinemon-generate-config CLI."""
    parser = argparse.ArgumentParser(
        prog="cinemon-generate-config",
        description="Generate YAML configuration for cinemon"
    )

    # Add mutually exclusive group for main commands
    group = parser.add_mutually_exclusive_group(required=True)

    # Preset generation command
    group.add_argument(
        "recording_dir",
        nargs="?",
        type=Path,
        help="Path to recording directory"
    )

    # List presets command
    group.add_argument(
        "--list-presets",
        action="store_true",
        help="List all available presets"
    )

    # Preset generation parameters
    parser.add_argument(
        "--preset",
        type=str,
        help="Preset name to use for configuration generation"
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Override layout seed value"
    )

    parser.add_argument(
        "--main-audio",
        type=str,
        help="Specify main audio file (required if multiple audio files exist)"
    )

    return parser


def generate_config_command(args) -> int:
    """
    Execute config generation command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        recording_dir = Path(args.recording_dir)

        if not recording_dir.exists():
            print(f"Error: Recording directory not found: {recording_dir}")
            return 1

        # Prepare overrides
        overrides = {}
        if args.seed is not None:
            overrides["seed"] = args.seed
        if args.main_audio:
            overrides["main_audio"] = args.main_audio

        # Generate configuration
        generator = CinemonConfigGenerator()
        config_path = generator.generate_preset(
            recording_dir,
            args.preset,
            **overrides
        )

        print(f"✅ Configuration generated: {config_path}")
        print(f"   Preset: {args.preset}")
        if overrides:
            print(f"   Overrides: {overrides}")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


def list_presets_command() -> int:
    """
    Execute list presets command.

    Returns:
        Exit code (0 for success)
    """
    try:
        preset_manager = PresetManager()
        presets = preset_manager.list_presets()

        print("Available presets:")
        print()

        for preset_name in presets:
            preset_config = preset_manager.get_preset(preset_name)
            print(f"  {preset_name}")
            print(f"    {preset_config.description}")
            print()

        return 0

    except Exception as e:
        print(f"Error listing presets: {e}")
        return 1


def main() -> int:
    """
    Main entry point for cinemon-generate-config CLI.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        parser = create_parser()
        args = parser.parse_args()

        # Handle list presets command
        if args.list_presets:
            return list_presets_command()

        # Validate recording directory argument
        if not args.recording_dir:
            print("Error: recording_dir is required when not using --list-presets")
            parser.print_help()
            return 1

        # Validate preset argument
        if not args.preset:
            print("Error: --preset is required for config generation")
            parser.print_help()
            return 1

        # Execute config generation
        return generate_config_command(args)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except SystemExit as e:
        # Handle argparse calling sys.exit() for help/error
        return e.code if e.code is not None else 0
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
