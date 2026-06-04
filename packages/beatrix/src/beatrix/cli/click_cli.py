# ABOUTME: Modernized CLI using click framework for better argument parsing
# ABOUTME: Replaces manual sys.argv parsing with declarative click interface

"""
Modernized CLI interface for Beatrix using click framework.

This module provides a more robust and user-friendly command-line interface
for audio analysis, replacing the manual sys.argv parsing approach.
"""

import json
import logging
from pathlib import Path

import click

from ..core.audio_analyzer import AudioAnalyzer
from .. import __version__
from setka_common.file_structure.specialized.recording import (
    RecordingStructureManager,
    sanitize_stem_name,
)


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


def _analyze_single_file(
    audio_file: Path,
    output_dir: Path,
    beat_division: int,
    min_onset_interval: float,
    output_name: str | None = None,
) -> tuple[Path, dict]:
    """Analyze a single audio file and save results to output_dir.

    Returns a (output_path, analysis_result) tuple.
    When output_name is provided, uses <output_name>_analysis.json as the
    output filename; otherwise falls back to {audio_file.stem}_analysis.json.
    Raises click.ClickException on any failure.
    """
    logger = logging.getLogger(__name__)

    label = output_name if output_name is not None else audio_file.stem
    output_filename = f"{label}_analysis.json"
    output_path = output_dir / output_filename

    logger.info(f"Analyzing audio file: {audio_file}")
    logger.info(f"Output will be saved to: {output_path}")
    logger.debug(
        f"Parameters: beat_division={beat_division}, min_onset_interval={min_onset_interval}"
    )

    analyzer = AudioAnalyzer()
    analysis_result = analyzer.analyze_for_animation(
        audio_file,
        beat_division=beat_division,
        min_onset_interval=min_onset_interval,
    )
    analyzer.save_analysis(analysis_result, output_path)

    click.echo(f"Analysis complete: {output_path}")
    logger.info(f"Analysis completed successfully: {output_path}")
    return output_path, analysis_result


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

        _analyze_single_file(audio_file, output_dir, beat_division, min_onset_interval)  # noqa: result unused

    except FileNotFoundError as e:
        click.echo(f"Error: Audio file not found: {audio_file}", err=True)
        raise click.ClickException(str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        click.echo(f"Error: Audio analysis failed: {e}", err=True)
        raise click.ClickException(f"Audio analysis failed: {e}")


def _determine_role_and_origin(
    audio_file: Path, recording_dir: Path
) -> tuple[str, str]:
    """Determine role and origin of an audio source based on its location.

    Location rules:
    - directly in mixed/        → role="master", origin="mixed"
    - in mixed/stems/           → role="stem",   origin="mixed"
    - anywhere under bitwig/    → role="stem",   origin="bitwig"
    - in extracted/             → role="main",   origin="extracted"

    Falls back to role="main", origin="extracted" for unrecognised paths.
    """
    try:
        rel = audio_file.relative_to(recording_dir)
    except ValueError:
        return "main", "extracted"

    parts = rel.parts
    if parts[0] == RecordingStructureManager.MIXED_DIRNAME:
        if len(parts) >= 3 and parts[1] == "stems":
            return "stem", "mixed"
        if len(parts) == 2:
            return "master", "mixed"
    if parts[0] == RecordingStructureManager.BITWIG_DIRNAME:
        return "stem", "bitwig"
    if parts[0] == RecordingStructureManager.EXTRACTED_DIRNAME:
        return "main", "extracted"

    return "main", "extracted"


@cli.command("analyze-recording")
@click.argument("recording_dir", type=click.Path(exists=True, path_type=Path))
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
def analyze_recording(recording_dir, beat_division, min_onset_interval):
    """
    Analyze all audio sources in a recording directory.

    RECORDING_DIR: Path to the recording directory

    Prefers mixed/ (master + stems) over extracted/ as audio source.
    Writes one <label>_analysis.json per audio file into analysis/ and
    saves a manifest analysis/index.json with role/origin/label/source/analysis
    for each source.
    """
    logger = logging.getLogger(__name__)

    try:
        audio_sources = RecordingStructureManager.find_analysis_audio_sources(
            recording_dir
        )
    except ValueError as e:
        raise click.ClickException(f"Stem name collision: {e}")

    if not audio_sources:
        raise click.ClickException(
            f"No audio files found in '{recording_dir}'. "
            "Add audio to mixed/ or extracted/ before analyzing."
        )

    analysis_dir = RecordingStructureManager.ensure_analysis_dir(recording_dir)

    manifest_sources = []
    for audio_file in audio_sources:
        label = sanitize_stem_name(audio_file.stem)
        role, origin = _determine_role_and_origin(audio_file, recording_dir)
        try:
            output_path, analysis_result = _analyze_single_file(
                audio_file,
                analysis_dir,
                beat_division,
                min_onset_interval,
                output_name=label,
            )
        except Exception as e:
            logger.error(f"Analysis failed for {audio_file}: {e}")
            raise click.ClickException(f"Audio analysis failed for '{audio_file}': {e}")

        manifest_sources.append(
            {
                "role": role,
                "origin": origin,
                "label": label,
                "source": audio_file.relative_to(recording_dir).as_posix(),
                "analysis": output_path.relative_to(recording_dir).as_posix(),
                "duration": analysis_result.get("duration"),
                "sample_rate": analysis_result.get("sample_rate"),
            }
        )

    index_path = analysis_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {"version": 1, "sources": manifest_sources}, indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    logger.info(f"Manifest written: {index_path}")


def main():
    """Entry point for the CLI."""
    cli()
