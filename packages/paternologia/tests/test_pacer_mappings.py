# ABOUTME: Unit tests for Pacer MIDI mappings.
# ABOUTME: Tests device channel mapping and action to MIDI conversion.

import pytest

from paternologia.models import Action, ActionType, Device
from paternologia.pacer.mappings import (
    action_to_midi,
    build_device_channel_map,
    get_device_channel,
    note_to_midi,
    pattern_to_program,
)
from paternologia.pacer import constants as c


class TestBuildDeviceChannelMap:
    """Tests for device channel map building."""

    def test_build_from_devices(self):
        """Builds map from Device.midi_channel."""
        devices = [
            Device(id="boss", name="Boss", midi_channel=0),
            Device(id="ms", name="M:S", midi_channel=1),
            Device(id="freak", name="Freak", midi_channel=2),
        ]
        channel_map = build_device_channel_map(devices)

        assert channel_map["boss"] == 0
        assert channel_map["ms"] == 1
        assert channel_map["freak"] == 2

    def test_empty_devices(self):
        """Empty device list gives empty map."""
        assert build_device_channel_map([]) == {}


class TestGetDeviceChannel:
    """Tests for device channel lookup."""

    def test_known_device(self):
        """Returns channel for known device."""
        channel_map = {"boss": 5, "ms": 10}
        assert get_device_channel("boss", channel_map) == 5
        assert get_device_channel("ms", channel_map) == 10

    def test_unknown_device_fallback(self):
        """Returns 0 for unknown device."""
        channel_map = {"boss": 5}
        assert get_device_channel("unknown", channel_map) == 0


class TestPatternToProgram:
    """Tests for pattern ID conversion."""

    def test_integer_passthrough(self):
        """Integer values pass through unchanged."""
        assert pattern_to_program(42) == 42

    def test_pattern_a01(self):
        """A01 converts to 0."""
        assert pattern_to_program("A01") == 0

    def test_pattern_a16(self):
        """A16 converts to 15."""
        assert pattern_to_program("A16") == 15

    def test_pattern_b01(self):
        """B01 converts to 16."""
        assert pattern_to_program("B01") == 16

    def test_pattern_f16(self):
        """F16 converts to 95."""
        assert pattern_to_program("F16") == 95

    def test_lowercase_pattern(self):
        """Lowercase pattern letters work."""
        assert pattern_to_program("a01") == 0
        assert pattern_to_program("b02") == 17

    def test_invalid_pattern_fallback(self):
        """Invalid patterns return 0."""
        assert pattern_to_program("invalid") == 0
        assert pattern_to_program("X99") == 0
        assert pattern_to_program(None) == 0


class TestActionToMidiPreset:
    """Tests for PRESET action conversion."""

    def test_preset_basic(self):
        """PRESET action converts to MSG_SW_PRG_BANK with bank=0."""
        action = Action(device="boss", type=ActionType.PRESET, value=5)
        channel_map = {"boss": 0}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert msg_type == c.MSG_SW_PRG_BANK
        assert channel == 0
        assert data1 == 5  # program (0-127)
        assert data2 == 0  # bank LSB
        assert data3 == 0  # bank MSB

    def test_preset_different_channel(self):
        """PRESET action on different channel."""
        action = Action(device="boss", type=ActionType.PRESET, value=10)
        channel_map = {"boss": 3}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert channel == 3
        assert data1 == 10  # program (0-127)
        assert data2 == 0  # bank LSB
        assert data3 == 0  # bank MSB


class TestActionToMidiPattern:
    """Tests for PATTERN action conversion."""

    def test_pattern_string(self):
        """PATTERN with string value."""
        action = Action(device="ms", type=ActionType.PATTERN, value="A02")
        channel_map = {"ms": 1}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert msg_type == c.MSG_SW_PRG_STEP
        assert channel == 1
        assert data1 == 0  # unused
        assert data2 == 1  # A02 = 1
        assert data3 == 1  # same = immediate

    def test_pattern_integer(self):
        """PATTERN with integer value."""
        action = Action(device="ms", type=ActionType.PATTERN, value=50)
        channel_map = {"ms": 1}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert data1 == 0  # unused
        assert data2 == 50  # start (program)
        assert data3 == 50  # end (same = immediate)


