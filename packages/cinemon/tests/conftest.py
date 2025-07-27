# ABOUTME: Pytest configuration and fixtures for cinemon tests
# ABOUTME: Provides mock for bpy module when running tests outside Blender

"""Pytest configuration for cinemon tests."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add blender_addon to Python path so tests can import it
blender_addon_path = Path(__file__).parent.parent / "blender_addon"
if str(blender_addon_path) not in sys.path:
    sys.path.insert(0, str(blender_addon_path))


@pytest.fixture(autouse=True)
def mock_bpy(monkeypatch):
    """Mock bpy module for tests running outside Blender."""
    if "bpy" not in sys.modules:
        mock = Mock()

        # Mock scene render settings
        mock.context.scene.render.resolution_x = 1920
        mock.context.scene.render.resolution_y = 1080
        mock.context.scene.render.fps = 30
        mock.context.scene.frame_start = 1
        mock.context.scene.frame_end = 900  # 30 seconds at 30fps

        # Mock sequencer
        mock.context.scene.sequence_editor = Mock()
        mock.context.scene.sequence_editor.sequences = []

        # Add to sys.modules
        monkeypatch.setitem(sys.modules, "bpy", mock)

        # Return mock for tests that need to configure it further
        return mock

    # If bpy already exists, return it
    return sys.modules["bpy"]


@pytest.fixture
def sample_recording_structure(tmp_path):
    """Create a sample recording structure for testing."""
    # Create recording directory structure
    recording_dir = tmp_path / "sample_recording"
    recording_dir.mkdir()

    # Create metadata.json
    metadata_file = recording_dir / "metadata.json"
    metadata_file.write_text('{"fps": 30, "resolution": "1920x1080"}')

    # Create main video file in recording directory (for RecordingStructureManager)
    (recording_dir / "recording.mkv").write_text("fake main recording data")

    # Create extracted directory with sample files
    extracted_dir = recording_dir / "extracted"
    extracted_dir.mkdir()

    # Create sample video files
    (extracted_dir / "camera1.mp4").write_text("fake video data")
    (extracted_dir / "screen.mkv").write_text("fake video data")
    (extracted_dir / "main_audio.m4a").write_text("fake audio data")

    # Create analysis directory
    analysis_dir = recording_dir / "analysis"
    analysis_dir.mkdir()
    (analysis_dir / "main_audio_analysis.json").write_text(
        '{"beats": [], "energy_peaks": []}'
    )

    # Create blender directory
    blender_dir = recording_dir / "blender"
    blender_dir.mkdir()
    (blender_dir / "render").mkdir()

    return recording_dir
