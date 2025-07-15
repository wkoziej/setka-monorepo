# ABOUTME: Pytest configuration and fixtures for cinemon tests
# ABOUTME: Provides mock for bpy module when running tests outside Blender

"""Pytest configuration for cinemon tests."""

import sys
from unittest.mock import Mock
import pytest


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