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
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

DEFAULT_BLENDER_EXECUTABLE = "/Applications/Blender.app/Contents/MacOS/Blender"


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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PresetParams":
        return cls(
            palette=data["palette"],
            primitive=data["primitive"],
            accent_intensity=data["accent_intensity"],
            decay=data["decay"],
            tau=data["tau"],
        )

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
        blender_executable: Path to the Blender binary (default: macOS).
        preset: Optional visual preset parameters.
    """

    analysis_file: str
    output_mp4: str
    base_directory: str
    fps: int = 30
    resolution: Optional[Tuple[int, int]] = None
    blender_executable: str = DEFAULT_BLENDER_EXECUTABLE
    preset: Optional[PresetParams] = field(default=None)

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
        )

    @classmethod
    def from_json(cls, text: str) -> "VisualizerConfig":
        return cls.from_dict(json.loads(text))
