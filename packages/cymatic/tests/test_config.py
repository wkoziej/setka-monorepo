# ABOUTME: Tests for cymatic config dataclasses (VisualizerConfig, PresetParams)
# ABOUTME: TDD — round-trip serialization, defaults, and import smoke

"""Tests for cymatic.config dataclasses."""

import json

import pytest


def test_import_cymatic_smoke():
    """Smoke test: the package imports cleanly."""
    import cymatic  # noqa: F401


def test_import_config_symbols():
    """VisualizerConfig and PresetParams are importable from cymatic.config."""
    from cymatic.config import PresetParams, VisualizerConfig  # noqa: F401


class TestVisualizerConfig:
    def _make(self):
        from cymatic.config import VisualizerConfig

        return VisualizerConfig(
            analysis_file="/rec/analysis/song_analysis.json",
            output_mp4="/rec/blender/render/song.mp4",
            base_directory="/rec",
            fps=60,
            resolution=(1920, 1080),
            blender_executable="/usr/bin/blender",
        )

    def test_to_dict_from_dict_roundtrip_lossless(self):
        from cymatic.config import VisualizerConfig

        cfg = self._make()
        restored = VisualizerConfig.from_dict(cfg.to_dict())
        assert restored == cfg

    def test_to_json_from_json_roundtrip_lossless(self):
        from cymatic.config import VisualizerConfig

        cfg = self._make()
        restored = VisualizerConfig.from_json(cfg.to_json())
        assert restored == cfg

    def test_json_is_valid_json_string(self):
        cfg = self._make()
        # Must parse as JSON and contain the resolution as a 2-element list
        data = json.loads(cfg.to_json())
        assert data["resolution"] == [1920, 1080]
        assert data["fps"] == 60

    def test_resolution_tuple_survives_roundtrip(self):
        """resolution must come back as a tuple, not a list."""
        from cymatic.config import VisualizerConfig

        cfg = self._make()
        restored = VisualizerConfig.from_json(cfg.to_json())
        assert restored.resolution == (1920, 1080)
        assert isinstance(restored.resolution, tuple)

    def test_defaults_fps_and_resolution_and_executable(self):
        """fps defaults to 30, resolution defaults to None, executable to macOS path."""
        from cymatic.config import VisualizerConfig

        cfg = VisualizerConfig(
            analysis_file="/a.json",
            output_mp4="/o.mp4",
            base_directory="/b",
        )
        assert cfg.fps == 30
        assert cfg.resolution is None
        assert cfg.blender_executable == (
            "/Applications/Blender.app/Contents/MacOS/Blender"
        )

    def test_resolution_none_roundtrip(self):
        """resolution=None survives serialization round-trip."""
        from cymatic.config import VisualizerConfig

        cfg = VisualizerConfig(
            analysis_file="/a.json",
            output_mp4="/o.mp4",
            base_directory="/b",
        )
        restored = VisualizerConfig.from_json(cfg.to_json())
        assert restored.resolution is None
        assert restored == cfg

    def test_no_n_tolerance_frames_field(self):
        """n_tolerance_frames belongs to the sync harness (Unit 10), not config."""
        cfg = self._make()
        assert not hasattr(cfg, "n_tolerance_frames")


class TestPresetParams:
    def _make(self):
        from cymatic.config import PresetParams

        return PresetParams(
            palette="neon",
            primitive="icosphere",
            accent_intensity=0.8,
            decay=0.25,
            tau=0.15,
        )

    def test_to_dict_from_dict_roundtrip_lossless(self):
        from cymatic.config import PresetParams

        params = self._make()
        restored = PresetParams.from_dict(params.to_dict())
        assert restored == params

    def test_to_json_from_json_roundtrip_lossless(self):
        from cymatic.config import PresetParams

        params = self._make()
        restored = PresetParams.from_json(params.to_json())
        assert restored == params


def test_visualizer_config_can_embed_preset_params():
    """A VisualizerConfig carrying a PresetParams round-trips losslessly."""
    from cymatic.config import PresetParams, VisualizerConfig

    cfg = VisualizerConfig(
        analysis_file="/a.json",
        output_mp4="/o.mp4",
        base_directory="/b",
        preset=PresetParams(
            palette="vintage",
            primitive="cube",
            accent_intensity=0.5,
            decay=0.3,
            tau=0.2,
        ),
    )
    restored = VisualizerConfig.from_json(cfg.to_json())
    assert restored == cfg
    assert restored.preset.palette == "vintage"
