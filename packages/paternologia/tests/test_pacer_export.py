# ABOUTME: Unit tests for Pacer SysEx export.
# ABOUTME: Tests export_song_to_syx function with various song configurations.

import pytest

from paternologia.models import (
    Action,
    ActionType,
    Device,
    PacerButton,
    PacerConfig,
    Song,
    SongMetadata,
)
from paternologia.pacer.export import export_song_to_syx
from paternologia.pacer.sysex import PacerSysExBuilder
from paternologia.pacer import constants as c


@pytest.fixture
def devices():
    """Sample devices for testing."""
    return [
        Device(id="boss", name="Boss RC-600", midi_channel=0),
        Device(id="ms", name="Elektron M:S", midi_channel=1),
        Device(id="freak", name="MicroFreak", midi_channel=2),
    ]


class TestExportBasic:
    """Basic export tests."""

    def test_export_minimal_song(self, devices):
        """Export minimal song (no buttons)."""
        song = Song(song=SongMetadata(id="test", name="TEST"), pacer=[])
        syx = export_song_to_syx(song, devices, "A1")

        assert len(syx) > 0
        assert syx[0] == c.SYSEX_START
        # Find first F7 (end of first message)
        assert c.SYSEX_END in syx

    def test_export_contains_preset_name(self, devices):
        """Exported data contains preset name."""
        song = Song(song=SongMetadata(id="test", name="TESTSONG"), pacer=[])
        syx = export_song_to_syx(song, devices, "A1")

        assert b"TESTSONG" in syx

    def test_export_different_preset(self, devices):
        """Different target preset affects output."""
        song = Song(song=SongMetadata(id="test", name="X"), pacer=[])
        syx_a1 = export_song_to_syx(song, devices, "A1")
        syx_b3 = export_song_to_syx(song, devices, "B3")

        # Different preset indices in the data
        assert syx_a1 != syx_b3


class TestExportWithButtons:
    """Export tests with PACER buttons."""

    def test_export_single_button(self, devices):
        """Export song with one button."""
        song = Song(
            song=SongMetadata(id="test", name="TEST"),
            pacer=[
                PacerButton(
                    name="Start",
                    actions=[Action(device="boss", type=ActionType.PRESET, value=1)],
                )
            ],
        )
        syx = export_song_to_syx(song, devices, "A1")

        # Message count: 1 name + 6 × (1 mode + 6 steps + 6 LED) + 16 M CFG = 95
        f0_count = syx.count(bytes([c.SYSEX_START]))
        assert f0_count == 95

    def test_export_multiple_actions(self, devices):
        """Export button with multiple actions."""
        song = Song(
            song=SongMetadata(id="test", name="TEST"),
            pacer=[
                PacerButton(
                    name="Complex",
                    actions=[
                        Action(device="boss", type=ActionType.PRESET, value=1),
                        Action(device="ms", type=ActionType.PATTERN, value="A01"),
                        Action(device="freak", type=ActionType.PRESET, value=65),
                    ],
                )
            ],
        )
        syx = export_song_to_syx(song, devices, "A1")

        # PRESET uses MSG_SW_PRG_BANK, PATTERN uses MSG_SW_PRG_STEP
        # 2 PRESET actions + 1 PATTERN action
        assert syx.count(bytes([c.MSG_SW_PRG_BANK])) >= 2
        assert syx.count(bytes([c.MSG_SW_PRG_STEP])) >= 1

    def test_export_cc_release_same_device_up_equals_down(self):
        """Urządzenie z cc_release_same eksportuje krok CC z up == down."""
        devices = [
            Device(id="gp50", name="GP-50", midi_channel=5, cc_release_same=True),
        ]
        song = Song(
            song=SongMetadata(id="test", name="TEST"),
            pacer=[
                PacerButton(
                    name="Patch 12",
                    actions=[Action(device="gp50", type=ActionType.CC, cc=0, value=12)],
                )
            ],
        )
        syx = export_song_to_syx(song, devices, "A1")

        expected_step = PacerSysExBuilder(c.PRESET_INDICES["A1"]).build_control_step(
            control_id=c.STOMPSWITCHES[0],
            step_index=1,
            msg_type=c.MSG_SW_MIDI_CC,
            channel=5,
            data1=0,
            data2=12,
            data3=12,
        )
        assert expected_step in syx


