# ABOUTME: CLI command for audio analysis of recordings
# ABOUTME: Provides command-line interface for extracting animation timing data

"""
CLI tool for analyzing audio files to extract animation timing data.

This module provides a command-line interface for analyzing audio files
and generating JSON data suitable for Blender VSE animations.
"""

import sys
import logging
from pathlib import Path

from ..core.audio_analyzer import AudioAnalyzer

logger = logging.getLogger(__name__)


def analyze_audio_command(
    audio_file: Path,
    output_dir: Path,
    beat_division: int = 8,
    min_onset_interval: float = 2.0,
) -> Path:
    """
    Analyze audio file and save animation timing data.

    Args:
        audio_file: Path to audio file to analyze
        output_dir: Directory to save analysis results
        beat_division: Beat division for animation events
        min_onset_interval: Minimum interval between onset events

    Returns:
        Path: Path to saved analysis JSON file

    Raises:
        FileNotFoundError: If audio file doesn't exist
        RuntimeError: If analysis fails
    """
    # Validate input file
    audio_file = Path(audio_file)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    base_name = audio_file.stem
    output_filename = f"{base_name}_analysis.json"
    output_path = output_dir / output_filename

    logger.info(f"Analyzing audio file: {audio_file}")
    logger.info(f"Output will be saved to: {output_path}")

    try:
        # Create analyzer and analyze
        analyzer = AudioAnalyzer()
        analysis_result = analyzer.analyze_for_animation(
            audio_file,
            beat_division=beat_division,
            min_onset_interval=min_onset_interval,
        )

        # Save results
        analyzer.save_analysis(analysis_result, output_path)

        logger.info(f"Analysis completed successfully: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise RuntimeError(f"Audio analysis failed: {e}")


def main() -> None:
    """
    Main CLI entry point for audio analysis.

    Usage:
        python -m cli.analyze_audio <audio_file> <output_dir> [options]

    Options:
        --beat-division <int>         Beat division for events (default: 8)
        --min-onset-interval <float>  Minimum onset interval (default: 2.0)
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parse command line arguments
    args = sys.argv[1:]

    if len(args) < 2:
        print("Usage: python -m cli.analyze_audio <audio_file> <output_dir> [options]")
        print("Options:")
        print("  --beat-division <int>         Beat division for events (default: 8)")
        print("  --min-onset-interval <float>  Minimum onset interval (default: 2.0)")
        sys.exit(1)

    # Required arguments
    audio_file = Path(args[0])
    output_dir = Path(args[1])

    # Optional arguments
    beat_division = 8
    min_onset_interval = 2.0

    # Parse optional arguments
    i = 2
    while i < len(args):
        if args[i] == "--beat-division" and i + 1 < len(args):
            beat_division = int(args[i + 1])
            i += 2
        elif args[i] == "--min-onset-interval" and i + 1 < len(args):
            min_onset_interval = float(args[i + 1])
            i += 2
        else:
            print(f"Unknown option: {args[i]}")
            sys.exit(1)

    try:
        result_path = analyze_audio_command(
            audio_file,
            output_dir,
            beat_division=beat_division,
            min_onset_interval=min_onset_interval,
        )
        print(f"Analysis complete: {result_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
