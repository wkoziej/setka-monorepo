"""
Testy dla modułu recording structure.
"""

import json
from pathlib import Path
import pytest

from setka_common.file_structure.specialized.recording import (
    RecordingStructure,
    RecordingStructureManager,
)
from setka_common.file_structure.types import MediaType


class TestRecordingStructure:
    """Testy dla klasy RecordingStructure."""

    def test_recording_structure_creation(self, tmp_path):
        """Test tworzenia struktury nagrania."""
        project_dir = tmp_path / "test_recording"
        media_file = project_dir / "recording.mkv"
        metadata_file = project_dir / "metadata.json"
        processed_dir = project_dir / "processed"
        extracted_dir = project_dir / "extracted"

        structure = RecordingStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
            extracted_dir=extracted_dir,
        )

        assert structure.project_dir == project_dir
        assert structure.media_file == media_file
        assert structure.metadata_file == metadata_file
        assert structure.processed_dir == processed_dir
        assert structure.extracted_dir == extracted_dir

    def test_exists_all_present(self, tmp_path):
        """Test exists() gdy wszystkie pliki istnieją."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()

        media_file = project_dir / "recording.mkv"
        media_file.touch()

        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        processed_dir = project_dir / "processed"
        processed_dir.mkdir()

        extracted_dir = project_dir / "extracted"
        extracted_dir.mkdir()

        structure = RecordingStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
            extracted_dir=extracted_dir,
        )

        assert structure.exists() is True

    def test_exists_missing_extracted_dir(self, tmp_path):
        """Test exists() gdy brakuje extracted_dir."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()

        media_file = project_dir / "recording.mkv"
        media_file.touch()

        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        processed_dir = project_dir / "processed"
        processed_dir.mkdir()

        extracted_dir = project_dir / "extracted"
        # extracted_dir not created

        structure = RecordingStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
            extracted_dir=extracted_dir,
        )

        assert structure.exists() is False

    def test_is_valid_correct_structure(self, tmp_path):
        """Test is_valid() dla poprawnej struktury."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()

        media_file = project_dir / "recording.mkv"
        media_file.touch()

        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text('{"obs_data": "test"}')

        processed_dir = project_dir / "processed"
        processed_dir.mkdir()

        extracted_dir = project_dir / "extracted"
        extracted_dir.mkdir()

        structure = RecordingStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
            extracted_dir=extracted_dir,
        )

        assert structure.is_valid() is True

    def test_is_valid_invalid_json(self, tmp_path):
        """Test is_valid() dla niepoprawnego JSON."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()

        media_file = project_dir / "recording.mkv"
        media_file.touch()

        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text("invalid json")

        processed_dir = project_dir / "processed"
        processed_dir.mkdir()

        extracted_dir = project_dir / "extracted"
        extracted_dir.mkdir()

        structure = RecordingStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
            extracted_dir=extracted_dir,
        )

        assert structure.is_valid() is False

    def test_is_valid_missing_metadata(self, tmp_path):
        """Test is_valid() gdy metadata nie istnieje."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()

        media_file = project_dir / "recording.mkv"
        media_file.touch()

        metadata_file = project_dir / "metadata.json"
        # metadata_file not created

        processed_dir = project_dir / "processed"
        processed_dir.mkdir()

        extracted_dir = project_dir / "extracted"
        extracted_dir.mkdir()

        structure = RecordingStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
            extracted_dir=extracted_dir,
        )

        assert structure.is_valid() is True  # metadata jest opcjonalna


class TestRecordingStructureManager:
    """Testy dla klasy RecordingStructureManager."""

    def test_get_structure(self, tmp_path):
        """Test get_structure()."""
        project_dir = tmp_path / "test_recording"
        video_file = project_dir / "recording.mkv"

        structure = RecordingStructureManager.get_structure(video_file)

        assert structure.project_dir == project_dir
        assert structure.media_file == video_file
        assert structure.metadata_file == project_dir / "metadata.json"
        assert structure.processed_dir == project_dir / "processed"
        assert structure.extracted_dir == project_dir / "extracted"

    def test_create_structure(self, tmp_path):
        """Test create_structure()."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()
        video_file = project_dir / "recording.mkv"

        structure = RecordingStructureManager.create_structure(video_file)

        assert structure.extracted_dir.exists()
        assert structure.extracted_dir.is_dir()

    def test_get_extracted_dir(self, tmp_path):
        """Test get_extracted_dir()."""
        project_dir = tmp_path / "test_recording"
        video_file = project_dir / "recording.mkv"

        extracted_dir = RecordingStructureManager.get_extracted_dir(video_file)

        assert extracted_dir == project_dir / "extracted"

    def test_find_recording_structure_with_metadata(self, tmp_path):
        """Test find_recording_structure() z metadata."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()

        # Create metadata.json
        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text('{"obs_data": "test"}')

        # Create video file
        video_file = project_dir / "recording.mkv"
        video_file.touch()

        # Create extracted directory
        extracted_dir = project_dir / "extracted"
        extracted_dir.mkdir()

        structure = RecordingStructureManager.find_recording_structure(project_dir)

        assert structure is not None
        assert structure.project_dir == project_dir
        assert structure.media_file == video_file
        assert structure.is_valid()

    def test_find_recording_structure_no_metadata(self, tmp_path):
        """Test find_recording_structure() bez metadata."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()

        # Create video file without metadata
        video_file = project_dir / "recording.mkv"
        video_file.touch()

        structure = RecordingStructureManager.find_recording_structure(project_dir)

        assert structure is None

    def test_find_recording_structure_no_video(self, tmp_path):
        """Test find_recording_structure() bez pliku video."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()

        # Create metadata.json without video
        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text('{"obs_data": "test"}')

        structure = RecordingStructureManager.find_recording_structure(project_dir)

        assert structure is None

    def test_find_recording_structure_nonexistent_directory(self, tmp_path):
        """Test find_recording_structure() dla nieistniejącego katalogu."""
        nonexistent_dir = tmp_path / "nonexistent"

        structure = RecordingStructureManager.find_recording_structure(nonexistent_dir)

        assert structure is None

    def test_find_recording_structure_invalid_json(self, tmp_path):
        """Test find_recording_structure() z niepoprawnym JSON."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()

        # Create invalid metadata.json
        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text("invalid json")

        # Create video file
        video_file = project_dir / "recording.mkv"
        video_file.touch()

        structure = RecordingStructureManager.find_recording_structure(project_dir)

        assert structure is None

    def test_ensure_blender_dir(self, tmp_path):
        """Test ensure_blender_dir()."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        blender_dir = RecordingStructureManager.ensure_blender_dir(recording_dir)

        assert blender_dir == recording_dir / "blender"
        assert blender_dir.exists()
        assert blender_dir.is_dir()

        # Check render subdirectory is created
        render_dir = blender_dir / "render"
        assert render_dir.exists()
        assert render_dir.is_dir()

    def test_ensure_blender_dir_already_exists(self, tmp_path):
        """Test ensure_blender_dir() gdy katalog już istnieje."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        existing_blender_dir = recording_dir / "blender"
        existing_blender_dir.mkdir()

        blender_dir = RecordingStructureManager.ensure_blender_dir(recording_dir)

        assert blender_dir == existing_blender_dir
        assert blender_dir.exists()
        assert blender_dir.is_dir()

    def test_ensure_analysis_dir(self, tmp_path):
        """Test ensure_analysis_dir()."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        analysis_dir = RecordingStructureManager.ensure_analysis_dir(recording_dir)

        assert analysis_dir == recording_dir / "analysis"
        assert analysis_dir.exists()
        assert analysis_dir.is_dir()

    def test_ensure_analysis_dir_already_exists(self, tmp_path):
        """Test ensure_analysis_dir() gdy katalog już istnieje."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        existing_analysis_dir = recording_dir / "analysis"
        existing_analysis_dir.mkdir()

        analysis_dir = RecordingStructureManager.ensure_analysis_dir(recording_dir)

        assert analysis_dir == existing_analysis_dir
        assert analysis_dir.exists()
        assert analysis_dir.is_dir()

    def test_get_analysis_file_path(self, tmp_path):
        """Test get_analysis_file_path()."""
        project_dir = tmp_path / "test_recording"
        video_file = project_dir / "recording.mkv"

        analysis_file_path = RecordingStructureManager.get_analysis_file_path(video_file)

        expected_path = project_dir / "analysis" / "recording_analysis.json"
        assert analysis_file_path == expected_path

    def test_get_analysis_file_path_different_extension(self, tmp_path):
        """Test get_analysis_file_path() dla różnych rozszerzeń."""
        project_dir = tmp_path / "test_recording"
        video_file = project_dir / "recording.mp4"

        analysis_file_path = RecordingStructureManager.get_analysis_file_path(video_file)

        expected_path = project_dir / "analysis" / "recording_analysis.json"
        assert analysis_file_path == expected_path

    def test_find_audio_analysis_exists(self, tmp_path):
        """Test find_audio_analysis() gdy plik istnieje."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()
        video_file = project_dir / "recording.mkv"

        # Create analysis directory and file
        analysis_dir = project_dir / "analysis"
        analysis_dir.mkdir()
        analysis_file = analysis_dir / "recording_analysis.json"
        analysis_file.write_text('{"beats": []}')

        result = RecordingStructureManager.find_audio_analysis(video_file)

        assert result == analysis_file

    def test_find_audio_analysis_not_exists(self, tmp_path):
        """Test find_audio_analysis() gdy plik nie istnieje."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()
        video_file = project_dir / "recording.mkv"

        result = RecordingStructureManager.find_audio_analysis(video_file)

        assert result is None

    def test_constants_values(self):
        """Test wartości stałych."""
        assert RecordingStructureManager.EXTRACTED_DIRNAME == "extracted"
        assert RecordingStructureManager.BLENDER_DIRNAME == "blender"
        assert RecordingStructureManager.ANALYSIS_DIRNAME == "analysis"
        assert RecordingStructureManager.METADATA_FILENAME == "metadata.json"
        assert RecordingStructureManager.PROCESSED_DIRNAME == "processed"