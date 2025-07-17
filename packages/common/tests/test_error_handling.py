"""
Testy dla obsługi błędów w setka-common.
"""

import pytest
from pathlib import Path

from setka_common.exceptions import (
    InvalidPathError,
    DirectoryCreationError,
    StructureValidationError,
    FileNotFoundError,
    InvalidFileFormatError,
    MetadataError,
)
from setka_common.file_structure.base import StructureManager
from setka_common.file_structure.specialized.recording import RecordingStructureManager
from setka_common.utils.files import find_files_by_type, find_media_files, sanitize_filename
from setka_common.file_structure.types import MediaType


class TestExceptions:
    """Testy dla klas wyjątków."""

    def test_exception_hierarchy(self):
        """Test hierarchii wyjątków."""
        from setka_common.exceptions import SetkaCommonError
        
        # Test inheritance
        assert issubclass(InvalidPathError, SetkaCommonError)
        assert issubclass(DirectoryCreationError, SetkaCommonError)
        assert issubclass(StructureValidationError, SetkaCommonError)
        assert issubclass(FileNotFoundError, SetkaCommonError)
        assert issubclass(InvalidFileFormatError, SetkaCommonError)
        assert issubclass(MetadataError, SetkaCommonError)

    def test_exception_messages(self):
        """Test wiadomości wyjątków."""
        message = "Test error message"
        
        error = InvalidPathError(message)
        assert str(error) == message
        
        error = DirectoryCreationError(message)
        assert str(error) == message


class TestBaseStructureManagerErrorHandling:
    """Testy obsługi błędów w StructureManager."""

    def test_get_structure_empty_path(self):
        """Test get_structure() z pustą ścieżką."""
        with pytest.raises(InvalidPathError, match="Media path cannot be empty"):
            StructureManager.get_structure("")

    def test_get_structure_none_path(self):
        """Test get_structure() z None."""
        with pytest.raises(InvalidPathError, match="Media path cannot be empty"):
            StructureManager.get_structure(None)

    def test_get_structure_invalid_path(self):
        """Test get_structure() z niepoprawną ścieżką."""
        with pytest.raises(InvalidPathError, match="Invalid media path"):
            StructureManager.get_structure(Path())

    def test_create_structure_permission_error(self, tmp_path, monkeypatch):
        """Test create_structure() z błędem uprawnień."""
        media_file = tmp_path / "test.mp4"
        
        # Mock mkdir to raise PermissionError
        def mock_mkdir(*args, **kwargs):
            raise PermissionError("Permission denied")
        
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)
        
        with pytest.raises(DirectoryCreationError, match="Failed to create structure"):
            StructureManager.create_structure(media_file)

    def test_ensure_directory_empty_base_path(self):
        """Test ensure_directory() z pustą ścieżką bazową."""
        with pytest.raises(InvalidPathError, match="Base path cannot be empty"):
            StructureManager.ensure_directory("", "test")

    def test_ensure_directory_empty_dirname(self, tmp_path):
        """Test ensure_directory() z pustą nazwą katalogu."""
        with pytest.raises(InvalidPathError, match="Directory name cannot be empty"):
            StructureManager.ensure_directory(tmp_path, "")

    def test_ensure_directory_nonexistent_base(self, tmp_path):
        """Test ensure_directory() z nieistniejącą ścieżką bazową."""
        nonexistent = tmp_path / "nonexistent"
        
        with pytest.raises(InvalidPathError, match="Base path does not exist"):
            StructureManager.ensure_directory(nonexistent, "test")

    def test_ensure_directory_file_as_base(self, tmp_path):
        """Test ensure_directory() z plikiem jako ścieżką bazową."""
        file_path = tmp_path / "test.txt"
        file_path.touch()
        
        with pytest.raises(InvalidPathError, match="Base path is not a directory"):
            StructureManager.ensure_directory(file_path, "test")

    def test_ensure_directory_permission_error(self, tmp_path, monkeypatch):
        """Test ensure_directory() z błędem uprawnień."""
        # Mock mkdir to raise PermissionError
        def mock_mkdir(*args, **kwargs):
            raise PermissionError("Permission denied")
        
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)
        
        with pytest.raises(DirectoryCreationError, match="Failed to create directory"):
            StructureManager.ensure_directory(tmp_path, "test")


