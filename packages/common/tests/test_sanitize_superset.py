"""
ABOUTME: Regression guard that the canonical sanitize_filename is a byte-stable superset
ABOUTME: of obsession's stronger rules, so unifying later renames no existing extracted files.
"""

import re

from setka_common.utils.files import sanitize_filename


def _obsession_sanitize_filename(filename: str) -> str:
    """Verbatim copy of obsession's current ``core/extractor.py`` sanitize_filename.

    Kept in this test as the frozen reference implementation. The canonical
    ``setka_common`` version must produce byte-identical output on real source
    names so that adopting it in obsession (Phase 5) does not rename any file
    already on disk.
    """
    sanitized = re.sub(r'[/\\:*?"<>|]', "_", filename)
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip("_")
    if not sanitized:
        sanitized = "source"
    return sanitized


# Real-ish OBS source names, including PulseAudio capture labels, camera names,
# browser sources, and names with characters that differ between the two impls.
REAL_OBS_SOURCE_NAMES = [
    "Przechwytywanie wejścia dźwięku (PulseAudio)",
    "Przechwytywanie wyjścia dźwięku (PulseAudio)",
    "Camera1",
    "Camera 2",
    "Kamera/Główna",
    "Window Capture (Xcomposite)",
    "Audio Output Capture",
    "Mic/Aux",
    "Display Capture",
    "Browser Source",
    "Scene: Intro/Outro",
    "track 4+git",
    "stem*name?bad<chars>",
    'quote"name',
    "pipe|name",
    "back\\slash",
    "colon:name",
    "multiple___underscores",
    "_leading_and_trailing_",
    "***",
    "main_audio",
    "źródło ekranu",
]


class TestSanitizeSupersetByteStability:
    """The canonical sanitize must match obsession's impl byte-for-byte on real names."""

    def test_byte_identical_to_obsession_on_real_source_names(self):
        mismatches = []
        for name in REAL_OBS_SOURCE_NAMES:
            canonical = sanitize_filename(name)
            obsession = _obsession_sanitize_filename(name)
            if canonical != obsession:
                mismatches.append((name, canonical, obsession))

        assert not mismatches, (
            "Canonical sanitize_filename diverges from obsession's impl "
            f"(would rename existing files): {mismatches}"
        )

    def test_replaces_path_separators(self):
        assert sanitize_filename("Kamera/Główna") == "Kamera_Główna"
        assert sanitize_filename("back\\slash") == "back_slash"

    def test_collapses_repeated_underscores(self):
        assert sanitize_filename("multiple___underscores") == "multiple_underscores"

    def test_non_empty_fallback_to_source(self):
        assert sanitize_filename("***") == "source"
        assert sanitize_filename("///") == "source"

    def test_strips_surrounding_underscores(self):
        assert sanitize_filename("_leading_and_trailing_") == "leading_and_trailing"
