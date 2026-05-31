# ABOUTME: Config dataclasses for the cymatic 3D audio visualizer (host-side)
# ABOUTME: VisualizerConfig + PresetParams with lossless JSON/dict serialization

"""Configuration dataclasses for cymatic.

The serialized ``VisualizerConfig`` is what the host-side runner writes to a
temporary file (via ``tempfile.NamedTemporaryFile``) and passes to the
in-Blender ``build_scene.py`` through ``--config``.

Notes:
- ``fps`` lives here (beatrix does NOT emit fps) — the build script sets
  ``scene.render.fps`` from this value, kept in sync with the harness.
- ``n_tolerance_frames`` deliberately does NOT live here — it is an internal
  constant of the sync-verification harness (Unit 10), not a config surface.
- Serialization must round-trip losslessly: ``resolution`` survives as a tuple
  even though JSON stores it as a list.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, Optional, Tuple

# Cross-platform default: resolve "blender" on PATH. May be None when Blender is
# not installed/on PATH — the runner raises a clear RuntimeError before spawning
# a subprocess in that case (pass --blender-executable or set it in config).
DEFAULT_BLENDER_EXECUTABLE: Optional[str] = shutil.which("blender")


@dataclass
class PresetParams:
    """Visual preset parameters (the "look", codified for reproducibility).

    The autoring loop (Unit 11 / Phase C) may only manipulate parameters
    expressible here — otherwise INV2 (deterministic reproduction from
    builder + params + analysis) does not hold.
    """

    palette: str = "default"
    primitive: str = "icosphere"
    accent_intensity: float = 0.5
    decay: float = 0.25
    tau: float = 0.15

    def __post_init__(self) -> None:
        if self.decay <= 0:
            raise ValueError(f"PresetParams.decay must be > 0, got {self.decay}")
        if self.tau <= 0:
            raise ValueError(f"PresetParams.tau must be > 0, got {self.tau}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PresetParams":
        # Rebuild from the dataclass fields so adding a new field does not
        # silently break round-trips (missing keys surface as a clear KeyError).
        return cls(**{f.name: data[f.name] for f in fields(cls)})

    @classmethod
    def from_json(cls, text: str) -> "PresetParams":
        return cls.from_dict(json.loads(text))


@dataclass
class VisualizerConfig:
    """Host-side configuration passed to the in-Blender build script.

    Args:
        analysis_file: Path to the beatrix ``*_analysis.json``.
        output_mp4: Destination render path (under ``blender/render/``).
        base_directory: Recording base directory (for audio resolution).
        fps: Render fps. From config, NOT from analysis. Default 30.
        resolution: ``(width, height)`` or ``None`` for the scene default.
        blender_executable: Path to the Blender binary (default: ``shutil.which
            ("blender")``, may be ``None`` if Blender is not on PATH — the
            runner then raises a clear error before spawning a subprocess).
        preset: Optional visual preset parameters.
        blender_timeout_sec: Hard timeout for the Blender render subprocess.
        ffmpeg_timeout_sec: Hard timeout for the ffmpeg mux subprocess.
    """

    analysis_file: str
    output_mp4: str
    base_directory: str
    fps: int = 30
    resolution: Optional[Tuple[int, int]] = None
    blender_executable: Optional[str] = DEFAULT_BLENDER_EXECUTABLE
    preset: Optional[PresetParams] = field(default=None)
    # Render/mux fields (Unit 9 follow-up — frames -> ffmpeg mux):
    audio_file: Optional[str] = None  # source wav/flac to mux into the mp4
    frame_start: int = 1
    frame_end: Optional[int] = None  # None -> derive from analysis duration
    frames_dir: Optional[str] = None  # when set, build_scene renders PNG sequence here
    # Subprocess timeouts (seconds); None disables the timeout.
    blender_timeout_sec: Optional[int] = 3600
    ffmpeg_timeout_sec: Optional[int] = 600

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict. ``resolution`` becomes a list in JSON."""
        return {
            "analysis_file": self.analysis_file,
            "output_mp4": self.output_mp4,
            "base_directory": self.base_directory,
            "fps": self.fps,
            "resolution": (
                list(self.resolution) if self.resolution is not None else None
            ),
            "blender_executable": self.blender_executable,
            "preset": self.preset.to_dict() if self.preset is not None else None,
            "audio_file": self.audio_file,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "frames_dir": self.frames_dir,
            "blender_timeout_sec": self.blender_timeout_sec,
            "ffmpeg_timeout_sec": self.ffmpeg_timeout_sec,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualizerConfig":
        resolution = data.get("resolution")
        if resolution is not None:
            resolution = tuple(resolution)

        preset = data.get("preset")
        if preset is not None:
            preset = PresetParams.from_dict(preset)

        return cls(
            analysis_file=data["analysis_file"],
            output_mp4=data["output_mp4"],
            base_directory=data["base_directory"],
            fps=data.get("fps", 30),
            resolution=resolution,
            blender_executable=data.get(
                "blender_executable", DEFAULT_BLENDER_EXECUTABLE
            ),
            preset=preset,
            audio_file=data.get("audio_file"),
            frame_start=data.get("frame_start", 1),
            frame_end=data.get("frame_end"),
            frames_dir=data.get("frames_dir"),
            blender_timeout_sec=data.get("blender_timeout_sec", 3600),
            ffmpeg_timeout_sec=data.get("ffmpeg_timeout_sec", 600),
        )

    @classmethod
    def from_json(cls, text: str) -> "VisualizerConfig":
        return cls.from_dict(json.loads(text))
