"""
Testy dla modułu file_structure.
"""

import json
from pathlib import Path

import pytest

from setka_common.file_structure.base import MediaStructure, StructureManager
from setka_common.file_structure.types import MediaType


class TestMediaStructure:
    """Testy dla klasy MediaStructure."""

    def test_media_structure_creation(self, tmp_path):
        """Test tworzenia struktury mediów."""
        project_dir = tmp_path / "test_project"
        media_file = project_dir / "test.mp4"
        metadata_file = project_dir / "metadata.json"
        processed_dir = project_dir / "processed"

        structure = MediaStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
        )

        assert structure.project_dir == project_dir
        assert structure.media_file == media_file
        assert structure.metadata_file == metadata_file
        assert structure.processed_dir == processed_dir

    def test_exists_all_present(self, tmp_path):
        """Test exists() gdy wszystkie pliki istnieją."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        media_file = project_dir / "test.mp4"
        media_file.touch()

        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        processed_dir = project_dir / "processed"
        processed_dir.mkdir()

        structure = MediaStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
        )

        assert structure.exists() is True

    def test_exists_missing_files(self, tmp_path):
        """Test exists() gdy brakuje plików."""
        project_dir = tmp_path / "test_project"
        media_file = project_dir / "test.mp4"
        metadata_file = project_dir / "metadata.json"
        processed_dir = project_dir / "processed"

        structure = MediaStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
        )

        assert structure.exists() is False

    def test_is_valid_correct_structure(self, tmp_path):
        """Test is_valid() dla poprawnej struktury."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        media_file = project_dir / "test.mp4"
        media_file.touch()

        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        processed_dir = project_dir / "processed"
        processed_dir.mkdir()

        structure = MediaStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
        )

        assert structure.is_valid() is True

    def test_is_valid_invalid_json(self, tmp_path):
        """Test is_valid() dla niepoprawnego JSON."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        media_file = project_dir / "test.mp4"
        media_file.touch()

        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text("invalid json")

        processed_dir = project_dir / "processed"
        processed_dir.mkdir()

        structure = MediaStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
        )

        assert structure.is_valid() is False

    def test_is_valid_missing_files(self, tmp_path):
        """Test is_valid() dla brakujących plików."""
        project_dir = tmp_path / "test_project"
        media_file = project_dir / "test.mp4"
        metadata_file = project_dir / "metadata.json"
        processed_dir = project_dir / "processed"

        structure = MediaStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
        )

        assert structure.is_valid() is False

    def test_is_valid_optional_metadata(self, tmp_path):
        """Test is_valid() gdy metadata jest opcjonalna."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        media_file = project_dir / "test.mp4"
        media_file.touch()

        # Nie tworzymy metadata_file
        metadata_file = project_dir / "metadata.json"

        processed_dir = project_dir / "processed"
        processed_dir.mkdir()

        structure = MediaStructure(
            project_dir=project_dir,
            media_file=media_file,
            metadata_file=metadata_file,
            processed_dir=processed_dir,
        )

        # Bez metadata.json struktura nadal powinna być valid
        assert structure.is_valid() is True


class TestStructureManager:
    """Testy dla klasy StructureManager."""

    def test_get_structure(self, tmp_path):
        """Test get_structure()."""
        project_dir = tmp_path / "test_project"
        media_file = project_dir / "test.mp4"

        structure = StructureManager.get_structure(media_file)

        assert structure.project_dir == project_dir
        assert structure.media_file == media_file
        assert structure.metadata_file == project_dir / "metadata.json"
        assert structure.processed_dir == project_dir / "processed"

    def test_create_structure(self, tmp_path):
        """Test create_structure()."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        media_file = project_dir / "test.mp4"

        structure = StructureManager.create_structure(media_file)

        assert structure.processed_dir.exists()
        assert structure.processed_dir.is_dir()

    def test_ensure_directory(self, tmp_path):
        """Test ensure_directory()."""
        base_path = tmp_path / "base"
        base_path.mkdir()

        result_dir = StructureManager.ensure_directory(base_path, "test_dir")

        assert result_dir == base_path / "test_dir"
        assert result_dir.exists()
        assert result_dir.is_dir()

    def test_ensure_directory_already_exists(self, tmp_path):
        """Test ensure_directory() gdy katalog już istnieje."""
        base_path = tmp_path / "base"
        base_path.mkdir()
        
        existing_dir = base_path / "existing"
        existing_dir.mkdir()

        result_dir = StructureManager.ensure_directory(base_path, "existing")

        assert result_dir == existing_dir
        assert result_dir.exists()
        assert result_dir.is_dir()