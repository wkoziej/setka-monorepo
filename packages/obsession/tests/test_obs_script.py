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

    def test_on_event_recording_started(self, mock_obspython):
        """Test event handler for recording started."""
        with patch(
            "obsession.obs_integration.obs_script.prepare_metadata_collection"
        ) as mock_prepare:
            # Set script as enabled
            import obsession.obs_integration.obs_script as script_module

            script_module.script_enabled = True

            # Mock obs reference
            script_module.obs = mock_obspython

            # Call event handler
            on_event(mock_obspython.OBS_FRONTEND_EVENT_RECORDING_STARTED)

            # Verify prepare was called
            mock_prepare.assert_called_once()

    def test_on_event_recording_stopped(self, mock_obspython):
        """Test event handler for recording stopped."""
        with patch(
            "obsession.obs_integration.obs_script.collect_and_save_metadata"
        ) as mock_collect:
            # Set script as enabled
            import obsession.obs_integration.obs_script as script_module

            script_module.script_enabled = True

            # Mock obs reference
            script_module.obs = mock_obspython

            # Call event handler
            on_event(mock_obspython.OBS_FRONTEND_EVENT_RECORDING_STOPPED)

            # Verify collect was called
            mock_collect.assert_called_once()

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

    def test_save_metadata_to_file(self):
        """Test metadata saving to file."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set recording output path
            import obsession.obs_integration.obs_script as script_module

            # Save original path
            original_path = script_module.recording_output_path
            script_module.recording_output_path = temp_dir

            try:
                # Test metadata
                metadata = {
                    "canvas_size": [1920, 1080],
                    "fps": 30.0,
                    "sources": {
                        "Camera1": {"name": "Camera1", "position": {"x": 0, "y": 0}}
                    },
                    "scene_name": "Test Scene",
                }

                # Save metadata
                save_metadata_to_file(metadata)

                # Verify file was created
                files = os.listdir(temp_dir)
                assert len(files) == 1
                assert files[0].endswith("_metadata.json")

                # Verify file content
                with open(os.path.join(temp_dir, files[0]), "r") as f:
                    saved_metadata = json.load(f)

                assert saved_metadata["canvas_size"] == [1920, 1080]
                assert saved_metadata["fps"] == 30.0
                assert "Camera1" in saved_metadata["sources"]
            finally:
                # Restore original path
                script_module.recording_output_path = original_path

    def test_collect_and_save_metadata_no_scene_data(self):
        """Test collect metadata when no scene data is prepared."""
        # Clear scene data
        import obsession.obs_integration.obs_script as script_module

        script_module.current_scene_data = {}

        # Mock print to capture output
        with patch("builtins.print") as mock_print:
            collect_and_save_metadata()

            # Verify error message was printed
            mock_print.assert_called_with("[Canvas Recorder] No scene data prepared")

    def test_collect_and_save_metadata_with_sources(
        self, mock_obs_functions, mock_obs_scene, mock_obs_source, mock_obs_scene_item
    ):
        """Test collect metadata with scene sources."""
        # Setup scene data
        import obsession.obs_integration.obs_script as script_module

        script_module.current_scene_data = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "scene_name": "Test Scene",
        }

        # Ensure recording_output_path is set
        script_module.recording_output_path = "/tmp/test_output"

        # Mock obs reference
        script_module.obs = mock_obs_functions

        # Setup mock returns
        mock_obs_functions.obs_frontend_get_current_scene.return_value = mock_obs_scene
        mock_obs_functions.obs_scene_from_source.return_value = mock_obs_scene

        # Mock obs_scene_enum_items to return a list of scene items
        mock_obs_functions.obs_scene_enum_items.return_value = [mock_obs_scene_item]

        # Mock scene item functions
        mock_obs_functions.obs_sceneitem_get_source.return_value = mock_obs_source
        mock_obs_functions.obs_source_get_name.return_value = "Camera1"
        mock_obs_functions.obs_source_get_id.return_value = "camera_source"
        mock_obs_functions.obs_source_get_width.return_value = 1920
        mock_obs_functions.obs_source_get_height.return_value = 1080
        mock_obs_functions.obs_sceneitem_visible.return_value = True

        # Mock vec2 objects for position and scale
        mock_pos = Mock()
        mock_pos.x = 100
        mock_pos.y = 50
        mock_scale = Mock()
        mock_scale.x = 1.0
        mock_scale.y = 1.0
        mock_obs_functions.vec2.return_value = mock_pos

        # Mock sceneitem_list_release
        mock_obs_functions.sceneitem_list_release = Mock()

        # Mock save function
        with patch(
            "obsession.obs_integration.obs_script.save_metadata_to_file"
        ) as mock_save:
            # Mock determine_source_capabilities to return specific capabilities
            with patch(
                "obsession.obs_integration.obs_script.determine_source_capabilities"
            ) as mock_caps:
                mock_caps.return_value = {"has_audio": True, "has_video": True}

                collect_and_save_metadata()

                # Verify save was called
                mock_save.assert_called_once()

                # Get the metadata that was passed to save
                saved_metadata = mock_save.call_args[0][0]
                assert saved_metadata["canvas_size"] == [1920, 1080]
                assert saved_metadata["fps"] == 30.0
                assert "recording_stop_time" in saved_metadata
                assert "total_sources" in saved_metadata
                assert "Camera1" in saved_metadata["sources"]

                # Verify source has capabilities fields
                camera_source = saved_metadata["sources"]["Camera1"]
                assert "has_audio" in camera_source
                assert "has_video" in camera_source
                assert camera_source["has_audio"] is True
                assert camera_source["has_video"] is True

                # Verify sceneitem_list_release was called
                mock_obs_functions.sceneitem_list_release.assert_called_once()
