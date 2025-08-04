"""
Test module for OBS script functionality.
Using shared OBS fixtures from conftest.py to avoid duplication.
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch

# Import our module - obspython mock is handled by conftest.py
from obsession.obs_integration.obs_script import (
    script_description,
    script_load,
    script_unload,
    on_event,
    prepare_metadata_collection,
    collect_and_save_metadata,
    save_metadata_to_file,
)


class TestOBSScript:
    """Test cases for OBS script functionality."""

    def setup_method(self):
        """Setup method for each test."""
        pass

    def test_script_description(self):
        """Test script description returns proper HTML."""
        description = script_description()
        assert "Canvas Recording Metadata Collector" in description
        assert "<h2>" in description
        assert "<p>" in description

    def test_script_load_with_mock_obs(self, mock_obs_functions):
        """Test script load functionality."""
        mock_settings = Mock()

        # Call script_load
        script_load(mock_settings)

        # Verify callback was registered
        mock_obs_functions.obs_frontend_add_event_callback.assert_called_once()

    def test_script_unload_with_mock_obs(self, mock_obs_functions):
        """Test script unload functionality."""
        # Call script_unload
        script_unload()

        # Verify callback was removed
        mock_obs_functions.obs_frontend_remove_event_callback.assert_called_once()


    def test_on_event_script_disabled(self, mock_obspython):
        """Test event handler when script is disabled."""
        with patch(
            "obsession.obs_integration.obs_script.prepare_metadata_collection"
        ) as mock_prepare:
            # Set script as disabled
            import obsession.obs_integration.obs_script as script_module

            script_module.script_enabled = False

            # Mock obs reference
            script_module.obs = mock_obspython

            # Call event handler
            on_event(mock_obspython.OBS_FRONTEND_EVENT_RECORDING_STARTED)

            # Verify prepare was NOT called
            mock_prepare.assert_not_called()

    def test_prepare_metadata_collection(self, mock_obs_functions, mock_obs_scene):
        """Test metadata preparation."""
        # Setup specific mock returns
        mock_obs_functions.obs_frontend_get_current_scene.return_value = mock_obs_scene
        mock_obs_functions.obs_source_get_name.return_value = "Test Scene"

        # Call prepare_metadata_collection
        prepare_metadata_collection()

        # Verify OBS functions were called
        mock_obs_functions.obs_frontend_get_current_scene.assert_called_once()
        mock_obs_functions.obs_source_get_name.assert_called_once_with(mock_obs_scene)
        mock_obs_functions.obs_source_release.assert_called_once_with(mock_obs_scene)
        mock_obs_functions.obs_get_video_info.assert_called_once()