class TestExportEmptySteps:
    """Tests for empty/inactive step handling."""

    def test_empty_button_generates_steps(self, devices):
        """Empty song generates step messages for all 6 steps per button."""
        song = Song(song=SongMetadata(id="empty", name="XYZ"), pacer=[])
        all_frames = _frames(export_song_to_syx(song, devices, "A1"))
        stompswitch_ids = set(c.STOMPSWITCHES.values())
        syx = b"".join(f for f in all_frames if f[8] in stompswitch_ids)

        # MSG_CTRL_OFF (0x61) appears in each step as msg_type value
        # Element IDs for msg_type: step1=0x02, step2=0x08, step3=0x0E, etc.
        # We count pattern [elm, 0x01, 0x61] for each step
        total_ctrl_off = 0
        for step in range(1, 7):
            msg_type_elm = (step - 1) * 6 + 2  # 0x02, 0x08, 0x0E, 0x14, 0x1A, 0x20
            pattern = bytes([msg_type_elm, 0x01, c.MSG_CTRL_OFF])
            total_ctrl_off += syx.count(pattern)
        # All 6 buttons × 6 steps = 36
        assert total_ctrl_off == 36

    def test_partial_button_has_mixed_steps(self, devices):
        """Button with actions has active steps, rest are inactive."""
        song = Song(
            song=SongMetadata(id="px", name="PX"),
            pacer=[
                PacerButton(
                    name="Btn",
                    actions=[
                        Action(device="boss", type=ActionType.PRESET, value=1),
                        Action(device="boss", type=ActionType.PRESET, value=2),
                    ],
                )
            ],
        )
        syx = export_song_to_syx(song, devices, "A1")

        # Button 1 has 2 PRESET actions with MSG_SW_PRG_BANK (0x45)
        # Count MSG_SW_PRG_BANK patterns in msg_type element position
        total_prg_bank = 0
        for step in range(1, 7):
            msg_type_elm = (step - 1) * 6 + 2
            pattern = bytes([msg_type_elm, 0x01, c.MSG_SW_PRG_BANK])
            total_prg_bank += syx.count(pattern)
        assert total_prg_bank == 2  # 2 active steps with PRESET


class TestExportSysExFormat:
    """Tests for correct SysEx format."""

    def test_all_messages_valid_sysex(self, devices):
        """All messages start with F0 and end with F7."""
        song = Song(
            song=SongMetadata(id="test", name="TEST"),
            pacer=[
                PacerButton(
                    name="Btn",
                    actions=[Action(device="boss", type=ActionType.PRESET, value=1)],
                )
            ],
        )
        syx = export_song_to_syx(song, devices, "A1")

        # Split into messages
        messages = []
        start = 0
        for i, b in enumerate(syx):
            if b == c.SYSEX_END:
                messages.append(syx[start : i + 1])
                start = i + 1

        for msg in messages:
            assert msg[0] == c.SYSEX_START
            assert msg[-1] == c.SYSEX_END
            # Manufacturer ID
            assert msg[1:4] == c.MANUFACTURER_ID

    def test_messages_concatenated(self, devices):
        """Messages are directly concatenated without separators."""
        song = Song(song=SongMetadata(id="x", name="X"), pacer=[])
        syx = export_song_to_syx(song, devices, "A1")

        # After each F7, next byte should be F0 (or end of data)
        for i, b in enumerate(syx[:-1]):
            if b == c.SYSEX_END:
                assert syx[i + 1] == c.SYSEX_START


class TestExportLed:
    """Tests for LED color export."""

    def test_export_includes_led_off_for_empty_buttons(self, devices):
        """Empty buttons get LED_OFF colors."""
        song = Song(song=SongMetadata(id="test", name="LED"), pacer=[])
        syx = export_song_to_syx(song, devices, "A1")

        # All 6 buttons × 6 steps = 36 LED messages
        # LED active color elements: 0x41 (step1), 0x45 (step2), 0x49 (step3), etc.
        total_led_off = 0
        for step in range(1, 7):
            active_color_element = (step - 1) * 4 + 0x41
            total_led_off += syx.count(bytes([active_color_element, 0x01, c.LED_OFF]))
        assert total_led_off == 36  # All 6 buttons × 6 steps

    def test_export_led_colors_for_buttons_with_actions(self, devices):
        """Buttons with actions get BLUE/AMBER colors."""
        song = Song(
            song=SongMetadata(id="test", name="CLR"),
            pacer=[
                PacerButton(
                    name="Btn",
                    actions=[Action(device="boss", type=ActionType.PRESET, value=1)],
                )
            ],
        )
        syx = export_song_to_syx(song, devices, "A1")

        # Button 1 has actions: 6 steps with BLUE/AMBER
        # Buttons 2-6 empty: 30 steps with OFF/OFF
        # LED active color elements: 0x41 (step1), 0x45 (step2), 0x49 (step3), etc.
        total_blue = 0
        total_amber = 0
        total_off = 0
        for step in range(1, 7):
            active_color_element = (step - 1) * 4 + 0x41
            inactive_color_element = (step - 1) * 4 + 0x42
            total_blue += syx.count(bytes([active_color_element, 0x01, c.LED_BLUE]))
            total_amber += syx.count(bytes([inactive_color_element, 0x01, c.LED_AMBER]))
            total_off += syx.count(bytes([active_color_element, 0x01, c.LED_OFF]))

        assert total_blue == 6  # Button 1 × 6 steps
        assert total_amber == 6
        assert total_off == 30  # Buttons 2-6 × 6 steps

    def test_export_message_count_with_led(self, devices):
        """Export includes LED messages for all 6 steps per button."""
        song = Song(song=SongMetadata(id="test", name="CNT"), pacer=[])
        syx = export_song_to_syx(song, devices, "A1")

        # Count F0 (message starts)
        f0_count = syx.count(bytes([c.SYSEX_START]))
        # 1 name + 6 × (1 mode + 6 steps + 6 LED) + 16 M CFG = 95
        assert f0_count == 95


