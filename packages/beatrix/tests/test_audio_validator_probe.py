# ABOUTME: Tests for AudioValidator decode-probe fail-fast validation (Unit 2.3)
# ABOUTME: A file passing extension/existence checks but undecodable must be rejected

"""Decode-probe and message-consistency tests for AudioValidator."""

import wave

import pytest

from beatrix import AudioValidator
from beatrix.exceptions import AudioValidationError


def _write_real_wav(path, sample_rate=22050, n_samples=2205):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_samples)
    return path


class TestDecodeProbe:
    """Unit 2.3: a corrupt file with a valid extension must be rejected."""

    def test_corrupt_file_with_audio_extension_is_rejected(self, tmp_path):
        """A .wav full of garbage passes existence/extension but must fail probe."""
        corrupt = tmp_path / "broken.wav"
        corrupt.write_bytes(b"this is not a real wav file at all")

        validator = AudioValidator()
        with pytest.raises(AudioValidationError):
            validator.validate_audio_file(corrupt)

    def test_real_wav_passes_probe(self, tmp_path):
        good = _write_real_wav(tmp_path / "good.wav")
        validator = AudioValidator()
        # Must not raise and should return the path.
        assert validator.validate_audio_file(good) == good

    def test_detect_main_audio_rejects_corrupt_single_file(self, tmp_path):
        """Fail-fast: the only audio file present is undecodable."""
        corrupt = tmp_path / "only.wav"
        corrupt.write_bytes(b"garbage bytes, not audio")

        validator = AudioValidator()
        with pytest.raises(AudioValidationError):
            validator.detect_main_audio(tmp_path)

    def test_detect_main_audio_accepts_real_single_file(self, tmp_path):
        good = _write_real_wav(tmp_path / "only.wav")
        validator = AudioValidator()
        assert validator.detect_main_audio(tmp_path) == good

    def test_specified_corrupt_file_is_rejected(self, tmp_path):
        _write_real_wav(tmp_path / "good.wav")
        corrupt = tmp_path / "bad.wav"
        corrupt.write_bytes(b"not audio")

        validator = AudioValidator()
        with pytest.raises(AudioValidationError):
            validator.detect_main_audio(tmp_path, "bad.wav")


class TestMessageConsistency:
    """Unit 2.3: validation messages are uniformly Polish (no EN/PL mix)."""

    def test_specified_not_found_message_is_polish(self, tmp_path):
        _write_real_wav(tmp_path / "exists.wav")
        validator = AudioValidator()
        with pytest.raises(ValueError, match="Nie znaleziono"):
            validator.detect_main_audio(tmp_path, "missing.mp3")

    def test_specified_invalid_format_message_is_polish(self, tmp_path):
        (tmp_path / "document.txt").touch()
        validator = AudioValidator()
        with pytest.raises(ValueError, match="nieprawidłowym plikiem audio"):
            validator.detect_main_audio(tmp_path, "document.txt")
