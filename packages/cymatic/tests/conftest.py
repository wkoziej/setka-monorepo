# ABOUTME: Pytest configuration and fixtures for cymatic tests
# ABOUTME: Provides mock bpy + mock subprocess; injects blender_script/ on sys.path

"""Pytest configuration for cymatic tests (pattern from cinemon)."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add blender_script to Python path so tests can import in-Blender modules.
blender_script_path = Path(__file__).parent.parent / "blender_script"
if str(blender_script_path) not in sys.path:
    sys.path.insert(0, str(blender_script_path))


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

        # Add to sys.modules
        monkeypatch.setitem(sys.modules, "bpy", mock)

        # Return mock for tests that need to configure it further
        return mock

    # If bpy already exists, return it
    return sys.modules["bpy"]


@pytest.fixture(autouse=True)
def mock_subprocess(monkeypatch):
    """Mock subprocess.run to prevent actual Blender execution in tests."""
    mock_result = Mock()
    mock_result.stdout = "Blender execution mocked"
    mock_result.stderr = ""
    mock_result.returncode = 0

    monkeypatch.setattr(subprocess, "run", Mock(return_value=mock_result))
    monkeypatch.setattr(subprocess, "Popen", Mock())