def _frames(syx: bytes) -> list[bytes]:
    return [bytes([c.SYSEX_START]) + f for f in syx.split(bytes([c.SYSEX_START]))[1:]]


def _midi_config_entries(syx: bytes) -> dict[int, tuple[int, int, int, int, int]]:
    """Parsuj ramki M CFG (obiekt 0x7E) do {wpis: (channel, typ, d1, d2, d3)}."""
    entries = {}
    for f in _frames(syx):
        if f[8] != c.CONTROL_MIDI:
            continue
        values = f[9:-2][2::4]  # [elm, 0x01, wartość, 0x00] ...
        entries[(f[9] - 1) // 6 + 1] = tuple(values)
    return entries


class TestExportMidiConfig:
    """Eksport on_load jako 16 wpisów M CFG."""

    def test_on_load_actions_fill_first_entries_rest_cleared(self, devices):
        song = Song(
            song=SongMetadata(id="test", name="T"),
            on_load=[
                Action(device="ms", type=ActionType.PATTERN, value="D01"),
                Action(device="boss", type=ActionType.CC, cc=40, value=99),
            ],
        )
        entries = _midi_config_entries(export_song_to_syx(song, devices, "D5"))

        assert sorted(entries) == list(range(1, 17))
        assert entries[1] == (1, c.MSG_SW_PRG_BANK, 48, 0, 0)
        assert entries[2] == (0, c.MSG_LOAD_CC, 40, 99, 0)
        for n in range(3, 17):
            assert entries[n] == (0, c.MSG_CTRL_OFF, 0, 0, 0)

    def test_song_without_on_load_clears_all_entries(self, devices):
        """Eksport bez on_load czyści M CFG ustawione wcześniej w presecie."""
        song = Song(song=SongMetadata(id="test", name="T"))
        entries = _midi_config_entries(export_song_to_syx(song, devices, "A1"))

        assert len(entries) == 16
        assert all(e == (0, c.MSG_CTRL_OFF, 0, 0, 0) for e in entries.values())

    def test_midi_config_frames_follow_buttons(self, devices):
        song = Song(song=SongMetadata(id="test", name="T"))
        objects = [f[8] for f in _frames(export_song_to_syx(song, devices, "A1"))]

        assert objects[-16:] == [c.CONTROL_MIDI] * 16
        assert c.CONTROL_MIDI not in objects[:-16]

    def test_midi_config_frames_target_preset_only(self, devices):
        song = Song(
            song=SongMetadata(id="test", name="T"),
            on_load=[Action(device="freak", type=ActionType.PRESET, value=67)],
        )
        for f in _frames(export_song_to_syx(song, devices, "D5")):
            assert f[6] == c.TARGET_PRESET
            assert f[7] == c.PRESET_INDICES["D5"]

    def test_obs_trigger_note_in_on_load_fails(self, devices):
        # fixture: freak na kanale 2 (1-16) = record_trigger_channel 1 (0-15)
        config = PacerConfig(
            record_trigger_channel=1, record_start_note=94, record_stop_note=93
        )
        song = Song(
            song=SongMetadata(id="test", name="T"),
            on_load=[Action(device="freak", type=ActionType.NOTE, note=94)],
        )
        with pytest.raises(ValueError, match="OBS"):
            export_song_to_syx(song, devices, "A1", pacer_config=config)
