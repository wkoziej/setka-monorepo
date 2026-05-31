# ABOUTME: Host-side runner — builds the Blender subprocess command and renders.
# ABOUTME: Mirrors cinemon's BlenderProjectManager (subprocess + "--" + --config).

"""Host-side runner for the cymatic 3D audio visualizer.

Builds the Blender headless command, serializes the ``VisualizerConfig`` to a
temp file, runs ``build_scene.py`` inside Blender, and returns the output path
under ``blender/render/``.

Pattern mirrors ``cinemon`` (``BlenderProjectManager``):

    [blender_exec, "--background", "--python", build_scene.py,
     "--", "--config", <config_file>]

with ``subprocess.run(..., capture_output=True, text=True, check=True)`` and a
``RuntimeError`` carrying stderr on ``CalledProcessError``.

macOS note: the default ``blender_executable`` in ``VisualizerConfig`` is the
explicit ``/Applications/Blender.app/...`` path. The snap branch only fires for
the literal ``"blender"`` command (Linux), mirroring cinemon.

RENDER CAVEAT (documented, NOT solved here):
    The dev Blender 5.1.2 has NO internal FFMPEG encoder and no system ``ffmpeg``
    on PATH, so direct mp4 muxing is not yet possible. The intended target is a
    frames -> mux approach: ``build_scene.py`` renders PNG frames, and a later
    step muxes them to mp4 via external ffmpeg (exact codec deferred to
    ``project_setup.py``, matching cinemon's FFMPEG/H264/AAC settings).
    TODO(Unit 9 follow-up): add a frames->mp4 ffmpeg mux seam once ffmpeg is
    available. For now the runner builds/executes the command and returns the
    intended output path; it does not perform actual video encoding.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from setka_common.file_structure.specialized import RecordingStructureManager

from cymatic.config import VisualizerConfig

logger = logging.getLogger(__name__)

# Resolve the in-Blender script the same way cinemon's BlenderProjectManager
# does: packages/cymatic/src/cymatic/runner.py -> packages/cymatic/blender_script/.
BUILD_SCENE_SCRIPT = (
    Path(__file__).parent.parent.parent / "blender_script" / "build_scene.py"
)


class CymaticRunner:
    """Drives the headless Blender subprocess that builds + renders the scene."""

    def __init__(
        self,
        config: VisualizerConfig,
        script_path: Optional[Path] = None,
    ) -> None:
        """Initialize the runner.

        Args:
            config: The visualizer configuration (serialized and passed to
                Blender via ``--config``).
            script_path: Override for the in-Blender ``build_scene.py`` path
                (defaults to the resolved package location).
        """
        self.config = config
        self.script_path = Path(script_path) if script_path else BUILD_SCENE_SCRIPT

    def _resolve_output_path(self) -> Path:
        """Resolve the render output path under ``blender/render/``.

        Uses ``RecordingStructureManager.ensure_blender_dir`` so directory names
        are never hardcoded; appends the ``render/`` subdir it creates.

        Returns:
            Path to the intended ``<name>.mp4`` under ``blender/render/``.
        """
        base_directory = Path(self.config.base_directory)
        blender_dir = RecordingStructureManager.ensure_blender_dir(base_directory)
        render_dir = blender_dir / "render"

        # Derive a stable output name from the analysis file stem
        # (e.g. "song_analysis.json" -> "song_analysis.mp4").
        name = Path(self.config.analysis_file).stem or base_directory.name
        return render_dir / f"{name}.mp4"

    def _build_command(self, config_path: str) -> List[str]:
        """Build the Blender headless command list.

        Args:
            config_path: Path to the serialized config temp file.

        Returns:
            The argv list for ``subprocess.run``.
        """
        executable = self.config.blender_executable

        # Snap branch is Linux-only and only for the literal "blender" command.
        # On macOS the config default is the explicit Blender.app path -> direct.
        if executable == "blender":
            prefix: List[str] = ["snap", "run", "blender"]
        else:
            prefix = [executable]

        return [
            *prefix,
            "--background",
            "--python",
            str(self.script_path),
            "--",  # separator: Blender args vs build_scene.py args
            "--config",
            config_path,
        ]

    def run(self) -> Path:
        """Serialize config, run Blender headless, return the output path.

        Returns:
            Path to the intended render output under ``blender/render/``.

        Raises:
            RuntimeError: If the in-Blender script is missing or Blender exits
                with a non-zero status (stderr is propagated).
        """
        if not self.script_path.exists():
            raise RuntimeError(f"cymatic build_scene script not found: {self.script_path}")

        output_path = self._resolve_output_path()

        # Serialize the config to a temp file passed via --config; cleaned up
        # after the subprocess so we never leave config layout on disk.
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="cymatic_config_",
            delete=False,
            encoding="utf-8",
        )
        config_path = tmp.name
        try:
            tmp.write(self.config.to_json())
            tmp.close()

            cmd = self._build_command(config_path)
            logger.debug("Executing Blender command: %s", " ".join(cmd))
            logger.debug("Working directory: %s", os.getcwd())

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=True
                )
            except subprocess.CalledProcessError as exc:
                logger.error("Blender execution failed (rc=%s)", exc.returncode)
                logger.error("Blender stdout: %s", exc.stdout)
                logger.error("Blender stderr: %s", exc.stderr)
                raise RuntimeError(f"Blender execution failed: {exc.stderr}")

            if result.stdout and result.stdout.strip():
                logger.debug("Blender stdout: %s", result.stdout)
            if result.stderr and result.stderr.strip():
                logger.debug("Blender stderr: %s", result.stderr)

            logger.info("cymatic render finished, output: %s", output_path)
            return output_path
        finally:
            # Clean up the temp config regardless of success/failure.
            try:
                os.unlink(config_path)
            except OSError:
                logger.warning("Could not remove temp config: %s", config_path)


def render(config: VisualizerConfig) -> Path:
    """Convenience wrapper: build a :class:`CymaticRunner` and run it.

    Args:
        config: The visualizer configuration.

    Returns:
        Path to the intended render output under ``blender/render/``.
    """
    return CymaticRunner(config).run()
