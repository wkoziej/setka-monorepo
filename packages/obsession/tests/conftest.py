"""
Shared fixtures for tests.
"""

import pytest
import sys
from unittest.mock import Mock


# OBS Mock Classes
class MockVec2:
    """Mock for OBS vec2 class."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0


class MockVideoInfo:
    """Mock for OBS video info class."""

    def __init__(self):
        self.base_width = 1920
        self.base_height = 1080
        self.output_width = 1920
        self.output_height = 1080
        self.fps_num = 30
        self.fps_den = 1
        self.output_format = 0
        self.adapter = 0
        self.gpu_conversion = True


class MockTransformInfo:
    """Mock for OBS transform info class."""

    def __init__(self):
        self.rot = 0.0
        self.alignment = 0
        self.bounds_type = 0
        self.bounds_alignment = 0


@pytest.fixture(scope="session", autouse=True)
def mock_obspython():
    """
    Session-wide fixture that mocks obspython module.
    This runs automatically for all tests.
    """
    if "obspython" not in sys.modules:
        mock_obs = Mock()

        # Constants
        mock_obs.OBS_FRONTEND_EVENT_RECORDING_STARTED = 1
        mock_obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED = 2
        mock_obs.OBS_PATH_DIRECTORY = "directory"
        mock_obs.OBS_TEXT_INFO = "info"

        # Classes
        mock_obs.vec2 = MockVec2
        mock_obs.obs_video_info = MockVideoInfo

        # Add to sys.modules
        sys.modules["obspython"] = mock_obs

        # Also ensure the import in the actual modules works
        import obsession.obs_integration.obs_script as obs_script_module

        obs_script_module.obs = mock_obs

    return sys.modules["obspython"]


@pytest.fixture
def mock_obs_scene():
    """Fixture for mock OBS scene."""
    scene = Mock()
    scene.name = "Test Scene"
    return scene


@pytest.fixture
def mock_obs_source():
    """Fixture for mock OBS source."""
    source = Mock()
    source.name = "Camera1"
    source.id = "camera_source"
    source.width = 1920
    source.height = 1080
    source.visible = True
    return source


@pytest.fixture
def mock_obs_scene_item():
    """Fixture for mock OBS scene item."""
    item = Mock()
    item.visible = True
    item.locked = False
    return item


@pytest.fixture
def mock_obs_functions(mock_obspython):
    """Fixture that provides commonly used OBS function mocks."""
    obs = mock_obspython

    # Reset all mocks
    obs.reset_mock()

    # Setup default return values
    obs.obs_frontend_get_current_scene = Mock(return_value=Mock())
    obs.obs_scene_from_source = Mock(return_value=Mock())
    obs.obs_source_get_name = Mock(return_value="Test Scene")
    obs.obs_source_release = Mock()
    obs.obs_get_video_info = Mock()
    obs.obs_frontend_add_event_callback = Mock()
    obs.obs_frontend_remove_event_callback = Mock()
    obs.obs_data_get_bool = Mock(return_value=True)
    obs.obs_data_get_string = Mock(return_value="/tmp/test")
    obs.obs_data_set_default_bool = Mock()
    obs.obs_data_set_default_string = Mock()
    obs.obs_properties_create = Mock()
    obs.obs_properties_add_bool = Mock()
    obs.obs_properties_add_path = Mock()
    obs.obs_properties_add_text = Mock()
    obs.obs_scene_enum_items = Mock()
    obs.obs_frontend_enum_scenes = Mock()
    obs.sceneitem_list_release = Mock()

    # Source-related functions
    obs.obs_sceneitem_get_source = Mock(return_value=Mock())
    obs.obs_sceneitem_visible = Mock(return_value=True)
    obs.obs_sceneitem_locked = Mock(return_value=False)
    obs.obs_source_get_id = Mock(return_value="camera_source")
    obs.obs_source_get_type = Mock(return_value=1)
    obs.obs_source_get_width = Mock(return_value=1920)
    obs.obs_source_get_height = Mock(return_value=1080)
    obs.obs_sceneitem_get_pos = Mock()
    obs.obs_sceneitem_get_scale = Mock()
    obs.obs_sceneitem_get_bounds = Mock()
    obs.obs_sceneitem_get_info = Mock(return_value=MockTransformInfo())

    # Source capabilities - return flags for audio+video by default
    obs.obs_source_get_output_flags = Mock(
        return_value=0x003
    )  # Audio (0x002) + Video (0x001)

    return obs


# Test Data Fixtures (existing ones)
@pytest.fixture
def test_video_file():
    """Fixture for test video file path."""
    return "tests/fixtures/test_recording.mp4"


@pytest.fixture
def basic_source_info():
    """Fixture for basic source information."""
    return {
        "position": {"x": 0, "y": 0},
        "scale": {"x": 1.0, "y": 1.0},
        "dimensions": {
            "source_width": 1920,
            "source_height": 1080,
            "final_width": 1920,
            "final_height": 1080,
        },
    }


@pytest.fixture
def positioned_source_info():
    """Fixture for source with non-zero position."""
    return {
        "position": {"x": 1920, "y": 0},
        "scale": {"x": 1.0, "y": 1.0},
        "dimensions": {
            "source_width": 1920,
            "source_height": 1080,
            "final_width": 1920,
            "final_height": 1080,
        },
    }


@pytest.fixture
def scaled_source_info():
    """Fixture for source with scaling."""
    return {
        "position": {"x": 0, "y": 0},
        "scale": {"x": 0.5, "y": 0.5},
        "dimensions": {
            "source_width": 1920,
            "source_height": 1080,
            "final_width": 960,
            "final_height": 540,
        },
    }


@pytest.fixture
def complex_source_info():
    """Fixture for source with position and scale."""
    return {
        "position": {"x": 100, "y": 50},
        "scale": {"x": 0.8, "y": 0.6},
        "dimensions": {
            "source_width": 1920,
            "source_height": 1080,
            "final_width": 1536,
            "final_height": 648,
        },
    }


@pytest.fixture
def single_source_metadata():
    """Fixture for metadata with single source."""
    return {
        "canvas_size": [1920, 1080],
        "sources": {
            "Camera1": {
                "position": {"x": 0, "y": 0},
                "scale": {"x": 1.0, "y": 1.0},
                "has_audio": True,
                "has_video": True,
            }
        },
    }


@pytest.fixture
def dual_source_metadata():
    """Fixture for metadata with two sources."""
    return {
        "canvas_size": [3840, 1080],
        "sources": {
            "Camera1": {
                "position": {"x": 0, "y": 0},
                "scale": {"x": 1.0, "y": 1.0},
                "has_audio": True,
                "has_video": True,
            },
            "Camera2": {
                "position": {"x": 1920, "y": 0},
                "scale": {"x": 1.0, "y": 1.0},
                "has_audio": True,
                "has_video": True,
            },
        },
    }


@pytest.fixture
def empty_sources_metadata():
    """Fixture for metadata with empty sources."""
    return {"canvas_size": [1920, 1080], "sources": {}}


@pytest.fixture
def invalid_metadata():
    """Fixture for invalid metadata (missing sources field)."""
    return {
        "canvas_size": [1920, 1080],
        # Missing sources field
    }


@pytest.fixture
def standard_canvas_size():
    """Fixture for standard canvas size."""
    return [1920, 1080]


@pytest.fixture
def wide_canvas_size():
    """Fixture for wide canvas size."""
    return [3840, 1080]


# Blender Test Fixtures
@pytest.fixture
def sample_recording_structure(tmp_path):
    """
    Fixture for sample recording directory structure.
    Creates a complete recording structure with files for testing.
    """
    # Create recording directory
    recording_dir = tmp_path / "sample_recording"
    recording_dir.mkdir()

    # Create metadata.json
    metadata_file = recording_dir / "metadata.json"
    metadata_content = """
    {
        "canvas_size": {"width": 1920, "height": 1080},
        "fps": 30,
        "recording_started": "2025-01-05T14:30:22",
        "recording_stopped": "2025-01-05T14:35:45",
        "sources": [
            {
                "name": "Camera1",
                "id": "camera_source",
                "type": "dshow_input",
                "visible": true,
                "position": {"x": 0, "y": 0},
                "scale": {"x": 1.0, "y": 1.0},
                "dimensions": {
                    "source_width": 1920,
                    "source_height": 1080,
                    "final_width": 1920,
                    "final_height": 1080
                }
            }
        ]
    }
    """
    metadata_file.write_text(metadata_content)

    # Create main recording file
    main_recording = recording_dir / "sample_recording.mkv"
    main_recording.touch()

    # Create extracted directory
    extracted_dir = recording_dir / "extracted"
    extracted_dir.mkdir()

    # Create extracted files
    (extracted_dir / "Camera1.mp4").touch()
    (extracted_dir / "main_audio.m4a").touch()

    return recording_dir


@pytest.fixture
def sample_recording_multiple_audio(tmp_path):
    """
    Fixture for sample recording with multiple audio files.
    Used for testing multiple audio file scenarios.
    """
    # Create recording directory
    recording_dir = tmp_path / "sample_recording_multi"
    recording_dir.mkdir()

    # Create metadata.json
    metadata_file = recording_dir / "metadata.json"
    metadata_content = '{"canvas_size": {"width": 1920, "height": 1080}, "fps": 30}'
    metadata_file.write_text(metadata_content)

    # Create main recording file
    main_recording = recording_dir / "sample_recording_multi.mkv"
    main_recording.touch()

    # Create extracted directory
    extracted_dir = recording_dir / "extracted"
    extracted_dir.mkdir()

    # Create extracted files with multiple audio
    (extracted_dir / "Camera1.mp4").touch()
    (extracted_dir / "Camera2.mp4").touch()
    (extracted_dir / "main_audio.m4a").touch()
    (extracted_dir / "background_audio.mp3").touch()

    return recording_dir


@pytest.fixture
def sample_recording_no_audio(tmp_path):
    """
    Fixture for sample recording without audio files.
    Used for testing no audio file scenarios.
    """
    # Create recording directory
    recording_dir = tmp_path / "sample_recording_no_audio"
    recording_dir.mkdir()

    # Create metadata.json
    metadata_file = recording_dir / "metadata.json"
    metadata_content = '{"canvas_size": {"width": 1920, "height": 1080}, "fps": 30}'
    metadata_file.write_text(metadata_content)

    # Create main recording file
    main_recording = recording_dir / "sample_recording_no_audio.mkv"
    main_recording.touch()

    # Create extracted directory
    extracted_dir = recording_dir / "extracted"
    extracted_dir.mkdir()

    # Create only video files
    (extracted_dir / "Camera1.mp4").touch()
    (extracted_dir / "Screen.mp4").touch()

    return recording_dir
