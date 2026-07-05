"""
Tests for Unit 5.2 metadata robustness:
- calculate_crop_params must not raise KeyError when position is {} or absent;
- validate_metadata must check per-source position/bounds/dimensions shapes and
  reject zero/negative canvas dimensions.
"""

from obsession.core.extractor import calculate_crop_params
from obsession.core.metadata import validate_metadata


class TestCropParamsDefensivePosition:
    """position.get('x', 0) — no KeyError on empty/missing position."""

    def test_empty_position_dict_defaults_to_zero(self):
        source_info = {
            "position": {},  # present but empty — previously raised KeyError
            "dimensions": {"source_width": 800, "source_height": 600},
            "scale": {"x": 1.0, "y": 1.0},
        }
        params = calculate_crop_params(source_info, [1920, 1080])
        assert params["x"] == 0
        assert params["y"] == 0

    def test_missing_position_key_defaults_to_zero(self):
        source_info = {
            "dimensions": {"source_width": 800, "source_height": 600},
            "scale": {"x": 1.0, "y": 1.0},
        }
        params = calculate_crop_params(source_info, [1920, 1080])
        assert params["x"] == 0
        assert params["y"] == 0

    def test_partial_position_defaults_missing_axis(self):
        source_info = {
            "position": {"x": 100},  # y missing
            "dimensions": {"source_width": 800, "source_height": 600},
            "scale": {"x": 1.0, "y": 1.0},
        }
        params = calculate_crop_params(source_info, [1920, 1080])
        assert params["x"] == 100
        assert params["y"] == 0


class TestValidateMetadataSourceShapes:
    """validate_metadata checks per-source position/bounds/dimensions shapes."""

    def _base(self, sources):
        return {
            "canvas_size": [1920, 1080],
            "sources": sources,
            "fps": 30.0,
            "timestamp": 1.0,
        }

    def test_valid_source_with_full_shapes(self):
        metadata = self._base(
            {
                "Cam": {
                    "position": {"x": 0, "y": 0},
                    "bounds": {"x": 960.0, "y": 540.0, "type": 0},
                    "dimensions": {"source_width": 1920, "source_height": 1080},
                    "has_audio": False,
                    "has_video": True,
                }
            }
        )
        assert validate_metadata(metadata) is True

    def test_position_not_a_dict_rejected(self):
        metadata = self._base({"Cam": {"position": [0, 0]}})
        assert validate_metadata(metadata) is False

    def test_position_non_numeric_axis_rejected(self):
        metadata = self._base({"Cam": {"position": {"x": "left", "y": 0}}})
        assert validate_metadata(metadata) is False

    def test_bounds_not_a_dict_rejected(self):
        metadata = self._base({"Cam": {"bounds": "960x540"}})
        assert validate_metadata(metadata) is False

    def test_dimensions_not_a_dict_rejected(self):
        metadata = self._base({"Cam": {"dimensions": 1920}})
        assert validate_metadata(metadata) is False

    def test_source_not_a_dict_rejected(self):
        metadata = self._base({"Cam": "not-a-dict"})
        assert validate_metadata(metadata) is False

    def test_negative_canvas_rejected(self):
        metadata = self._base({})
        metadata["canvas_size"] = [-1920, 1080]
        assert validate_metadata(metadata) is False

    def test_source_with_only_capabilities_is_valid(self):
        # Audio-only source carries no position/bounds/dimensions — still valid.
        metadata = self._base(
            {"Mic": {"has_audio": True, "has_video": False}}
        )
        assert validate_metadata(metadata) is True
