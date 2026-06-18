# ABOUTME: Tests for preset display-number conversion helpers (to_display/to_stored).
# ABOUTME: Verifies the hidden per-device offset round-trips and never touches patterns.

from paternologia.display import to_display, to_stored
from paternologia.models import ActionType, Device


def _device(offset: int = 0, action_types=None) -> Device:
    return Device(
        id="dev",
        name="DEV",
        preset_display_offset=offset,
        action_types=action_types or [ActionType.PRESET],
    )


class TestToDisplay:
    """Stored raw MIDI value → number shown on the device screen."""

    def test_applies_positive_offset(self):
        boss = _device(offset=1)
        assert to_display(100, boss) == 101

    def test_zero_offset_is_identity(self):
        ms = _device(offset=0)
        assert to_display(7, ms) == 7

    def test_pattern_string_unchanged(self):
        ms = _device(offset=0, action_types=[ActionType.PATTERN])
        assert to_display("F03", ms) == "F03"

    def test_none_unchanged(self):
        boss = _device(offset=1)
        assert to_display(None, boss) is None


class TestToStored:
    """Number entered in the UI (device screen) → raw MIDI value."""

    def test_removes_positive_offset(self):
        boss = _device(offset=1)
        assert to_stored(101, boss) == 100

    def test_zero_offset_is_identity(self):
        ms = _device(offset=0)
        assert to_stored(7, ms) == 7

    def test_pattern_string_unchanged(self):
        ms = _device(offset=0, action_types=[ActionType.PATTERN])
        assert to_stored("F03", ms) == "F03"

    def test_none_unchanged(self):
        boss = _device(offset=1)
        assert to_stored(None, boss) is None


class TestRoundTrip:
    """Display↔stored must be an exact identity, or values drift on every save."""

    def test_round_trip_over_range(self):
        boss = _device(offset=1)
        for raw in range(0, 128):
            assert to_stored(to_display(raw, boss), boss) == raw

    def test_round_trip_zero_offset(self):
        ms = _device(offset=0)
        for raw in range(0, 16):
            assert to_stored(to_display(raw, ms), ms) == raw
