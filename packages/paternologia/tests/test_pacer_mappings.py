# ABOUTME: Unit tests for Pacer MIDI mappings.
# ABOUTME: Tests device channel mapping and action to MIDI conversion.

import pytest

from paternologia.models import Action, ActionType, Device, PacerConfig
from paternologia.pacer.mappings import (
    action_to_midi,
    action_to_midi_config,
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

    def test_cc_release_same_device_sends_down_value_on_release(self):
        """Urządzenie z cc_release_same: puszczenie wysyła tę samą wartość.

        GP-50 wybiera patch przez CC0 — up=0 cofałby patch na 00.
        """
        action = Action(device="gp50", type=ActionType.CC, cc=0, value=12)
        msg_type, channel, data1, data2, data3 = action_to_midi(
            action, {"gp50": 5}, cc_release_same_devices={"gp50"}
        )

        assert msg_type == c.MSG_SW_MIDI_CC
        assert channel == 5
        assert data1 == 0
        assert data2 == 12  # down
        assert data3 == 12  # up = down

    def test_cc_release_same_other_device_keeps_up_zero(self):
        """Urządzenie spoza cc_release_same dalej wysyła up=0 (RC-600 MOMENT)."""
        action = Action(device="boss", type=ActionType.CC, cc=1, value=127)
        _, _, _, data2, data3 = action_to_midi(
            action, {"boss": 13, "gp50": 5}, cc_release_same_devices={"gp50"}
        )

        assert data2 == 127
        assert data3 == 0


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


RIG_CHANNELS = {"boss": 13, "ms": 14, "freak": 1}


class TestActionToMidiConfig:
    """Mapowanie akcji on_load na wpis M CFG (typ, kanał, data1-3)."""

    def _map(self, action: Action, config: PacerConfig | None = None):
        return action_to_midi_config(action, RIG_CHANNELS, config or PacerConfig())

    def test_cc_maps_to_load_cc(self):
        action = Action(device="boss", type=ActionType.CC, cc=40, value=99)
        assert self._map(action) == (c.MSG_LOAD_CC, 13, 40, 99, 0)

    def test_preset_maps_to_prg_bank_without_display_offset(self):
        """Wartość surowa z YAML, bez preset_display_offset."""
        action = Action(device="freak", type=ActionType.PRESET, value=67)
        assert self._map(action) == (c.MSG_SW_PRG_BANK, 1, 67, 0, 0)

    def test_preset_above_127_uses_same_split_as_buttons(self):
        """Ten sam PC co z przycisku (action_to_midi): prog % 128, MSB = // 128."""
        action = Action(device="freak", type=ActionType.PRESET, value=200)
        _, ch, prog, lsb, msb = action_to_midi(action, RIG_CHANNELS)
        assert self._map(action) == (c.MSG_SW_PRG_BANK, ch, prog, lsb, msb)
        assert (prog, msb) == (72, 1)

    def test_pattern_maps_to_prg_bank(self):
        """M CFG nie ma PRG_STEP — pattern idzie jako Program Change."""
        action = Action(device="ms", type=ActionType.PATTERN, value="D01")
        assert self._map(action) == (c.MSG_SW_PRG_BANK, 14, 48, 0, 0)

    def test_note_maps_to_note(self):
        action = Action(device="freak", type=ActionType.NOTE, note="C4", velocity=90)
        assert self._map(action) == (c.MSG_SW_NOTE, 1, 60, 90, 0)

    def test_note_default_velocity(self):
        action = Action(device="freak", type=ActionType.NOTE, note=62)
        assert self._map(action) == (c.MSG_SW_NOTE, 1, 62, 100, 0)

    def test_unknown_device_fails_fast(self):
        action = Action(device="nope", type=ActionType.PRESET, value=1)
        with pytest.raises(ValueError, match="nope"):
            self._map(action)

    @pytest.mark.parametrize("note", [94, 93])
    def test_note_equal_to_obs_trigger_is_rejected(self, note):
        """Nuta triggera OBS w on_load uruchomiłaby nagranie przy zmianie presetu."""
        config = PacerConfig(
            record_trigger_channel=0, record_start_note=94, record_stop_note=93
        )
        action = Action(device="freak", type=ActionType.NOTE, note=note)
        with pytest.raises(ValueError, match="OBS"):
            self._map(action, config)

    def test_note_on_other_channel_than_obs_trigger_is_allowed(self):
        config = PacerConfig(
            record_trigger_channel=0, record_start_note=94, record_stop_note=93
        )
        action = Action(device="ms", type=ActionType.NOTE, note=94)
        assert self._map(action, config) == (c.MSG_SW_NOTE, 14, 94, 100, 0)


class TestActionToMidiConfigFailFast:
    """Wpis on_load wysyła się przy każdym załadowaniu — błędna akcja to błąd, nie PC/CC 0."""

    def _map(self, action, channels=None, config=None):
        return action_to_midi_config(
            action, channels or RIG_CHANNELS, config or PacerConfig()
        )

    def test_cc_without_controller_is_rejected(self):
        action = Action(device="boss", type=ActionType.CC, value=99)
        with pytest.raises(ValueError, match="CC"):
            self._map(action)

    @pytest.mark.parametrize("value", ["G01", "A17", "A00", "xyz", None])
    def test_invalid_pattern_is_rejected(self, value):
        action = Action(device="ms", type=ActionType.PATTERN, value=value)
        with pytest.raises(ValueError, match="pattern"):
            self._map(action)

    @pytest.mark.parametrize("value", ["A01", "a1", "0", 0])
    def test_pattern_a01_is_program_zero(self, value):
        action = Action(device="ms", type=ActionType.PATTERN, value=value)
        assert self._map(action)[2] == 0

    def test_preset_without_number_is_rejected(self):
        action = Action(device="freak", type=ActionType.PRESET, value=None)
        with pytest.raises(ValueError, match="preset"):
            self._map(action)

    def test_obs_trigger_note_on_global_channel_is_rejected(self):
        """Kanał 0 = Global Pacera — może być kanałem triggera OBS."""
        config = PacerConfig(
            record_trigger_channel=0, record_start_note=94, record_stop_note=93
        )
        action = Action(device="glob", type=ActionType.NOTE, note=94)
        with pytest.raises(ValueError, match="OBS"):
            self._map(action, {"glob": 0}, config)


class TestPresetViaCc:
    """PRESET na urządzeniu z preset_cc to CC (np. GP-50 patch = CC0), nie PC."""

    PRESET_CC = {"gp50": 0}

    def test_button_preset_is_cc_trigger_with_up_equal_down(self):
        """Puszczenie przycisku nie może wrócić do patcha 00."""
        action = Action(device="gp50", type=ActionType.PRESET, value=10)
        assert action_to_midi(
            action, {"gp50": 5}, preset_cc_devices=self.PRESET_CC
        ) == (c.MSG_SW_MIDI_CC, 5, 0, 10, 10)

    def test_button_preset_other_device_stays_program_change(self):
        action = Action(device="freak", type=ActionType.PRESET, value=10)
        msg_type = action_to_midi(
            action, {"freak": 1}, preset_cc_devices=self.PRESET_CC
        )[0]
        assert msg_type == c.MSG_SW_PRG_BANK

    def test_on_load_preset_is_load_cc(self):
        action = Action(device="gp50", type=ActionType.PRESET, value=10)
        assert action_to_midi_config(
            action, {"gp50": 5}, PacerConfig(), preset_cc_devices=self.PRESET_CC
        ) == (c.MSG_LOAD_CC, 5, 0, 10, 0)

    @pytest.mark.parametrize("mapper", ["button", "on_load"])
    def test_preset_above_cc_range_is_rejected(self, mapper):
        """Wartość CC to 0-127 — preset 128 nie ma reprezentacji."""
        action = Action(device="gp50", type=ActionType.PRESET, value=128)
        with pytest.raises(ValueError, match="0-127"):
            if mapper == "button":
                action_to_midi(action, {"gp50": 5}, preset_cc_devices=self.PRESET_CC)
            else:
                action_to_midi_config(
                    action,
                    {"gp50": 5},
                    PacerConfig(),
                    preset_cc_devices=self.PRESET_CC,
                )
