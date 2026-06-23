# ABOUTME: CLI entry point for cymatic (cymatic-render).
# ABOUTME: Builds a VisualizerConfig from a recording dir and drives the runner.

"""Command-line interface for cymatic.

Usage:
    cymatic-render <recording_dir> [--main-audio NAME] [--analysis-file PATH]
                   [--audio-file PATH] [--fps N] [--blender-executable PATH]

Resolves the beatrix ``*_analysis.json`` (explicit ``--analysis-file`` or, when
omitted, via ``AudioValidator.detect_main_audio`` on ``<recording_dir>/extracted``
to pick the main audio and derive ``analysis/<stem>_analysis.json``), builds a
:class:`VisualizerConfig`, and calls the host-side runner.

The runner resolves the output path under ``blender/render/`` itself, so
``output_mp4`` is left empty here.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from beatrix.exceptions import MultipleAudioFilesError, NoAudioFileError
from setka_common.file_structure.specialized import RecordingStructureManager

from cymatic.config import DEFAULT_BLENDER_EXECUTABLE, VisualizerConfig
from cymatic.runner import render

logger = logging.getLogger(__name__)


def _detect_audio(recording_dir: Path, main_audio: str | None) -> Path:
    """Detect the main audio file in ``<recording_dir>/extracted``.

    AudioValidator takes the extracted/ dir, NOT the recording root.

    Raises:
        NoAudioFileError / MultipleAudioFilesError: from beatrix validation.
    """
    from beatrix.core.audio_validator import AudioValidator

    extracted_dir = recording_dir / RecordingStructureManager.EXTRACTED_DIRNAME
    validator = AudioValidator()
    return validator.detect_main_audio(extracted_dir, specified_audio=main_audio)


def _resolve_analysis_file(
    recording_dir: Path,
    analysis_file: str | None,
    main_audio: str | None,
) -> tuple[Path, Path | None]:
    """Resolve the analysis JSON path (and detected audio) for a recording dir.

    Args:
        recording_dir: Recording base directory.
        analysis_file: Explicit analysis JSON path (takes precedence).
        main_audio: Optional main-audio filename hint for detection.

    Returns:
        ``(analysis_path, audio_path_or_None)``. The audio path is ``None`` when
        an explicit ``--analysis-file`` was given (no detection performed).

    Raises:
        FileNotFoundError: If the resolved analysis file does not exist.
    """
    if analysis_file:
        path = Path(analysis_file)
        if not path.exists():
            raise FileNotFoundError(f"Analysis file not found: {path}")
        return path, None

    # Detect the main audio in extracted/ and derive its analysis path.
    audio_path = _detect_audio(recording_dir, main_audio)

    analysis_path = (
        recording_dir
        / RecordingStructureManager.ANALYSIS_DIRNAME
        / f"{Path(audio_path).stem}_analysis.json"
    )
    if not analysis_path.exists():
        raise FileNotFoundError(
            f"Analysis file not found: {analysis_path}. "
            "Run beatrix to generate the analysis first."
        )
    return analysis_path, Path(audio_path)


def main(argv=None) -> int:
    """Entry point for the ``cymatic-render`` script.

    Returns:
        int: process exit code (0 on success, non-zero on error).
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="cymatic-render",
        description="Render a 3D audio visualizer from a beatrix analysis.",
    )
    parser.add_argument("recording_dir", help="Path to the recording directory")
    parser.add_argument(
        "--main-audio",
        default=None,
        help="Main audio filename in extracted/ (when analysis file is auto-detected)",
    )
    parser.add_argument(
        "--analysis-file",
        default=None,
        help="Explicit path to the beatrix *_analysis.json (overrides detection)",
    )
    parser.add_argument(
        "--audio-file",
        default=None,
        help="Audio file to mux into the render (overrides auto-detection)",
    )
    parser.add_argument(
        "--fps", type=int, default=30, help="Render fps (default: 30)"
    )
    parser.add_argument(
        "--blender-executable",
        default=DEFAULT_BLENDER_EXECUTABLE,
        help="Path to the Blender executable",
    )

    args = parser.parse_args(argv)

    recording_dir = Path(args.recording_dir)
    if not recording_dir.is_dir():
        print(
            f"cymatic-render: recording directory not found: {recording_dir}",
            file=sys.stderr,
        )
        return 1

    try:
        analysis_file, detected_audio = _resolve_analysis_file(
            recording_dir, args.analysis_file, args.main_audio
        )
    except (
        FileNotFoundError,
        NoAudioFileError,
        MultipleAudioFilesError,
        ValueError,
    ) as exc:
        # Surfaces FileNotFoundError plus beatrix audio-validation errors
        # (NoAudioFileError / MultipleAudioFilesError, Polish messages).
        print(f"cymatic-render: {exc}", file=sys.stderr)
        return 1

    # Forward audio so renders aren't silent: explicit --audio-file wins,
    # otherwise the auto-detected main audio (if any).
    if args.audio_file:
        audio_file = args.audio_file
    elif detected_audio is not None:
        audio_file = str(detected_audio)
    else:
        audio_file = None

    # Distinguish the two no-audio cases so neither fails silently:
    #  - an explicit --analysis-file skips detection entirely, so no audio is a
    #    deliberate analysis-only run -> INFO "rendering silent";
    #  - detection ran (no --analysis-file) but found nothing -> WARNING, since
    #    the user likely expected the detected main audio to be muxed.
    if audio_file is None:
        if args.analysis_file:
            logger.info(
                "No --audio-file and explicit --analysis-file given; "
                "rendering silent (no audio track)."
            )
        else:
            logger.warning(
                "No audio detected in %s and no --audio-file given; the render "
                "will be silent.",
                recording_dir / RecordingStructureManager.EXTRACTED_DIRNAME,
            )

    config = VisualizerConfig(
        analysis_file=str(analysis_file),
        output_mp4="",  # runner resolves the path under blender/render/
        base_directory=str(recording_dir),
        fps=args.fps,
        blender_executable=args.blender_executable,
        audio_file=audio_file,
    )

    try:
        output = render(config)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"cymatic-render: {exc}", file=sys.stderr)
        return 1

    print(f"cymatic-render: output -> {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
