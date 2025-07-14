"""
Testy dla modułu file_structure.py
"""

from src.core.file_structure import RecordingStructure, FileStructureManager


class TestRecordingStructure:
    """Testy dla klasy RecordingStructure."""

    def test_recording_structure_creation(self, tmp_path):
        """Test tworzenia struktury nagrania."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test.mkv"
        metadata_file = recording_dir / "metadata.json"
        extracted_dir = recording_dir / "extracted"

        structure = RecordingStructure(
            recording_dir=recording_dir,
            video_file=video_file,
            metadata_file=metadata_file,
            extracted_dir=extracted_dir,
        )

        assert structure.recording_dir == recording_dir
        assert structure.video_file == video_file
        assert structure.metadata_file == metadata_file
        assert structure.extracted_dir == extracted_dir

    def test_exists_all_present(self, tmp_path):
        """Test exists() gdy wszystkie pliki istnieją."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        video_file = recording_dir / "test.mkv"
        video_file.touch()

        metadata_file = recording_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()

        structure = RecordingStructure(
            recording_dir=recording_dir,
            video_file=video_file,
            metadata_file=metadata_file,
            extracted_dir=extracted_dir,
        )

        assert structure.exists() is True

    def test_exists_missing_files(self, tmp_path):
        """Test exists() gdy brakuje plików."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test.mkv"
        metadata_file = recording_dir / "metadata.json"
        extracted_dir = recording_dir / "extracted"

        structure = RecordingStructure(
            recording_dir=recording_dir,
            video_file=video_file,
            metadata_file=metadata_file,
            extracted_dir=extracted_dir,
        )

        assert structure.exists() is False

    def test_is_valid_correct_structure(self, tmp_path):
        """Test is_valid() dla poprawnej struktury."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        video_file = recording_dir / "test.mkv"
        video_file.touch()

        metadata_file = recording_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()

        structure = RecordingStructure(
            recording_dir=recording_dir,
            video_file=video_file,
            metadata_file=metadata_file,
            extracted_dir=extracted_dir,
        )

        assert structure.is_valid() is True

    def test_is_valid_invalid_json(self, tmp_path):
        """Test is_valid() dla niepoprawnego JSON."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        video_file = recording_dir / "test.mkv"
        video_file.touch()

        metadata_file = recording_dir / "metadata.json"
        metadata_file.write_text("invalid json")

        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()

        structure = RecordingStructure(
            recording_dir=recording_dir,
            video_file=video_file,
            metadata_file=metadata_file,
            extracted_dir=extracted_dir,
        )

        assert structure.is_valid() is False

    def test_is_valid_missing_files(self, tmp_path):
        """Test is_valid() dla brakujących plików."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test.mkv"
        metadata_file = recording_dir / "metadata.json"
        extracted_dir = recording_dir / "extracted"

        structure = RecordingStructure(
            recording_dir=recording_dir,
            video_file=video_file,
            metadata_file=metadata_file,
            extracted_dir=extracted_dir,
        )

        assert structure.is_valid() is False


