"""
Testy dla modułu utils.files.
"""

from setka_common.utils.files import (
    find_files_by_type,
    find_media_files,
    sanitize_filename,
)
from setka_common.file_structure.types import MediaType


class TestFindFilesByType:
    """Testy dla funkcji find_files_by_type."""

    def test_find_video_files(self, tmp_path):
        """Test znajdowania plików video."""
        test_dir = tmp_path / "test_media"
        test_dir.mkdir()

        # Create video files
        video1 = test_dir / "video1.mp4"
        video1.touch()
        video2 = test_dir / "video2.mkv"
        video2.touch()
        video3 = test_dir / "video3.avi"
        video3.touch()

        # Create non-video files
        audio1 = test_dir / "audio1.mp3"
        audio1.touch()
        text1 = test_dir / "text1.txt"
        text1.touch()

        result = find_files_by_type(test_dir, MediaType.VIDEO)

        assert len(result) == 3
        assert video1 in result
        assert video2 in result
        assert video3 in result
        assert audio1 not in result
        assert text1 not in result

    def test_find_audio_files(self, tmp_path):
        """Test znajdowania plików audio."""
        test_dir = tmp_path / "test_media"
        test_dir.mkdir()

        # Create audio files
        audio1 = test_dir / "audio1.mp3"
        audio1.touch()
        audio2 = test_dir / "audio2.wav"
        audio2.touch()
        audio3 = test_dir / "audio3.m4a"
        audio3.touch()

        # Create non-audio files
        video1 = test_dir / "video1.mp4"
        video1.touch()
        image1 = test_dir / "image1.jpg"
        image1.touch()

        result = find_files_by_type(test_dir, MediaType.AUDIO)

        assert len(result) == 3
        assert audio1 in result
        assert audio2 in result
        assert audio3 in result
        assert video1 not in result
        assert image1 not in result

    def test_find_image_files(self, tmp_path):
        """Test znajdowania plików obrazów."""
        test_dir = tmp_path / "test_media"
        test_dir.mkdir()

        # Create image files
        image1 = test_dir / "image1.jpg"
        image1.touch()
        image2 = test_dir / "image2.png"
        image2.touch()
        image3 = test_dir / "image3.gif"
        image3.touch()

        # Create non-image files
        video1 = test_dir / "video1.mp4"
        video1.touch()
        audio1 = test_dir / "audio1.mp3"
        audio1.touch()

        result = find_files_by_type(test_dir, MediaType.IMAGE)

        assert len(result) == 3
        assert image1 in result
        assert image2 in result
        assert image3 in result
        assert video1 not in result
        assert audio1 not in result

    def test_find_document_files(self, tmp_path):
        """Test znajdowania plików dokumentów."""
        test_dir = tmp_path / "test_media"
        test_dir.mkdir()

        # Create document files
        doc1 = test_dir / "doc1.pdf"
        doc1.touch()
        doc2 = test_dir / "doc2.txt"
        doc2.touch()
        doc3 = test_dir / "doc3.md"
        doc3.touch()

        # Create non-document files
        video1 = test_dir / "video1.mp4"
        video1.touch()
        audio1 = test_dir / "audio1.mp3"
        audio1.touch()

        result = find_files_by_type(test_dir, MediaType.DOCUMENT)

        assert len(result) == 3
        assert doc1 in result
        assert doc2 in result
        assert doc3 in result
        assert video1 not in result
        assert audio1 not in result

    def test_case_insensitive_matching(self, tmp_path):
        """Test niezależności od wielkości liter."""
        test_dir = tmp_path / "test_media"
        test_dir.mkdir()

        # Create files with uppercase extensions
        video1 = test_dir / "video1.MP4"
        video1.touch()
        video2 = test_dir / "video2.MKV"
        video2.touch()
        audio1 = test_dir / "audio1.WAV"
        audio1.touch()

        result = find_files_by_type(test_dir, MediaType.VIDEO)

        assert len(result) == 2
        assert video1 in result
        assert video2 in result
        assert audio1 not in result

    def test_sorted_output(self, tmp_path):
        """Test sortowania wyników."""
        test_dir = tmp_path / "test_media"
        test_dir.mkdir()

        # Create files in non-alphabetical order
        video_c = test_dir / "c_video.mp4"
        video_c.touch()
        video_a = test_dir / "a_video.mp4"
        video_a.touch()
        video_b = test_dir / "b_video.mp4"
        video_b.touch()

        result = find_files_by_type(test_dir, MediaType.VIDEO)

        assert len(result) == 3
        assert result[0] == video_a
        assert result[1] == video_b
        assert result[2] == video_c

    def test_nonexistent_directory(self, tmp_path):
        """Test dla nieistniejącego katalogu."""
        nonexistent_dir = tmp_path / "nonexistent"

        result = find_files_by_type(nonexistent_dir, MediaType.VIDEO)

        assert result == []

    def test_empty_directory(self, tmp_path):
        """Test dla pustego katalogu."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = find_files_by_type(empty_dir, MediaType.VIDEO)

        assert result == []

    def test_ignore_subdirectories(self, tmp_path):
        """Test ignorowania podkatalogów."""
        test_dir = tmp_path / "test_media"
        test_dir.mkdir()

        # Create file in main directory
        video1 = test_dir / "video1.mp4"
        video1.touch()

        # Create subdirectory with file
        subdir = test_dir / "subdir"
        subdir.mkdir()
        video2 = subdir / "video2.mp4"
        video2.touch()

        result = find_files_by_type(test_dir, MediaType.VIDEO)

        assert len(result) == 1
        assert video1 in result
        assert video2 not in result


class TestFindMediaFiles:
    """Testy dla funkcji find_media_files."""

    def test_find_mixed_media_files(self, tmp_path):
        """Test znajdowania mieszanych plików mediów."""
        test_dir = tmp_path / "test_media"
        test_dir.mkdir()

        # Create various media files
        video1 = test_dir / "video1.mp4"
        video1.touch()
        video2 = test_dir / "video2.mkv"
        video2.touch()

        audio1 = test_dir / "audio1.mp3"
        audio1.touch()
        audio2 = test_dir / "audio2.wav"
        audio2.touch()

        image1 = test_dir / "image1.jpg"
        image1.touch()

        doc1 = test_dir / "doc1.pdf"
        doc1.touch()

        result = find_media_files(test_dir)

        assert MediaType.VIDEO in result
        assert MediaType.AUDIO in result
        assert MediaType.IMAGE in result
        assert MediaType.DOCUMENT in result

        assert len(result[MediaType.VIDEO]) == 2
        assert len(result[MediaType.AUDIO]) == 2
        assert len(result[MediaType.IMAGE]) == 1
        assert len(result[MediaType.DOCUMENT]) == 1

        assert video1 in result[MediaType.VIDEO]
        assert video2 in result[MediaType.VIDEO]
        assert audio1 in result[MediaType.AUDIO]
        assert audio2 in result[MediaType.AUDIO]
        assert image1 in result[MediaType.IMAGE]
        assert doc1 in result[MediaType.DOCUMENT]

    def test_find_media_files_partial_types(self, tmp_path):
        """Test gdy są tylko niektóre typy plików."""
        test_dir = tmp_path / "test_media"
        test_dir.mkdir()

        # Create only video files
        video1 = test_dir / "video1.mp4"
        video1.touch()
        video2 = test_dir / "video2.mkv"
        video2.touch()

        result = find_media_files(test_dir)

        assert MediaType.VIDEO in result
        assert MediaType.AUDIO not in result
        assert MediaType.IMAGE not in result
        assert MediaType.DOCUMENT not in result

        assert len(result[MediaType.VIDEO]) == 2

    def test_find_media_files_empty_directory(self, tmp_path):
        """Test dla pustego katalogu."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = find_media_files(empty_dir)

        assert result == {}


