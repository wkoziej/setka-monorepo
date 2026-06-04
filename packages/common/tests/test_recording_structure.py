"""
Testy dla modułu recording structure.
"""

import pytest

from setka_common.file_structure.specialized.recording import (
    RecordingStructure,
    RecordingStructureManager,
    sanitize_stem_name,
)


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
            mixed_dir=project_dir / "mixed",
            bitwig_dir=project_dir / "bitwig",
        )

        assert structure.project_dir == project_dir
        assert structure.media_file == media_file
        assert structure.metadata_file == metadata_file
        assert structure.processed_dir == processed_dir
        assert structure.extracted_dir == extracted_dir
        assert structure.mixed_dir == project_dir / "mixed"

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
            mixed_dir=project_dir / "mixed",
            bitwig_dir=project_dir / "bitwig",
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
            mixed_dir=project_dir / "mixed",
            bitwig_dir=project_dir / "bitwig",
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
            mixed_dir=project_dir / "mixed",
            bitwig_dir=project_dir / "bitwig",
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
            mixed_dir=project_dir / "mixed",
            bitwig_dir=project_dir / "bitwig",
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
            mixed_dir=project_dir / "mixed",
            bitwig_dir=project_dir / "bitwig",
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

    def test_get_structure_mixed_dir(self, tmp_path):
        """Test get_structure() zwraca mixed_dir bez tworzenia katalogu."""
        project_dir = tmp_path / "test_recording"
        video_file = project_dir / "recording.mkv"

        structure = RecordingStructureManager.get_structure(video_file)

        assert structure.mixed_dir == project_dir / "mixed"
        assert not structure.mixed_dir.exists()

    def test_create_structure(self, tmp_path):
        """Test create_structure()."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()
        video_file = project_dir / "recording.mkv"

        structure = RecordingStructureManager.create_structure(video_file)

        assert structure.extracted_dir.exists()
        assert structure.extracted_dir.is_dir()

    def test_create_structure_creates_mixed_dir(self, tmp_path):
        """Test create_structure() tworzy katalog mixed/ obok extracted/."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()
        video_file = project_dir / "recording.mkv"

        structure = RecordingStructureManager.create_structure(video_file)

        assert structure.mixed_dir.exists()
        assert structure.mixed_dir.is_dir()

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

    def test_ensure_mixed_dir(self, tmp_path):
        """Test ensure_mixed_dir()."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        mixed_dir = RecordingStructureManager.ensure_mixed_dir(recording_dir)

        assert mixed_dir == recording_dir / "mixed"
        assert mixed_dir.exists()
        assert mixed_dir.is_dir()

    def test_ensure_mixed_dir_already_exists(self, tmp_path):
        """Test ensure_mixed_dir() gdy katalog już istnieje (idempotentność)."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        existing_mixed_dir = recording_dir / "mixed"
        existing_mixed_dir.mkdir()

        mixed_dir = RecordingStructureManager.ensure_mixed_dir(recording_dir)

        assert mixed_dir == existing_mixed_dir
        assert mixed_dir.exists()
        assert mixed_dir.is_dir()

    def test_get_analysis_file_path(self, tmp_path):
        """Test get_analysis_file_path()."""
        project_dir = tmp_path / "test_recording"
        video_file = project_dir / "recording.mkv"

        analysis_file_path = RecordingStructureManager.get_analysis_file_path(
            video_file
        )

        expected_path = project_dir / "analysis" / "recording_analysis.json"
        assert analysis_file_path == expected_path

    def test_get_analysis_file_path_different_extension(self, tmp_path):
        """Test get_analysis_file_path() dla różnych rozszerzeń."""
        project_dir = tmp_path / "test_recording"
        video_file = project_dir / "recording.mp4"

        analysis_file_path = RecordingStructureManager.get_analysis_file_path(
            video_file
        )

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
        assert RecordingStructureManager.MIXED_DIRNAME == "mixed"
        assert RecordingStructureManager.METADATA_FILENAME == "metadata.json"
        assert RecordingStructureManager.PROCESSED_DIRNAME == "processed"