class TestFileStructureManager:
    """Testy dla klasy FileStructureManager."""

    def test_get_structure(self, tmp_path):
        """Test get_structure()."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test.mkv"

        structure = FileStructureManager.get_structure(video_file)

        assert structure.recording_dir == recording_dir
        assert structure.video_file == video_file
        assert structure.metadata_file == recording_dir / "metadata.json"
        assert structure.extracted_dir == recording_dir / "extracted"

    def test_create_structure(self, tmp_path):
        """Test create_structure()."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()
        video_file = recording_dir / "test.mkv"

        structure = FileStructureManager.create_structure(video_file)

        assert structure.extracted_dir.exists()
        assert structure.extracted_dir.is_dir()

    def test_get_extracted_dir(self, tmp_path):
        """Test get_extracted_dir()."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test.mkv"

        extracted_dir = FileStructureManager.get_extracted_dir(video_file)

        assert extracted_dir == recording_dir / "extracted"

    def test_get_metadata_file(self, tmp_path):
        """Test get_metadata_file()."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test.mkv"

        metadata_file = FileStructureManager.get_metadata_file(video_file)

        assert metadata_file == recording_dir / "metadata.json"

    def test_create_recording_directory_name(self, tmp_path):
        """Test create_recording_directory_name()."""
        video_file = tmp_path / "test_recording.mkv"

        dir_name = FileStructureManager.create_recording_directory_name(video_file)

        assert dir_name == "test_recording"

    def test_find_recording_structure_found(self, tmp_path):
        """Test find_recording_structure() - struktura znaleziona."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        video_file = recording_dir / "test.mkv"
        video_file.touch()

        metadata_file = recording_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()

        structure = FileStructureManager.find_recording_structure(recording_dir)

        assert structure is not None
        assert structure.recording_dir == recording_dir
        assert structure.video_file == video_file
        assert structure.metadata_file == metadata_file
        assert structure.extracted_dir == extracted_dir

    def test_find_recording_structure_no_metadata(self, tmp_path):
        """Test find_recording_structure() - brak metadata.json."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        video_file = recording_dir / "test.mkv"
        video_file.touch()

        structure = FileStructureManager.find_recording_structure(recording_dir)

        assert structure is None

    def test_find_recording_structure_no_video(self, tmp_path):
        """Test find_recording_structure() - brak pliku wideo."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        metadata_file = recording_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        structure = FileStructureManager.find_recording_structure(recording_dir)

        assert structure is None

    def test_find_recording_structure_nonexistent_dir(self, tmp_path):
        """Test find_recording_structure() - katalog nie istnieje."""
        nonexistent_dir = tmp_path / "nonexistent"

        structure = FileStructureManager.find_recording_structure(nonexistent_dir)

        assert structure is None

    def test_find_recording_structure_multiple_video_files(self, tmp_path):
        """Test find_recording_structure() - wiele plików wideo."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        video_file1 = recording_dir / "test1.mkv"
        video_file1.touch()

        video_file2 = recording_dir / "test2.mp4"
        video_file2.touch()

        metadata_file = recording_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()

        structure = FileStructureManager.find_recording_structure(recording_dir)

        assert structure is not None
        # Powinien znaleźć jeden z plików wideo
        assert structure.video_file in [video_file1, video_file2]

    def test_ensure_extracted_dir(self, tmp_path):
        """Test ensure_extracted_dir()."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()
        video_file = recording_dir / "test.mkv"

        extracted_dir = FileStructureManager.ensure_extracted_dir(video_file)

        assert extracted_dir.exists()
        assert extracted_dir.is_dir()
        assert extracted_dir == recording_dir / "extracted"

    def test_ensure_extracted_dir_already_exists(self, tmp_path):
        """Test ensure_extracted_dir() gdy katalog już istnieje."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()
        video_file = recording_dir / "test.mkv"

        # Utwórz katalog extracted
        existing_extracted = recording_dir / "extracted"
        existing_extracted.mkdir()

        extracted_dir = FileStructureManager.ensure_extracted_dir(video_file)

        assert extracted_dir.exists()
        assert extracted_dir.is_dir()
        assert extracted_dir == existing_extracted

    def test_ensure_blender_dir(self, tmp_path):
        """Test ensure_blender_dir() - tworzenie katalogu blender."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        blender_dir = FileStructureManager.ensure_blender_dir(recording_dir)

        assert blender_dir == recording_dir / "blender"
        assert blender_dir.exists()
        assert blender_dir.is_dir()

        # Sprawdź czy katalog render został utworzony
        render_dir = blender_dir / "render"
        assert render_dir.exists()
        assert render_dir.is_dir()

    def test_ensure_blender_dir_already_exists(self, tmp_path):
        """Test ensure_blender_dir() gdy katalog już istnieje."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        # Utwórz katalog blender
        blender_dir = recording_dir / "blender"
        blender_dir.mkdir()

        result = FileStructureManager.ensure_blender_dir(recording_dir)

        assert result == blender_dir
        assert blender_dir.exists()
        assert blender_dir.is_dir()

    def test_find_audio_files_empty_directory(self, tmp_path):
        """Test find_audio_files() z pustym katalogiem."""
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()

        audio_files = FileStructureManager.find_audio_files(extracted_dir)

        assert audio_files == []

    def test_find_audio_files_with_audio(self, tmp_path):
        """Test find_audio_files() z plikami audio."""
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()

        # Utwórz pliki audio
        audio_files = [
            extracted_dir / "main.mp3",
            extracted_dir / "background.wav",
            extracted_dir / "voice.m4a",
        ]

        for file_path in audio_files:
            file_path.touch()

        # Utwórz pliki nie-audio
        (extracted_dir / "video.mp4").touch()
        (extracted_dir / "document.txt").touch()

        found_audio = FileStructureManager.find_audio_files(extracted_dir)

        # Sprawdź czy znaleziono tylko pliki audio, posortowane
        expected = [
            extracted_dir / "background.wav",
            extracted_dir / "main.mp3",
            extracted_dir / "voice.m4a",
        ]
        assert found_audio == expected

    def test_find_audio_files_nonexistent_directory(self, tmp_path):
        """Test find_audio_files() z nieistniejącym katalogiem."""
        nonexistent_dir = tmp_path / "nonexistent"

        audio_files = FileStructureManager.find_audio_files(nonexistent_dir)

        assert audio_files == []

    def test_find_video_files_empty_directory(self, tmp_path):
        """Test find_video_files() z pustym katalogiem."""
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()

        video_files = FileStructureManager.find_video_files(extracted_dir)

        assert video_files == []

    def test_find_video_files_with_videos(self, tmp_path):
        """Test find_video_files() z plikami wideo."""
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()

        # Utwórz pliki wideo
        video_files = [
            extracted_dir / "camera1.mp4",
            extracted_dir / "screen.mkv",
            extracted_dir / "webcam.avi",
        ]

        for file_path in video_files:
            file_path.touch()

        # Utwórz pliki nie-wideo
        (extracted_dir / "audio.mp3").touch()
        (extracted_dir / "document.txt").touch()

        found_videos = FileStructureManager.find_video_files(extracted_dir)

        # Sprawdź czy znaleziono tylko pliki wideo, posortowane
        expected = [
            extracted_dir / "camera1.mp4",
            extracted_dir / "screen.mkv",
            extracted_dir / "webcam.avi",
        ]
        assert found_videos == expected

    def test_find_video_files_nonexistent_directory(self, tmp_path):
        """Test find_video_files() z nieistniejącym katalogiem."""
        nonexistent_dir = tmp_path / "nonexistent"

        video_files = FileStructureManager.find_video_files(nonexistent_dir)

        assert video_files == []

    def test_find_video_files_case_insensitive(self, tmp_path):
        """Test find_video_files() z różnymi wielkościami liter w rozszerzeniach."""
        extracted_dir = tmp_path / "extracted"
        extracted_dir.mkdir()

        # Utwórz pliki z różnymi wielkościami liter
        video_files = [
            extracted_dir / "video1.MP4",
            extracted_dir / "video2.MKV",
            extracted_dir / "video3.AVI",
        ]

        for file_path in video_files:
            file_path.touch()

        found_videos = FileStructureManager.find_video_files(extracted_dir)

        assert len(found_videos) == 3
        assert all(f.suffix.lower() in [".mp4", ".mkv", ".avi"] for f in found_videos)