class TestRecordingStructureManagerErrorHandling:
    """Testy obsługi błędów w RecordingStructureManager."""

    def test_get_structure_empty_path(self):
        """Test get_structure() z pustą ścieżką."""
        with pytest.raises(InvalidPathError, match="Video path cannot be empty"):
            RecordingStructureManager.get_structure("")

    def test_get_structure_none_path(self):
        """Test get_structure() z None."""
        with pytest.raises(InvalidPathError, match="Video path cannot be empty"):
            RecordingStructureManager.get_structure(None)

    def test_create_structure_permission_error(self, tmp_path, monkeypatch):
        """Test create_structure() z błędem uprawnień."""
        video_file = tmp_path / "test.mkv"
        
        # Mock mkdir to raise PermissionError
        def mock_mkdir(*args, **kwargs):
            raise PermissionError("Permission denied")
        
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)
        
        with pytest.raises(DirectoryCreationError, match="Failed to create recording structure"):
            RecordingStructureManager.create_structure(video_file)

    def test_find_recording_structure_empty_path(self):
        """Test find_recording_structure() z pustą ścieżką."""
        with pytest.raises(InvalidPathError, match="Base path cannot be empty"):
            RecordingStructureManager.find_recording_structure("")

    def test_find_recording_structure_none_path(self):
        """Test find_recording_structure() z None."""
        with pytest.raises(InvalidPathError, match="Base path cannot be empty"):
            RecordingStructureManager.find_recording_structure(None)

    def test_ensure_blender_dir_empty_path(self):
        """Test ensure_blender_dir() z pustą ścieżką."""
        with pytest.raises(InvalidPathError, match="Recording directory cannot be empty"):
            RecordingStructureManager.ensure_blender_dir("")

    def test_ensure_blender_dir_nonexistent(self, tmp_path):
        """Test ensure_blender_dir() z nieistniejącą ścieżką."""
        nonexistent = tmp_path / "nonexistent"
        
        with pytest.raises(InvalidPathError, match="Recording directory does not exist"):
            RecordingStructureManager.ensure_blender_dir(nonexistent)

    def test_ensure_blender_dir_file_path(self, tmp_path):
        """Test ensure_blender_dir() z plikiem jako ścieżką."""
        file_path = tmp_path / "test.txt"
        file_path.touch()
        
        with pytest.raises(InvalidPathError, match="Recording path is not a directory"):
            RecordingStructureManager.ensure_blender_dir(file_path)

    def test_ensure_blender_dir_permission_error(self, tmp_path, monkeypatch):
        """Test ensure_blender_dir() z błędem uprawnień."""
        # Mock mkdir to raise PermissionError
        def mock_mkdir(*args, **kwargs):
            raise PermissionError("Permission denied")
        
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)
        
        with pytest.raises(DirectoryCreationError, match="Failed to create blender directory"):
            RecordingStructureManager.ensure_blender_dir(tmp_path)

    def test_ensure_analysis_dir_empty_path(self):
        """Test ensure_analysis_dir() z pustą ścieżką."""
        with pytest.raises(InvalidPathError, match="Recording directory cannot be empty"):
            RecordingStructureManager.ensure_analysis_dir("")

    def test_ensure_analysis_dir_permission_error(self, tmp_path, monkeypatch):
        """Test ensure_analysis_dir() z błędem uprawnień."""
        # Mock mkdir to raise PermissionError
        def mock_mkdir(*args, **kwargs):
            raise PermissionError("Permission denied")
        
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)
        
        with pytest.raises(DirectoryCreationError, match="Failed to create analysis directory"):
            RecordingStructureManager.ensure_analysis_dir(tmp_path)

    def test_get_analysis_file_path_empty_path(self):
        """Test get_analysis_file_path() z pustą ścieżką."""
        with pytest.raises(InvalidPathError, match="Video path cannot be empty"):
            RecordingStructureManager.get_analysis_file_path("")

    def test_get_analysis_file_path_invalid_path(self):
        """Test get_analysis_file_path() z niepoprawną ścieżką."""
        with pytest.raises(InvalidPathError, match="Invalid video path"):
            RecordingStructureManager.get_analysis_file_path(Path())

    def test_find_audio_analysis_invalid_path(self):
        """Test find_audio_analysis() z niepoprawną ścieżką."""
        # Should return None instead of raising exception
        result = RecordingStructureManager.find_audio_analysis("")
        assert result is None


class TestFileUtilsErrorHandling:
    """Testy obsługi błędów w utils.files."""

    def test_find_files_by_type_empty_directory(self):
        """Test find_files_by_type() z pustą ścieżką katalogu."""
        with pytest.raises(InvalidPathError, match="Directory cannot be empty"):
            find_files_by_type("", MediaType.VIDEO)

    def test_find_files_by_type_none_directory(self):
        """Test find_files_by_type() z None jako katalogiem."""
        with pytest.raises(InvalidPathError, match="Directory cannot be empty"):
            find_files_by_type(None, MediaType.VIDEO)

    def test_find_files_by_type_invalid_media_type(self, tmp_path):
        """Test find_files_by_type() z niepoprawnym typem media."""
        with pytest.raises(ValueError, match="Invalid media type"):
            find_files_by_type(tmp_path, "invalid_type")

    def test_find_files_by_type_permission_error(self, tmp_path, monkeypatch):
        """Test find_files_by_type() z błędem uprawnień."""
        # Mock iterdir to raise PermissionError
        def mock_iterdir(*args, **kwargs):
            raise PermissionError("Permission denied")
        
        monkeypatch.setattr(Path, "iterdir", mock_iterdir)
        
        # Should return empty list instead of raising exception
        result = find_files_by_type(tmp_path, MediaType.VIDEO)
        assert result == []

    def test_find_media_files_empty_directory(self):
        """Test find_media_files() z pustą ścieżką katalogu."""
        with pytest.raises(InvalidPathError, match="Directory cannot be empty"):
            find_media_files("")

    def test_find_media_files_none_directory(self):
        """Test find_media_files() z None jako katalogiem."""
        with pytest.raises(InvalidPathError, match="Directory cannot be empty"):
            find_media_files(None)

    def test_sanitize_filename_not_string(self):
        """Test sanitize_filename() z nie-stringiem."""
        with pytest.raises(ValueError, match="Filename must be a string"):
            sanitize_filename(123)

    def test_sanitize_filename_none(self):
        """Test sanitize_filename() z None."""
        with pytest.raises(ValueError, match="Filename must be a string"):
            sanitize_filename(None)