# ABOUTME: Modernized CLI using click framework for better argument parsing
# ABOUTME: Replaces manual sys.argv parsing with declarative click interface

"""
Modernized CLI interface for Beatrix using click framework.

This module provides a more robust and user-friendly command-line interface
for audio analysis, replacing the manual sys.argv parsing approach.
"""

import logging
from pathlib import Path

import click

from ..core.audio_analyzer import AudioAnalyzer
from .. import __version__


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.version_option(version=__version__, prog_name="beatrix")
@click.pass_context
def cli(ctx, verbose):
    """
    Audio analysis CLI for Beatrix.

    Beatrix provides audio analysis capabilities for animation timing,
    including beat detection, energy analysis, and structural segmentation.
    """
    # Configure logging based on verbosity
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("audio_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_dir", type=click.Path(path_type=Path))
@click.option(
    "--beat-division",
    type=click.IntRange(min=1),
    default=8,
    help="Beat division for animation events (default: 8)",
)
@click.option(
    "--min-onset-interval",
    type=click.FloatRange(min=0.1),
    default=2.0,
    help="Minimum interval between onset events in seconds (default: 2.0)",
)
def analyze(audio_file, output_dir, beat_division, min_onset_interval):
    """
    Analyze audio file and save animation timing data.

    AUDIO_FILE: Path to the audio file to analyze
    OUTPUT_DIR: Directory where analysis results will be saved

    The analysis will extract beat timings, energy peaks, and structural
    segments suitable for driving animations in video editing software.
    """
    logger = logging.getLogger(__name__)

    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate output filename
        base_name = audio_file.stem
        output_filename = f"{base_name}_analysis.json"
        output_path = output_dir / output_filename

        logger.info(f"Analyzing audio file: {audio_file}")
        logger.info(f"Output will be saved to: {output_path}")
        logger.debug(
            f"Parameters: beat_division={beat_division}, min_onset_interval={min_onset_interval}"
        )

        # Create analyzer and analyze
        analyzer = AudioAnalyzer()
        analysis_result = analyzer.analyze_for_animation(
            audio_file,
            beat_division=beat_division,
            min_onset_interval=min_onset_interval,
        )

        # Save results
        analyzer.save_analysis(analysis_result, output_path)

        click.echo(f"Analysis complete: {output_path}")
        logger.info(f"Analysis completed successfully: {output_path}")

    except FileNotFoundError as e:
        click.echo(f"Error: Audio file not found: {audio_file}", err=True)
        raise click.ClickException(str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        click.echo(f"Error: Audio analysis failed: {e}", err=True)
        raise click.ClickException(f"Audio analysis failed: {e}")


def main():
    """Entry point for the CLI."""
    cli()
