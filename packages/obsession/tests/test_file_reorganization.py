"""
Test module for file reorganization functionality.
Tests for new functions that reorganize files after recording.
"""

import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch


# Import functions to test - will be implemented
from src.obs_integration.obs_script import (
    get_recording_output_path,
    reorganize_files_after_recording,
    save_metadata_to_file,
)


class TestFileReorganization:
    """Test cases for file reorganization functionality."""

    def test_get_recording_output_path_with_obs(self, mock_obs_functions):
        """Test getting recording output path when OBS is available."""
        # Setup mock return value
        mock_obs_functions.obs_frontend_get_current_record_output_path.return_value = (
            "/path/to/recording.mkv"
        )

        # Call function
        result = get_recording_output_path()

        # Verify result
        assert result == "/path/to/recording.mkv"
        mock_obs_functions.obs_frontend_get_current_record_output_path.assert_called_once()
        # bfree() nie jest już wywoływane - obs_frontend_get_current_record_output_path() zwraca string

    def test_get_recording_output_path_no_obs(self):
        """Test getting recording output path when OBS is not available."""
        # Mock obs as None
        import src.obs_integration.obs_script as script_module

        original_obs = script_module.obs
        script_module.obs = None

        try:
            # Call function
            result = get_recording_output_path()

            # Verify result
            assert result is None
        finally:
            # Restore original obs
            script_module.obs = original_obs

    def test_get_recording_output_path_no_recording(self, mock_obs_functions):
        """Test getting recording output path when no recording is active."""
        # Setup mock to return None
        mock_obs_functions.obs_frontend_get_current_record_output_path.return_value = (
            None
        )

        # Call function
        result = get_recording_output_path()

        # Verify result
        assert result is None
        mock_obs_functions.obs_frontend_get_current_record_output_path.assert_called_once()

    def test_reorganize_files_after_recording_success(self):
        """Test successful file reorganization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            recording_path = os.path.join(temp_dir, "recording_2025-01-06_15-30-00.mkv")
            metadata_path = os.path.join(temp_dir, "metadata.json")

            # Create actual files
            Path(recording_path).touch()
            with open(metadata_path, "w") as f:
                json.dump({"test": "data"}, f)

            # Call function
            result = reorganize_files_after_recording(recording_path, metadata_path)

            # Verify structure was created
            expected_dir = os.path.join(temp_dir, "recording_2025-01-06_15-30-00")
            assert os.path.exists(expected_dir)
            assert os.path.exists(
                os.path.join(expected_dir, "recording_2025-01-06_15-30-00.mkv")
            )
            assert os.path.exists(os.path.join(expected_dir, "metadata.json"))
            assert os.path.exists(os.path.join(expected_dir, "extracted"))

            # Verify original files were moved
            assert not os.path.exists(recording_path)
            assert not os.path.exists(metadata_path)

            # Verify return value
            assert result == expected_dir

    def test_reorganize_files_after_recording_nonexistent_recording(self):
        """Test reorganization when recording file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recording_path = os.path.join(temp_dir, "nonexistent.mkv")
            metadata_path = os.path.join(temp_dir, "metadata.json")

            # Create only metadata file
            with open(metadata_path, "w") as f:
                json.dump({"test": "data"}, f)

            # Call function
            result = reorganize_files_after_recording(recording_path, metadata_path)

            # Verify it returns None on failure
            assert result is None

    def test_reorganize_files_after_recording_nonexistent_metadata(self):
        """Test reorganization when metadata file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recording_path = os.path.join(temp_dir, "recording.mkv")
            metadata_path = os.path.join(temp_dir, "nonexistent.json")

            # Create only recording file
            Path(recording_path).touch()

            # Call function
            result = reorganize_files_after_recording(recording_path, metadata_path)

            # Verify it returns None on failure
            assert result is None

    def test_reorganize_files_after_recording_existing_directory(self):
        """Test reorganization when target directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recording_path = os.path.join(temp_dir, "recording_2025-01-06_15-30-00.mkv")
            metadata_path = os.path.join(temp_dir, "metadata.json")

            # Create test files
            Path(recording_path).touch()
            with open(metadata_path, "w") as f:
                json.dump({"test": "data"}, f)

            # Create existing directory
            existing_dir = os.path.join(temp_dir, "recording_2025-01-06_15-30-00")
            os.makedirs(existing_dir)

            # Call function
            result = reorganize_files_after_recording(recording_path, metadata_path)

            # Should handle existing directory gracefully
            assert result == existing_dir
            assert os.path.exists(
                os.path.join(existing_dir, "recording_2025-01-06_15-30-00.mkv")
            )
            assert os.path.exists(os.path.join(existing_dir, "metadata.json"))

    def test_reorganize_files_different_extensions(self):
        """Test reorganization with different file extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with .mp4 extension
            recording_path = os.path.join(temp_dir, "recording_2025-01-06_15-30-00.mp4")
            metadata_path = os.path.join(temp_dir, "metadata.json")

            Path(recording_path).touch()
            with open(metadata_path, "w") as f:
                json.dump({"test": "data"}, f)

            result = reorganize_files_after_recording(recording_path, metadata_path)

            # Directory name should be based on filename without extension
            expected_dir = os.path.join(temp_dir, "recording_2025-01-06_15-30-00")
            assert result == expected_dir
            assert os.path.exists(
                os.path.join(expected_dir, "recording_2025-01-06_15-30-00.mp4")
            )

    def test_reorganize_files_permission_error(self):
        """Test reorganization when there are permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            recording_path = os.path.join(temp_dir, "recording.mkv")
            metadata_path = os.path.join(temp_dir, "metadata.json")

            Path(recording_path).touch()
            with open(metadata_path, "w") as f:
                json.dump({"test": "data"}, f)

            # Mock shutil.move to raise PermissionError
            with patch("shutil.move", side_effect=PermissionError("Permission denied")):
                result = reorganize_files_after_recording(recording_path, metadata_path)

                # Should return None on permission error
                assert result is None

    def test_save_metadata_to_file_fallback_behavior(self):
        """Test saving metadata fallback behavior (always uses timestamp after refactoring)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set the recording output path to the temp directory
            import src.obs_integration.obs_script as script_module

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

                # After refactoring, save_metadata_to_file always uses timestamp for fallback saves
                # Find the created file with timestamp
                metadata_files = [
                    f for f in os.listdir(temp_dir) if f.endswith("_metadata.json")
                ]
                assert len(metadata_files) == 1

                metadata_file = os.path.join(temp_dir, metadata_files[0])
                assert os.path.exists(metadata_file)

                # Verify content
                with open(metadata_file, "r") as f:
                    saved_metadata = json.load(f)

                assert saved_metadata["canvas_size"] == [1920, 1080]
                assert saved_metadata["fps"] == 30.0
                assert "Camera1" in saved_metadata["sources"]

            finally:
                # Restore original path
                script_module.recording_output_path = original_path

    def test_integration_full_reorganization_flow(self, mock_obs_functions):
        """Test full integration of reorganization functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup mock OBS to return recording path
            recording_path = os.path.join(temp_dir, "recording_2025-01-06_15-30-00.mkv")
            mock_obs_functions.obs_frontend_get_current_record_output_path.return_value = recording_path
            mock_obs_functions.bfree = Mock()

            # Create recording file
            Path(recording_path).touch()

            # Step 1: Get recording path
            path = get_recording_output_path()
            assert path == recording_path

            # Step 2: Create metadata in temp location
            temp_metadata_path = os.path.join(temp_dir, "temp_metadata.json")
            metadata = {
                "canvas_size": [1920, 1080],
                "fps": 30.0,
                "sources": {"Camera1": {"name": "Camera1"}},
                "scene_name": "Test Scene",
            }
            with open(temp_metadata_path, "w") as f:
                json.dump(metadata, f)

            # Step 3: Reorganize files
            result_dir = reorganize_files_after_recording(
                recording_path, temp_metadata_path
            )

            # Verify complete structure
            assert result_dir is not None
            assert os.path.exists(
                os.path.join(result_dir, "recording_2025-01-06_15-30-00.mkv")
            )
            assert os.path.exists(os.path.join(result_dir, "metadata.json"))
            assert os.path.exists(os.path.join(result_dir, "extracted"))

            # Verify original files were moved
            assert not os.path.exists(recording_path)
            assert not os.path.exists(temp_metadata_path)

    def test_collect_and_save_metadata_with_reorganization(
        self, mock_obs_functions, mock_obs_scene, mock_obs_source, mock_obs_scene_item
    ):
        """Test collect_and_save_metadata with file reorganization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup scene data
            import src.obs_integration.obs_script as script_module

            script_module.current_scene_data = {
                "canvas_size": [1920, 1080],
                "fps": 30.0,
                "scene_name": "Test Scene",
            }

            # Setup recording path - create a fresh file in temp directory
            recording_path = os.path.join(temp_dir, "test_recording.mkv")
            Path(recording_path).touch()

            # Simulate recent file creation by setting modification time to now
            import time

            current_time = time.time()
            os.utime(recording_path, (current_time, current_time))

            # Setup mock returns for OBS functions
            mock_obs_functions.obs_frontend_get_current_scene.return_value = (
                mock_obs_scene
            )
            mock_obs_functions.obs_scene_from_source.return_value = mock_obs_scene
            mock_obs_functions.obs_scene_enum_items.return_value = [mock_obs_scene_item]
            mock_obs_functions.obs_sceneitem_get_source.return_value = mock_obs_source
            mock_obs_functions.obs_source_get_name.return_value = "Camera1"
            mock_obs_functions.obs_source_get_id.return_value = "camera_source"
            mock_obs_functions.obs_source_get_width.return_value = 1920
            mock_obs_functions.obs_source_get_height.return_value = 1080
            mock_obs_functions.obs_sceneitem_visible.return_value = True
            mock_obs_functions.obs_frontend_get_current_record_output_path.return_value = temp_dir  # Return directory, not file

            # Mock vec2 objects
            mock_pos = Mock()
            mock_pos.x = 100
            mock_pos.y = 50
            mock_scale = Mock()
            mock_scale.x = 1.0
            mock_scale.y = 1.0
            mock_bounds = Mock()
            mock_bounds.x = 0
            mock_bounds.y = 0
            mock_obs_functions.vec2.return_value = mock_pos
            mock_obs_functions.obs_sceneitem_get_bounds_type.return_value = 0

            # Set recording output path to temp directory
            original_recording_path = script_module.recording_output_path
            script_module.recording_output_path = (
                temp_dir  # Set captured output directory
            )

            try:
                # Call collect_and_save_metadata
                from src.obs_integration.obs_script import collect_and_save_metadata

                collect_and_save_metadata()

                # Verify reorganized structure was created
                expected_dir = os.path.join(temp_dir, "test_recording")
                assert os.path.exists(expected_dir)
                assert os.path.exists(os.path.join(expected_dir, "test_recording.mkv"))
                assert os.path.exists(os.path.join(expected_dir, "metadata.json"))
                assert os.path.exists(os.path.join(expected_dir, "extracted"))

                # Verify original recording was moved
                assert not os.path.exists(recording_path)

                # Verify metadata content
                with open(os.path.join(expected_dir, "metadata.json"), "r") as f:
                    metadata = json.load(f)
                assert metadata["scene_name"] == "Test Scene"
                assert "Camera1" in metadata["sources"]

            finally:
                # Restore original paths
                script_module.recording_output_path = original_recording_path

    def test_collect_and_save_metadata_no_recording_path(
        self, mock_obs_functions, mock_obs_scene, mock_obs_source, mock_obs_scene_item
    ):
        """Test collect_and_save_metadata when recording path cannot be obtained."""
        # Setup scene data
        import src.obs_integration.obs_script as script_module

        script_module.current_scene_data = {
            "canvas_size": [1920, 1080],
            "fps": 30.0,
            "scene_name": "Test Scene",
        }

        # Setup mock returns for OBS functions
        mock_obs_functions.obs_frontend_get_current_scene.return_value = mock_obs_scene
        mock_obs_functions.obs_scene_from_source.return_value = mock_obs_scene
        mock_obs_functions.obs_scene_enum_items.return_value = [mock_obs_scene_item]
        mock_obs_functions.obs_sceneitem_get_source.return_value = mock_obs_source
        mock_obs_functions.obs_source_get_name.return_value = "Camera1"
        mock_obs_functions.obs_source_get_id.return_value = "camera_source"
        mock_obs_functions.obs_source_get_width.return_value = 1920
        mock_obs_functions.obs_source_get_height.return_value = 1080
        mock_obs_functions.obs_sceneitem_visible.return_value = True

        # Mock to return None for recording path
        mock_obs_functions.obs_frontend_get_current_record_output_path.return_value = (
            None
        )

        # Mock vec2 objects
        mock_pos = Mock()
        mock_pos.x = 100
        mock_pos.y = 50
        mock_scale = Mock()
        mock_scale.x = 1.0
        mock_scale.y = 1.0
        mock_bounds = Mock()
        mock_bounds.x = 0
        mock_bounds.y = 0
        mock_obs_functions.vec2.return_value = mock_pos
        mock_obs_functions.obs_sceneitem_get_bounds_type.return_value = 0

        # Set recording output path to None (no recording path captured)
        original_recording_path = script_module.recording_output_path
        script_module.recording_output_path = None  # No recording path captured

        try:
            # Call collect_and_save_metadata
            from src.obs_integration.obs_script import collect_and_save_metadata

            collect_and_save_metadata()

            # Should fall back to default behavior when recording path not available
            # Check default directory (~/obs-canvas-metadata)
            default_dir = os.path.expanduser("~/obs-canvas-metadata")
            if os.path.exists(default_dir):
                files = os.listdir(default_dir)
                metadata_files = [f for f in files if f.endswith("_metadata.json")]
                assert len(metadata_files) >= 1

        finally:
            # Restore original paths
            script_module.recording_output_path = original_recording_path