class TestActionToMidiCC:
    """Tests for CC action conversion."""

    def test_cc_action(self):
        """CC action converts to MSG_SW_MIDI_CC (trigger down=127, up=0)."""
        action = Action(device="boss", type=ActionType.CC, cc=74, value=127)
        channel_map = {"boss": 0}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert msg_type == c.MSG_SW_MIDI_CC
        assert channel == 0
        assert data1 == 74  # CC number
        assert data2 == 127  # down (naciśnięcie)
        assert data3 == 0  # up (puszczenie)

    def test_cc_different_channel(self):
        """CC action on different channel."""
        action = Action(device="freak", type=ActionType.CC, cc=1, value=64)
        channel_map = {"freak": 5}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert msg_type == c.MSG_SW_MIDI_CC
        assert channel == 5
        assert data2 == 64  # down (naciśnięcie)
        assert data3 == 0  # up (puszczenie)


class TestActionToMidiUnknownDevice:
    """Tests for unknown device handling."""

    def test_unknown_device_channel_zero(self):
        """Unknown device defaults to channel 0."""
        action = Action(device="unknown", type=ActionType.PRESET, value=1)
        channel_map = {"boss": 5}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert channel == 0


class TestNoteToMidi:
    """Tests for musical notation to MIDI note number conversion."""

    def test_middle_c(self):
        """C4 (middle C) converts to 60."""
        assert note_to_midi("C4") == 60

    def test_a4_concert_pitch(self):
        """A4 (concert pitch) converts to 69."""
        assert note_to_midi("A4") == 69

    def test_lowest_note(self):
        """C-1 converts to 0."""
        assert note_to_midi("C-1") == 0

    def test_highest_note(self):
        """G9 converts to 127."""
        assert note_to_midi("G9") == 127

    def test_sharp_notes(self):
        """Sharp notes convert correctly."""
        assert note_to_midi("C#4") == 61
        assert note_to_midi("F#3") == 54
        assert note_to_midi("G#5") == 80

    def test_flat_notes(self):
        """Flat notes convert correctly."""
        assert note_to_midi("Db4") == 61  # same as C#4
        assert note_to_midi("Bb3") == 58
        assert note_to_midi("Eb5") == 75

    def test_lowercase(self):
        """Lowercase note names work."""
        assert note_to_midi("c4") == 60
        assert note_to_midi("f#3") == 54
        assert note_to_midi("bb3") == 58

    def test_integer_passthrough(self):
        """Integer values pass through unchanged."""
        assert note_to_midi(60) == 60
        assert note_to_midi(127) == 127

    def test_numeric_string(self):
        """Numeric strings convert to integers."""
        assert note_to_midi("60") == 60
        assert note_to_midi("127") == 127

    def test_invalid_note_raises(self):
        """Invalid note notation raises ValueError."""
        with pytest.raises(ValueError):
            note_to_midi("X4")
        with pytest.raises(ValueError):
            note_to_midi("C")
        with pytest.raises(ValueError):
            note_to_midi("invalid")

    def test_out_of_range_raises(self):
        """Out of range notes raise ValueError."""
        with pytest.raises(ValueError):
            note_to_midi("C10")  # > 127
        with pytest.raises(ValueError):
            note_to_midi(-1)
        with pytest.raises(ValueError):
            note_to_midi(128)


class TestActionToMidiNote:
    """Tests for NOTE action conversion."""

    def test_note_basic(self):
        """NOTE action converts to MSG_SW_NOTE."""
        action = Action(device="freak", type=ActionType.NOTE, note="C4", velocity=100)
        channel_map = {"freak": 2}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert msg_type == c.MSG_SW_NOTE
        assert channel == 2
        assert data1 == 60  # C4
        assert data2 == 100  # velocity
        assert data3 == 0  # unused

    def test_note_sharp(self):
        """NOTE action with sharp note."""
        action = Action(device="freak", type=ActionType.NOTE, note="F#3", velocity=80)
        channel_map = {"freak": 2}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert data1 == 54  # F#3
        assert data2 == 80

    def test_note_default_velocity(self):
        """NOTE action uses default velocity when not specified."""
        action = Action(device="freak", type=ActionType.NOTE, note="A4")
        channel_map = {"freak": 2}
        msg_type, channel, data1, data2, data3 = action_to_midi(action, channel_map)

        assert data1 == 69  # A4
        assert data2 == 100  # default velocity
