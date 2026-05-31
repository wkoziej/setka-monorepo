# ABOUTME: CLI entry point for cymatic (cymatic-render).
# ABOUTME: Builds a VisualizerConfig from a recording dir and drives the runner.

"""Command-line interface for cymatic.

Usage:
    cymatic-render <recording_dir> [--main-audio NAME] [--analysis-file PATH]
                   [--fps N] [--blender-executable PATH]

Resolves the beatrix ``*_analysis.json`` (explicit ``--analysis-file`` or, when
omitted, via ``AudioValidator.detect_main_audio`` on ``<recording_dir>/extracted``
to pick the main audio and derive ``analysis/<stem>_analysis.json``), builds a
:class:`VisualizerConfig`, and calls the host-side runner.

The runner resolves the output path under ``blender/render/`` itself, so
``output_mp4`` is left empty here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from setka_common.file_structure.specialized import RecordingStructureManager

from cymatic.config import DEFAULT_BLENDER_EXECUTABLE, VisualizerConfig
from cymatic.runner import render


def _resolve_analysis_file(
    recording_dir: Path,
    analysis_file: str | None,
    main_audio: str | None,
) -> Path:
    """Resolve the analysis JSON path for a recording directory.

    Args:
        recording_dir: Recording base directory.
        analysis_file: Explicit analysis JSON path (takes precedence).
        main_audio: Optional main-audio filename hint for detection.

    Returns:
        Path to the ``*_analysis.json`` file.

    Raises:
        FileNotFoundError: If the resolved analysis file does not exist.
    """
    if analysis_file:
        path = Path(analysis_file)
        if not path.exists():
            raise FileNotFoundError(f"Analysis file not found: {path}")
        return path

    # Detect the main audio in extracted/ and derive its analysis path.
    # AudioValidator takes the extracted/ dir, NOT the recording root.
    from beatrix.core.audio_validator import AudioValidator

    extracted_dir = recording_dir / RecordingStructureManager.EXTRACTED_DIRNAME
    validator = AudioValidator()
    audio_path = validator.detect_main_audio(extracted_dir, specified_audio=main_audio)

    analysis_path = (
        recording_dir / "analysis" / f"{Path(audio_path).stem}_analysis.json"
    )
    if not analysis_path.exists():
        raise FileNotFoundError(
            f"Analysis file not found: {analysis_path}. "
            "Run beatrix to generate the analysis first."
        )
    return analysis_path


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
        print(f"cymatic-render: recording directory not found: {recording_dir}")
        return 1

    try:
        analysis_file = _resolve_analysis_file(
            recording_dir, args.analysis_file, args.main_audio
        )
    except Exception as exc:
        # Surfaces FileNotFoundError plus beatrix audio-validation errors
        # (NoAudioFileError / MultipleAudioFilesError, Polish messages).
        print(f"cymatic-render: {exc}")
        return 1

    config = VisualizerConfig(
        analysis_file=str(analysis_file),
        output_mp4="",  # runner resolves the path under blender/render/
        base_directory=str(recording_dir),
        fps=args.fps,
        blender_executable=args.blender_executable,
    )

    try:
        output = render(config)
    except RuntimeError as exc:
        print(f"cymatic-render: {exc}")
        return 1

    print(f"cymatic-render: output -> {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
