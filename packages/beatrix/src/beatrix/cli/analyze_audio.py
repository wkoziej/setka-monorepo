# ABOUTME: CLI command for audio analysis of recordings
# ABOUTME: Provides command-line interface for extracting animation timing data

"""
CLI tool for analyzing audio files to extract animation timing data.

This module provides a command-line interface for analyzing audio files
and generating JSON data suitable for Blender VSE animations.
"""

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

    This function now delegates to the modernized click-based CLI.
    """
    from .click_cli import main as click_main

    click_main()


if __name__ == "__main__":
    main()