class TestSanitizeFilename:
    """Testy dla funkcji sanitize_filename."""

    def test_remove_invalid_characters(self):
        """Test usuwania niepoprawnych znaków."""
        filename = 'test<>:"|?*file.mp4'
        result = sanitize_filename(filename)
        assert result == "test_______file.mp4"

    def test_remove_leading_trailing_spaces(self):
        """Test usuwania spacji na początku i końcu."""
        filename = "  test file.mp4  "
        result = sanitize_filename(filename)
        assert result == "test file.mp4"

    def test_remove_leading_trailing_dots(self):
        """Test usuwania kropek na początku i końcu."""
        filename = "..test file.mp4.."
        result = sanitize_filename(filename)
        assert result == "test file.mp4"

    def test_remove_mixed_leading_trailing(self):
        """Test usuwania mieszanych znaków na początku i końcu."""
        filename = " . test file.mp4 . "
        result = sanitize_filename(filename)
        assert result == "test file.mp4"

    def test_limit_filename_length(self):
        """Test ograniczania długości nazwy pliku."""
        long_name = "a" * 250
        filename = f"{long_name}.mp4"
        result = sanitize_filename(filename)

        assert len(result) <= 255
        assert result.endswith(".mp4")

    def test_limit_filename_length_no_extension(self):
        """Test ograniczania długości nazwy pliku bez rozszerzenia."""
        long_filename = "a" * 300
        result = sanitize_filename(long_filename)

        assert len(result) <= 255
        assert result == "a" * 255

    def test_normal_filename_unchanged(self):
        """Test że normalna nazwa pliku nie jest zmieniona."""
        filename = "normal_file.mp4"
        result = sanitize_filename(filename)
        assert result == filename

    def test_empty_filename(self):
        """Test dla pustej nazwy pliku."""
        filename = ""
        result = sanitize_filename(filename)
        assert result == ""

    def test_only_spaces_and_dots(self):
        """Test dla nazwy składającej się tylko ze spacji i kropek."""
        filename = "  ...  "
        result = sanitize_filename(filename)
        assert result == ""

    def test_filename_with_multiple_dots(self):
        """Test dla nazwy z wieloma kropkami."""
        filename = "my.video.file.mp4"
        result = sanitize_filename(filename)
        assert result == "my.video.file.mp4"

    def test_complex_filename(self):
        """Test dla złożonej nazwy pliku."""
        filename = ' . <test>file|name"with*chars?.mp4 . '
        result = sanitize_filename(filename)
        assert result == "_test_file_name_with_chars_.mp4"
