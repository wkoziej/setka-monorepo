"""
Testy dla importów modułów.
"""


class TestImports:
    """Testy dla importów modułów."""

    def test_specialized_imports(self):
        """Test importów z specialized module."""
        from setka_common.file_structure.specialized import RecordingStructureManager
        from setka_common.file_structure.specialized.recording import RecordingStructure

        assert RecordingStructureManager is not None
        assert RecordingStructure is not None

    def test_utils_imports(self):
        """Test importów z utils module."""
        from setka_common.utils import (
            find_files_by_type,
            find_media_files,
            sanitize_filename,
        )

        assert find_files_by_type is not None
        assert find_media_files is not None
        assert sanitize_filename is not None

    def test_file_structure_imports(self):
        """Test importów z file_structure module."""
        from setka_common.file_structure import MediaStructure, StructureManager
        from setka_common.file_structure.types import MediaType, FileExtensions

        assert MediaStructure is not None
        assert StructureManager is not None
        assert MediaType is not None
        assert FileExtensions is not None

    def test_top_level_imports(self):
        """Test importów z głównego modułu."""
        import setka_common

        assert setka_common is not None