class TestFileStructureAnalysisIntegration:
    """Testy integracji FileStructureManager z audio analysis."""

    def test_ensure_analysis_dir_creates_directory(self, tmp_path):
        """Test ensure_analysis_dir() tworzy katalog analysis."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        analysis_dir = FileStructureManager.ensure_analysis_dir(recording_dir)

        assert analysis_dir == recording_dir / "analysis"
        assert analysis_dir.exists()
        assert analysis_dir.is_dir()

    def test_ensure_analysis_dir_already_exists(self, tmp_path):
        """Test ensure_analysis_dir() gdy katalog już istnieje."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        # Utwórz katalog analysis
        existing_analysis = recording_dir / "analysis"
        existing_analysis.mkdir()

        analysis_dir = FileStructureManager.ensure_analysis_dir(recording_dir)

        assert analysis_dir == existing_analysis
        assert analysis_dir.exists()
        assert analysis_dir.is_dir()

    def test_get_analysis_file_path(self, tmp_path):
        """Test get_analysis_file_path() zwraca poprawną ścieżkę."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test_recording.mkv"

        analysis_path = FileStructureManager.get_analysis_file_path(video_file)

        expected = recording_dir / "analysis" / "test_recording_analysis.json"
        assert analysis_path == expected

    def test_save_audio_analysis_creates_structure(self, tmp_path):
        """Test save_audio_analysis() tworzy katalog i zapisuje plik."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test_recording.mkv"

        analysis_data = {
            "duration": 10.0,
            "tempo": {"bpm": 120.0},
            "animation_events": {"beats": [1.0, 2.0, 3.0]},
        }

        saved_path = FileStructureManager.save_audio_analysis(video_file, analysis_data)

        # Sprawdź czy katalog analysis został utworzony
        analysis_dir = recording_dir / "analysis"
        assert analysis_dir.exists()
        assert analysis_dir.is_dir()

        # Sprawdź czy plik został zapisany
        expected_path = analysis_dir / "test_recording_analysis.json"
        assert saved_path == expected_path
        assert saved_path.exists()

        # Sprawdź zawartość pliku
        import json

        with open(saved_path) as f:
            loaded_data = json.load(f)
        assert loaded_data == analysis_data

    def test_find_audio_analysis_file_exists(self, tmp_path):
        """Test find_audio_analysis() gdy plik istnieje."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()
        video_file = recording_dir / "test_recording.mkv"

        # Utwórz katalog analysis i plik
        analysis_dir = recording_dir / "analysis"
        analysis_dir.mkdir()
        analysis_file = analysis_dir / "test_recording_analysis.json"
        analysis_file.write_text('{"test": "data"}')

        found_path = FileStructureManager.find_audio_analysis(video_file)

        assert found_path == analysis_file
        assert found_path.exists()

    def test_find_audio_analysis_file_not_exists(self, tmp_path):
        """Test find_audio_analysis() gdy plik nie istnieje."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test_recording.mkv"

        found_path = FileStructureManager.find_audio_analysis(video_file)

        assert found_path is None

    def test_load_audio_analysis_valid_file(self, tmp_path):
        """Test load_audio_analysis() z poprawnym plikiem."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()
        video_file = recording_dir / "test_recording.mkv"

        # Utwórz plik analizy
        analysis_data = {
            "duration": 5.0,
            "tempo": {"bpm": 140.0},
            "animation_events": {"beats": [0.5, 1.0, 1.5]},
        }

        analysis_dir = recording_dir / "analysis"
        analysis_dir.mkdir()
        analysis_file = analysis_dir / "test_recording_analysis.json"

        import json

        with open(analysis_file, "w") as f:
            json.dump(analysis_data, f)

        loaded_data = FileStructureManager.load_audio_analysis(video_file)

        assert loaded_data == analysis_data

    def test_load_audio_analysis_missing_file(self, tmp_path):
        """Test load_audio_analysis() z brakującym plikiem."""
        recording_dir = tmp_path / "test_recording"
        video_file = recording_dir / "test_recording.mkv"

        loaded_data = FileStructureManager.load_audio_analysis(video_file)

        assert loaded_data is None

    def test_load_audio_analysis_invalid_json(self, tmp_path):
        """Test load_audio_analysis() z niepoprawnym JSON."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()
        video_file = recording_dir / "test_recording.mkv"

        # Utwórz plik z niepoprawnym JSON
        analysis_dir = recording_dir / "analysis"
        analysis_dir.mkdir()
        analysis_file = analysis_dir / "test_recording_analysis.json"
        analysis_file.write_text("invalid json content")

        loaded_data = FileStructureManager.load_audio_analysis(video_file)

        assert loaded_data is None

    def test_complete_structure_with_analysis(self, tmp_path):
        """Test pełnej struktury z katalogiem analysis."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        video_file = recording_dir / "test.mkv"
        video_file.touch()

        metadata_file = recording_dir / "metadata.json"
        metadata_file.write_text('{"test": "data"}')

        # Utwórz wszystkie katalogi
        FileStructureManager.ensure_extracted_dir(video_file)
        FileStructureManager.ensure_blender_dir(recording_dir)
        FileStructureManager.ensure_analysis_dir(recording_dir)

        # Sprawdź pełną strukturę
        expected_dirs = [
            recording_dir / "extracted",
            recording_dir / "blender",
            recording_dir / "blender" / "render",
            recording_dir / "analysis",
        ]

        for expected_dir in expected_dirs:
            assert expected_dir.exists()
            assert expected_dir.is_dir()

        # Sprawdź że find_recording_structure nadal działa
        structure = FileStructureManager.find_recording_structure(recording_dir)
        assert structure is not None
        assert structure.is_valid()
