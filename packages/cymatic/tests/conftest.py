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


# --- matplotlib font-scan compatibility shim --------------------------------
# On the GitHub Linux runner, matplotlib 3.10.9 builds its FontManager at import
# time by calling ``subprocess.check_output(['fc-list', '--help'])`` and testing
# ``b'--format' not in <output>``. On that runner the call comes back as ``str``
# instead of the expected ``bytes``, raising
# ``TypeError: 'in <string>' requires string as left operand, not bytes``.
# (macOS goes through a different font path, so this never fires locally.)
# Force check_output back to bytes when the caller did not request text mode, so
# the scan works. Installed before any matplotlib import (tests import it lazily
# inside render_heatmap); only affects this test process.
_orig_check_output = subprocess.check_output


def _check_output_bytes(*args, **kwargs):
    result = _orig_check_output(*args, **kwargs)
    text_mode = (
        kwargs.get("text")
        or kwargs.get("encoding")
        or kwargs.get("universal_newlines")
    )
    if isinstance(result, str) and not text_mode:
        return result.encode("utf-8", "surrogateescape")
    return result


subprocess.check_output = _check_output_bytes
# ----------------------------------------------------------------------------


# Markers are registered in pyproject.toml. Tests are unit tests by default, so
# tag any test that carries no explicit marker as `unit` — this keeps
# ``pytest -m unit`` meaningful (non-empty) without retagging every module.
_EXPLICIT_MARKERS = {"integration", "slow", "unit"}


def pytest_collection_modifyitems(config, items):
    for item in items:
        if not any(m.name in _EXPLICIT_MARKERS for m in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


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