class TestBitwigDir:
    """Testy dla obsługi katalogu bitwig/ (Unit 1)."""

    def test_bitwig_dirname_constant(self):
        """Test wartości stałej BITWIG_DIRNAME."""
        assert RecordingStructureManager.BITWIG_DIRNAME == "bitwig"

    def test_get_structure_returns_bitwig_dir_path(self, tmp_path):
        """Test get_structure() zwraca bitwig_dir jako ścieżkę bez tworzenia katalogu."""
        project_dir = tmp_path / "test_recording"
        video_file = project_dir / "recording.mkv"

        structure = RecordingStructureManager.get_structure(video_file)

        assert structure.bitwig_dir == project_dir / "bitwig"
        assert not structure.bitwig_dir.exists()

    def test_create_structure_creates_bitwig_dir(self, tmp_path):
        """Test create_structure() materializuje bitwig/ obok extracted/ i mixed/."""
        project_dir = tmp_path / "test_recording"
        project_dir.mkdir()
        video_file = project_dir / "recording.mkv"

        structure = RecordingStructureManager.create_structure(video_file)

        assert structure.bitwig_dir.exists()
        assert structure.bitwig_dir.is_dir()
        assert structure.bitwig_dir == project_dir / "bitwig"

    def test_ensure_bitwig_dir_creates_and_returns_path(self, tmp_path):
        """Test ensure_bitwig_dir() tworzy katalog bitwig/ i zwraca Path."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        bitwig_dir = RecordingStructureManager.ensure_bitwig_dir(recording_dir)

        assert bitwig_dir == recording_dir / "bitwig"
        assert bitwig_dir.exists()
        assert bitwig_dir.is_dir()

    def test_ensure_bitwig_dir_is_idempotent(self, tmp_path):
        """Test ensure_bitwig_dir() jest idempotentne — drugie wywołanie działa poprawnie."""
        recording_dir = tmp_path / "test_recording"
        recording_dir.mkdir()

        bitwig_dir_first = RecordingStructureManager.ensure_bitwig_dir(recording_dir)
        bitwig_dir_second = RecordingStructureManager.ensure_bitwig_dir(recording_dir)

        assert bitwig_dir_first == bitwig_dir_second
        assert bitwig_dir_second.exists()

    def test_ensure_bitwig_dir_empty_path_raises(self, tmp_path):
        """Test ensure_bitwig_dir() dla pustej ścieżki → InvalidPathError."""
        from setka_common.exceptions import InvalidPathError

        import pytest

        with pytest.raises(InvalidPathError):
            RecordingStructureManager.ensure_bitwig_dir("")

    def test_ensure_bitwig_dir_nonexistent_raises(self, tmp_path):
        """Test ensure_bitwig_dir() dla nieistniejącego katalogu → InvalidPathError."""
        from setka_common.exceptions import InvalidPathError

        import pytest

        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(InvalidPathError):
            RecordingStructureManager.ensure_bitwig_dir(nonexistent)

    def test_ensure_bitwig_dir_not_a_dir_raises(self, tmp_path):
        """Test ensure_bitwig_dir() gdy ścieżka wskazuje plik → InvalidPathError."""
        from setka_common.exceptions import InvalidPathError

        import pytest

        file_path = tmp_path / "not_a_dir.mkv"
        file_path.touch()

        with pytest.raises(InvalidPathError):
            RecordingStructureManager.ensure_bitwig_dir(file_path)


class TestFindAnalysisAudioSources:
    """Testy dla resolvera źródeł audio do analizy (Unit 2)."""

    def test_only_mixed_master(self, tmp_path):
        """Tylko mixed/master.wav → zwraca [master.wav]."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        master = mixed_dir / "master.wav"
        master.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert result == [master]

    def test_mixed_master_plus_stems(self, tmp_path):
        """mixed/master.wav + mixed/stems/{a,b}.wav → zwraca wszystkie trzy."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()

        master = mixed_dir / "master.wav"
        master.touch()
        stem_a = stems_dir / "bass.wav"
        stem_a.touch()
        stem_b = stems_dir / "guitar.wav"
        stem_b.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert master in result
        assert stem_a in result
        assert stem_b in result
        assert len(result) == 3

    def test_mixed_no_audio_falls_back_to_extracted(self, tmp_path):
        """mixed/ istnieje ale bez plików audio → fallback do extracted/."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        # Tworzymy tylko podkatalog stems/ bez plików audio
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()

        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()
        ext_audio = extracted_dir / "source.m4a"
        ext_audio.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert result == [ext_audio]

    def test_no_mixed_falls_back_to_extracted(self, tmp_path):
        """mixed/ nieobecne, extracted/ ma pliki → fallback do extracted/."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()
        ext_audio = extracted_dir / "source.m4a"
        ext_audio.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert result == [ext_audio]

    def test_both_empty_returns_empty_list(self, tmp_path):
        """Oba katalogi puste/nieobecne → zwraca [] bez wyjątku."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert result == []

    def test_mixed_extensions_all_audio_caught(self, tmp_path):
        """Mieszane rozszerzenia — wszystkie audio złapane, nie-audio pominięte."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()

        wav_file = mixed_dir / "master.wav"
        wav_file.touch()
        flac_file = mixed_dir / "master2.flac"
        flac_file.touch()
        m4a_file = stems_dir / "stem.m4a"
        m4a_file.touch()
        txt_file = mixed_dir / "readme.txt"
        txt_file.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert wav_file in result
        assert flac_file in result
        assert m4a_file in result
        assert txt_file not in result

    def test_collision_raises_error(self, tmp_path):
        """Kolizja nazwy (mixed/master.wav + mixed/stems/master.wav) → wyjątek z opisem."""
        import pytest

        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()

        master_mixed = mixed_dir / "master.wav"
        master_mixed.touch()
        master_stem = stems_dir / "master.wav"
        master_stem.touch()

        with pytest.raises(ValueError, match="master"):
            RecordingStructureManager.find_analysis_audio_sources(recording_dir)

    def test_deterministic_ordering(self, tmp_path):
        """Kolejność wyników jest deterministyczna (sort case-insensitive)."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()

        # Nazwy ze zróżnicowaną wielkością liter
        file_z = mixed_dir / "Zebra.wav"
        file_z.touch()
        file_a = stems_dir / "apple.wav"
        file_a.touch()
        file_m = mixed_dir / "Master.wav"
        file_m.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)
        result_names = [f.name.lower() for f in result]

        assert result_names == sorted(result_names)


class TestFindBitwigSampleSources:
    """Testy dla find_bitwig_sample_sources (Unit 2)."""

    def test_bitwig_samples_flat(self, tmp_path):
        """bitwig/samples/ z wav → zwraca te pliki."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        samples_dir = recording_dir / "bitwig" / "samples"
        samples_dir.mkdir(parents=True)
        a = samples_dir / "m_s-24.wav"
        a.touch()
        b = samples_dir / "track 4+git-24.wav"
        b.touch()

        result = RecordingStructureManager.find_bitwig_sample_sources(recording_dir)

        assert a in result
        assert b in result
        assert len(result) == 2

    def test_bitwig_samples_nested_one_level(self, tmp_path):
        """bitwig/<proj>/samples/ (jeden poziom zagnieżdżenia) jest wykrywane."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        samples_dir = recording_dir / "bitwig" / "MyProject" / "samples"
        samples_dir.mkdir(parents=True)
        wav = samples_dir / "m_s-24.wav"
        wav.touch()

        result = RecordingStructureManager.find_bitwig_sample_sources(recording_dir)

        assert wav in result

    def test_bitwig_flat_takes_priority_over_nested(self, tmp_path):
        """bitwig/samples/ (flat) wykryte zamiast bitwig/*/samples/ gdy oba istnieją."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        # flat samples dir
        flat_samples = recording_dir / "bitwig" / "samples"
        flat_samples.mkdir(parents=True)
        flat_wav = flat_samples / "flat.wav"
        flat_wav.touch()
        # nested samples dir
        nested_samples = recording_dir / "bitwig" / "proj" / "samples"
        nested_samples.mkdir(parents=True)
        nested_wav = nested_samples / "nested.wav"
        nested_wav.touch()

        result = RecordingStructureManager.find_bitwig_sample_sources(recording_dir)

        # flat bierze priorytet
        assert flat_wav in result
        assert nested_wav not in result

    def test_no_bitwig_dir_returns_empty(self, tmp_path):
        """Brak bitwig/ → zwraca []."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()

        result = RecordingStructureManager.find_bitwig_sample_sources(recording_dir)

        assert result == []

    def test_bitwig_exists_no_samples_dir_returns_empty(self, tmp_path):
        """bitwig/ istnieje ale bez samples/ → zwraca []."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        bitwig_dir = recording_dir / "bitwig"
        bitwig_dir.mkdir()

        result = RecordingStructureManager.find_bitwig_sample_sources(recording_dir)

        assert result == []

    def test_bitwig_samples_empty_dir_returns_empty(self, tmp_path):
        """bitwig/samples/ istnieje ale puste → zwraca []."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        samples_dir = recording_dir / "bitwig" / "samples"
        samples_dir.mkdir(parents=True)

        result = RecordingStructureManager.find_bitwig_sample_sources(recording_dir)

        assert result == []

    def test_non_audio_files_ignored(self, tmp_path):
        """Pliki nie-audio w bitwig/samples/ są pomijane."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        samples_dir = recording_dir / "bitwig" / "samples"
        samples_dir.mkdir(parents=True)
        wav = samples_dir / "track.wav"
        wav.touch()
        bwproject = samples_dir / "project.bwproject"
        bwproject.touch()

        result = RecordingStructureManager.find_bitwig_sample_sources(recording_dir)

        assert wav in result
        assert bwproject not in result
        assert len(result) == 1


class TestFindAnalysisAudioSourcesHybrid:
    """Testy hybrydowego resolvera (Unit 2) — tiery master + stems|bitwig."""

    def test_master_plus_mixed_stems(self, tmp_path):
        """mixed/master.wav + mixed/stems/{a,b}.wav → master + 2 stemy (bitwig ignorowany)."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()
        master = mixed_dir / "master.wav"
        master.touch()
        stem_a = stems_dir / "bass.wav"
        stem_a.touch()
        stem_b = stems_dir / "guitar.wav"
        stem_b.touch()
        # bitwig/samples/ — powinien być ignorowany gdy mixed/stems/ niepuste
        bitwig_samples = recording_dir / "bitwig" / "samples"
        bitwig_samples.mkdir(parents=True)
        (bitwig_samples / "ignored.wav").touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert master in result
        assert stem_a in result
        assert stem_b in result
        assert len(result) == 3

    def test_master_plus_bitwig_stems_when_no_mixed_stems(self, tmp_path):
        """mixed/master.wav + brak/puste mixed/stems/ + bitwig/samples/ z 3 wav → master + 3 stemy."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        # stems/ puste (nie istnieje)
        master = mixed_dir / "master.wav"
        master.touch()
        bitwig_samples = recording_dir / "bitwig" / "samples"
        bitwig_samples.mkdir(parents=True)
        b1 = bitwig_samples / "m_s-24.wav"
        b1.touch()
        b2 = bitwig_samples / "track 4+git-24.wav"
        b2.touch()
        b3 = bitwig_samples / "track 5_6+mic+freak-24.wav"
        b3.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert master in result
        assert b1 in result
        assert b2 in result
        assert b3 in result
        assert len(result) == 4

    def test_only_bitwig_no_mixed(self, tmp_path):
        """Brak mixed/, bitwig/samples/ z N wav → N źródeł (master-tier pusty)."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        bitwig_samples = recording_dir / "bitwig" / "samples"
        bitwig_samples.mkdir(parents=True)
        b1 = bitwig_samples / "m_s-24.wav"
        b1.touch()
        b2 = bitwig_samples / "track 1-25.wav"
        b2.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert b1 in result
        assert b2 in result
        assert len(result) == 2

    def test_bitwig_nested_project_detected(self, tmp_path):
        """bitwig/<proj>/samples/ (jeden poziom zagnieżdżenia) wykryte jako fallback stemów."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        master = mixed_dir / "master.wav"
        master.touch()
        # nested bitwig project
        nested_samples = recording_dir / "bitwig" / "LiveSession" / "samples"
        nested_samples.mkdir(parents=True)
        stem = nested_samples / "m_s-24.wav"
        stem.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert master in result
        assert stem in result
        assert len(result) == 2

    def test_mixed_stems_wins_over_bitwig(self, tmp_path):
        """mixed/stems/ niepuste → bitwig/samples/ nie jest odpytywany (fallback nie odpala)."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()
        master = mixed_dir / "master.wav"
        master.touch()
        mixed_stem = stems_dir / "polished.wav"
        mixed_stem.touch()
        # bitwig istnieje i ma pliki — ale stems/ wygrywa
        bitwig_samples = recording_dir / "bitwig" / "samples"
        bitwig_samples.mkdir(parents=True)
        bitwig_wav = bitwig_samples / "raw.wav"
        bitwig_wav.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert master in result
        assert mixed_stem in result
        assert bitwig_wav not in result
        assert len(result) == 2

    def test_fallback_extracted_when_no_mixed_no_bitwig(self, tmp_path):
        """Brak mixed/ i bitwig/, extracted/ ma pliki → fallback extracted/ (zgodność wstecz)."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        extracted_dir = recording_dir / "extracted"
        extracted_dir.mkdir()
        ext_audio = extracted_dir / "source.m4a"
        ext_audio.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert result == [ext_audio]

    def test_all_empty_returns_empty_list(self, tmp_path):
        """Wszystko puste/nieobecne → [] bez wyjątku."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert result == []

    def test_collision_via_sanitize_raises_value_error(self, tmp_path):
        """Dwa źródła o kolidujących sanityzowanych nazwach → ValueError z oboma plikami."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        bitwig_samples = recording_dir / "bitwig" / "samples"
        bitwig_samples.mkdir(parents=True)
        # Oba sanityzują się do "track_1"
        f1 = bitwig_samples / "track 1-24.wav"
        f1.touch()
        f2 = bitwig_samples / "track_1.wav"
        f2.touch()

        with pytest.raises(ValueError):
            RecordingStructureManager.find_analysis_audio_sources(recording_dir)

    def test_collision_error_mentions_both_files(self, tmp_path):
        """ValueError z collision-check wymienia oba kolidujące pliki."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        bitwig_samples = recording_dir / "bitwig" / "samples"
        bitwig_samples.mkdir(parents=True)
        f1 = bitwig_samples / "track 1-24.wav"
        f1.touch()
        f2 = bitwig_samples / "track_1.wav"
        f2.touch()

        with pytest.raises(ValueError) as exc_info:
            RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        error_msg = str(exc_info.value)
        # Błąd musi wymienić sanityzowaną etykietę kolizji
        assert "track_1" in error_msg

    def test_deterministic_order_with_bitwig(self, tmp_path):
        """Kolejność wyników deterministyczna (sort case-insensitive) przy źródłach bitwig."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        bitwig_samples = recording_dir / "bitwig" / "samples"
        bitwig_samples.mkdir(parents=True)
        # Nazwy ze zróżnicowaną wielkością liter
        (bitwig_samples / "Zebra-24.wav").touch()
        (bitwig_samples / "apple-24.wav").touch()
        (bitwig_samples / "Master-24.wav").touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)
        result_names = [f.name.lower() for f in result]

        assert result_names == sorted(result_names)

    def test_empty_mixed_stems_uses_bitwig(self, tmp_path):
        """mixed/stems/ ISTNIEJE ale pusta → używa bitwig/samples/ (fallback odpala)."""
        recording_dir = tmp_path / "recording"
        recording_dir.mkdir()
        mixed_dir = recording_dir / "mixed"
        mixed_dir.mkdir()
        stems_dir = mixed_dir / "stems"
        stems_dir.mkdir()
        # stems/ istnieje ale puste — fallback do bitwig
        master = mixed_dir / "master.wav"
        master.touch()
        bitwig_samples = recording_dir / "bitwig" / "samples"
        bitwig_samples.mkdir(parents=True)
        bitwig_wav = bitwig_samples / "raw.wav"
        bitwig_wav.touch()

        result = RecordingStructureManager.find_analysis_audio_sources(recording_dir)

        assert master in result
        assert bitwig_wav in result
        assert len(result) == 2


class TestSanitizeStemName:
    """Testy dla funkcji sanitize_stem_name (Unit 1).

    Mapowania realnych nazw z nagrania (bitwig/samples/):
    - "m_s-24"               → "m_s"
    - "track 1-25"           → "track_1"
    - "track 2-26"           → "track_2"
    - "track 3-25"           → "track_3"
    - "track 4+git-24"       → "track_4_git"
    - "track 5_6+mic+freak-24" → "track_5_6_mic_freak"
    - "master"               → "master"
    """

    @pytest.mark.parametrize(
        "input_name, expected",
        [
            # Realne nazwy z nagrania (surowy stem Bitwiga)
            ("m_s-24", "m_s"),
            ("track 1-25", "track_1"),
            ("track 2-26", "track_2"),
            ("track 3-25", "track_3"),
            ("track 4+git-24", "track_4_git"),
            ("track 5_6+mic+freak-24", "track_5_6_mic_freak"),
            # Master — brak sufiksu liczbowego, bez zmian
            ("master", "master"),
            # Brak sufiksu -NN — tylko normalizacja separatorów
            ("bass+guitar", "bass_guitar"),
            ("my track/stem", "my_track_stem"),
            (r"path\to\stem", "path_to_stem"),
            # Zachowanie wielkości liter (NIE lower-case)
            ("MyTrack-24", "MyTrack"),
            ("DRUMS-10", "DRUMS"),
            # Rozszerzenie .wav w wejściu — zdejmij
            ("master.wav", "master"),
            ("track 4+git-24.wav", "track_4_git"),
            ("m_s-24.wav", "m_s"),
            # Wielokrotne podkreślniki → scalone
            ("track__double-24", "track_double"),
            # Brzegowe podkreślniki → przycięte
            (" leading space-24", "leading_space"),
            # Sufiks -NN z wielocyfrową liczbą
            ("stem-100", "stem"),
            ("stem-9", "stem"),
        ],
    )
    def test_real_name_mappings(self, input_name, expected):
        """Test tabelaryczny: realne nazwy z nagrania mapują się na oczekiwane etykiety."""
        assert sanitize_stem_name(input_name) == expected

    def test_idempotent_on_real_names(self):
        """sanitize(sanitize(x)) == sanitize(x) dla realnych nazw."""
        raw_names = [
            "m_s-24",
            "track 4+git-24",
            "track 5_6+mic+freak-24",
            "master",
            "DRUMS-10",
        ]
        for name in raw_names:
            once = sanitize_stem_name(name)
            twice = sanitize_stem_name(once)
            assert once == twice, f"Nie idempotentne dla '{name}': {once!r} → {twice!r}"

    def test_idempotent_on_already_clean_names(self):
        """sanitize(x) == x gdy wejście jest już czyste."""
        clean_names = ["master", "m_s", "track_1", "track_4_git", "DRUMS"]
        for name in clean_names:
            assert sanitize_stem_name(name) == name, (
                f"Czysta nazwa '{name}' zmodyfikowana przez sanitize"
            )

    def test_error_on_pure_separator_input(self):
        """Wejście złożone z samych znaków specjalnych → ValueError."""
        with pytest.raises(ValueError, match="sanitize_stem_name"):
            sanitize_stem_name("+/\\")

    def test_error_on_empty_string(self):
        """Pusty string → ValueError z czytelnym komunikatem."""
        with pytest.raises(ValueError, match="sanitize_stem_name"):
            sanitize_stem_name("")

    def test_error_on_only_spaces(self):
        """Sama spacja/whitespace po normalizacji → ValueError."""
        with pytest.raises(ValueError, match="sanitize_stem_name"):
            sanitize_stem_name("   ")

    def test_preserves_case(self):
        """Zachowuje wielkość liter — NIE robi lower-case."""
        assert sanitize_stem_name("MyTrack-24") == "MyTrack"
        assert sanitize_stem_name("DRUMS") == "DRUMS"

    def test_dot_in_middle_of_name_treated_as_extension(self):
        """Nazwa pliku z kropką — Path.stem zdejmuje sufiks, nie środkową kropkę.

        Np. 'track.stem-24.wav' → Path.stem daje 'track.stem-24' → sanitize daje 'track.stem'.
        To zachowanie jest akceptowalne (nazwy z kropką w środku są rzadkie w Bitwigu).
        """
        # 'track-24.wav' — typowe: zdejmuje .wav, potem usuwa -24
        assert sanitize_stem_name("track-24.wav") == "track"
