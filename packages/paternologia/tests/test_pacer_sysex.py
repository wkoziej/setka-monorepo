# ABOUTME: Unit tests for Pacer SysEx message building.
# ABOUTME: Tests checksum calculation, preset name and control step encoding.


import pytest
from paternologia.pacer import constants as c
from paternologia.pacer.sysex import PacerSysExBuilder, checksum


class TestChecksum:
    """Tests for checksum calculation."""

    def test_checksum_range(self):
        """Checksum is always 0-127."""
        data = bytes([0x00, 0x01, 0x77, 0x7F, 0x01])
        cs = checksum(data)
        assert 0 <= cs < 128

    def test_checksum_consistency(self):
        """Same input gives same checksum."""
        data = bytes([0x00, 0x01, 0x77, 0x7F, 0x01])
        assert checksum(data) == checksum(data)

    def test_checksum_formula(self):
        """Checksum follows (128 - sum%128) % 128."""
        data = bytes([10, 20, 30])  # sum = 60
        expected = (128 - (60 % 128)) % 128  # = 68
        assert checksum(data) == expected


class TestPresetName:
    """Tests for preset name SysEx messages."""

    def test_preset_name_structure(self):
        """Preset name has correct SysEx structure."""
        builder = PacerSysExBuilder(0x00)  # A1
        syx = builder.build_preset_name("TEST")

        # SysEx frame
        assert syx[0] == c.SYSEX_START
        assert syx[-1] == c.SYSEX_END

        # Manufacturer ID
        assert syx[1:4] == c.MANUFACTURER_ID

    def test_preset_name_header(self):
        """Header contains Device ID, CMD, TARGET, INDEX, CONTROL_NAME, Element."""
        builder = PacerSysExBuilder(0x00)
        syx = builder.build_preset_name("TEST")

        # After Manufacturer ID: Device ID, CMD, TARGET, INDEX, CONTROL_NAME, Element
        assert syx[4] == c.DEVICE_ID  # 0x7F
        assert syx[5] == c.CMD_SET  # 0x01
        assert syx[6] == c.TARGET_PRESET  # 0x01
        assert syx[7] == 0x00  # preset index A1
        assert syx[8] == c.CONTROL_NAME  # 0x01
        assert syx[9] == 0x00  # Element = 0 for preset name

    def test_preset_name_data(self):
        """Data contains length + ASCII name."""
        builder = PacerSysExBuilder(0x00)
        syx = builder.build_preset_name("TEST")

        # Data starts at byte 10: [length, T, E, S, T]
        assert syx[10] == 4  # length
        assert syx[11:15] == b"TEST"

    def test_preset_name_truncation(self):
        """Long names are truncated to 8 characters."""
        builder = PacerSysExBuilder(0x00)
        syx = builder.build_preset_name("VERY_LONG_NAME")

        # Find length byte (after header)
        assert syx[10] == 8  # truncated to 8
        assert syx[11:19] == b"VERY_LON"

    def test_preset_name_different_index(self):
        """Different preset index in header."""
        builder = PacerSysExBuilder(0x0F)  # B8
        syx = builder.build_preset_name("X")

        assert syx[7] == 0x0F


class TestControlStep:
    """Tests for control step SysEx messages."""

    def test_control_step_structure(self):
        """Control step has correct SysEx structure."""
        builder = PacerSysExBuilder(0x00)
        syx = builder.build_control_step(
            control_id=0x0D,  # SW1
            step_index=1,
            msg_type=0x45,
            channel=0,
            data1=5,
            active=True,
        )

        assert syx[0] == c.SYSEX_START
        assert syx[-1] == c.SYSEX_END
        assert syx[1:4] == c.MANUFACTURER_ID

    def test_control_step_header(self):
        """Header for control step does NOT have Element."""
        builder = PacerSysExBuilder(0x00)
        syx = builder.build_control_step(
            control_id=0x0D,
            step_index=1,
            msg_type=0x45,
            channel=0,
            data1=5,
            active=True,
        )

        # Header: Device ID, CMD, TARGET, INDEX, CONTROL_ID (no Element)
        assert syx[4] == c.DEVICE_ID
        assert syx[5] == c.CMD_SET
        assert syx[6] == c.TARGET_PRESET
        assert syx[7] == 0x00  # preset A1
        assert syx[8] == 0x0D  # SW1

    def test_control_step_params_format(self):
        """Parameters have format [element_id, 0x01, value, 0x00]."""
        builder = PacerSysExBuilder(0x00)
        syx = builder.build_control_step(
            control_id=0x0D,
            step_index=1,
            msg_type=0x45,
            channel=3,
            data1=10,
            data2=20,
            data3=30,
            active=True,
        )

        # Parameters start at byte 9
        params = syx[9:-2]  # exclude checksum and F7

        # Step 1: base = 0, so element IDs are 1-6
        # Channel: [1, 0x01, 3, 0x00]
        assert params[0:4] == bytes([1, 0x01, 3, 0x00])
        # Message type: [2, 0x01, 0x45, 0x00]
        assert params[4:8] == bytes([2, 0x01, 0x45, 0x00])
        # Data1: [3, 0x01, 10, 0x00]
        assert params[8:12] == bytes([3, 0x01, 10, 0x00])
        # Data2: [4, 0x01, 20, 0x00]
        assert params[12:16] == bytes([4, 0x01, 20, 0x00])
        # Data3: [5, 0x01, 30, 0x00]
        assert params[16:20] == bytes([5, 0x01, 30, 0x00])
        # Active: [6, 0x01, 1] - NO padding
        assert params[20:23] == bytes([6, 0x01, 1])

    def test_control_step_different_step_index(self):
        """Step index affects element IDs."""
        builder = PacerSysExBuilder(0x00)
        syx = builder.build_control_step(
            control_id=0x0D,
            step_index=3,  # base = 12
            msg_type=0x45,
            channel=0,
            data1=5,
            active=True,
        )

        params = syx[9:-2]
        # Step 3: base = (3-1)*6 = 12, so element IDs are 13-18
        assert params[0] == 13  # channel element
        assert params[4] == 14  # msg_type element

    def test_control_step_inactive(self):
        """Inactive step has active=0."""
        builder = PacerSysExBuilder(0x00)
        syx = builder.build_control_step(
            control_id=0x0D,
            step_index=1,
            msg_type=c.MSG_CTRL_OFF,
            channel=0,
            data1=0,
            active=False,
        )

        params = syx[9:-2]
        # Last parameter: [6, 0x01, 0]
        assert params[-3:] == bytes([6, 0x01, 0])


class TestChecksumMatchesDevice:
    """Checksum liczony od bajtu CMD (po nagłówku F0 00 01 77 7F), jak w Pacerze.

    Ramki referencyjne: dump prawdziwego Pacera, preset B5 (wyeksportowany
    z Paternologii, docs/pacer-mcfg-verification.md).
    """

    def test_control_step_matches_device_dump(self):
        syx = PacerSysExBuilder(0x0B).build_control_step(
            control_id=c.STOMPSWITCHES[0],
            step_index=1,
            msg_type=c.MSG_SW_PRG_BANK,
            channel=13,
            data1=4,
        )
        assert syx == bytes.fromhex(
            "F0 00 01 77 7F 01 01 0B 0D 01 01 0D 00 02 01 45 00 03 01 04 00"
            " 04 01 00 00 05 01 00 00 06 01 01 74 F7"
        )

    def test_control_mode_matches_device_dump(self):
        syx = PacerSysExBuilder(0x0B).build_control_mode(c.STOMPSWITCHES[0], 0)
        assert syx == bytes.fromhex("F0 00 01 77 7F 01 01 0B 0D 60 01 00 05 F7")

    def test_control_led_matches_device_dump(self):
        syx = PacerSysExBuilder(0x0B).build_control_led(
            c.STOMPSWITCHES[0],
            step_index=1,
            active_color=c.LED_BLUE,
            inactive_color=c.LED_AMBER,
        )
        assert syx == bytes.fromhex(
            "F0 00 01 77 7F 01 01 0B 0D 40 01 00 00 41 01 11 00 42 01 07 00"
            " 43 01 00 44 F7"
        )

    def test_preset_name_checksum_from_cmd_byte(self):
        syx = PacerSysExBuilder(0x0B).build_preset_name("Swit")
        assert syx[-2] == checksum(syx[5:-2])


class TestMidiConfigEntry:
    """Wpis M CFG (Preset Recall MIDI): obiekt 0x7E, 5 elementów, bez active.

    Ramki referencyjne pochodzą z dumpu prawdziwego Pacera
    (docs/pacer-mcfg-verification.md).
    """

    def test_load_cc_matches_device_dump_entry_1(self):
        """A5 wpis 1: LOAD_CC ch1, CC 123 = 127."""
        syx = PacerSysExBuilder(0x05).build_midi_config_entry(
            entry_index=1, msg_type=c.MSG_LOAD_CC, channel=1, data1=123, data2=127
        )
        assert syx == bytes.fromhex(
            "F0 00 01 77 7F 01 01 05 7E 01 01 01 00 02 01 65 00"
            " 03 01 7B 00 04 01 7F 00 05 01 00 07 F7"
        )

    def test_last_entry_uses_elements_5b_to_5f(self):
        """A5 wpis 16: elementy 0x5B..0x5F."""
        syx = PacerSysExBuilder(0x05).build_midi_config_entry(
            entry_index=16, msg_type=c.MSG_LOAD_CC, channel=16, data1=123, data2=127
        )
        assert syx == bytes.fromhex(
            "F0 00 01 77 7F 01 01 05 7E 5B 01 10 00 5C 01 65 00"
            " 5D 01 7B 00 5E 01 7F 00 5F 01 00 36 F7"
        )

    def test_prg_bank_with_bank_matches_round_trip(self):
        """D5 wpis 3: PRG_BANK ch12 program 7, LSB 1, MSB 2 (round-trip)."""
        syx = PacerSysExBuilder(0x17).build_midi_config_entry(
            entry_index=3,
            msg_type=c.MSG_SW_PRG_BANK,
            channel=12,
            data1=7,
            data2=1,
            data3=2,
        )
        assert syx == bytes.fromhex(
            "F0 00 01 77 7F 01 01 17 7E 0D 01 0C 00 0E 01 45 00"
            " 0F 01 07 00 10 01 01 00 11 01 02 3E F7"
        )

    def test_empty_entry_matches_device_dump(self):
        """A1 wpis 1 pusty: kanał 0, typ OFF, dane 0."""
        syx = PacerSysExBuilder(0x01).build_empty_midi_config_entry(entry_index=1)
        assert syx == bytes.fromhex(
            "F0 00 01 77 7F 01 01 01 7E 01 01 00 00 02 01 61 00"
            " 03 01 00 00 04 01 00 00 05 01 00 0A F7"
        )

    def test_targets_preset_never_global(self):
        """Ramka M CFG zawsze ma TARGET_PRESET na pozycji target."""
        syx = PacerSysExBuilder(0x17).build_midi_config_entry(
            entry_index=1, msg_type=c.MSG_SW_NOTE, channel=11, data1=60, data2=100
        )
        assert syx[6] == c.TARGET_PRESET
        assert syx[6] != c.TARGET_GLOBAL
        assert syx[8] == c.CONTROL_MIDI

    def test_entry_index_out_of_range(self):
        builder = PacerSysExBuilder(0x17)
        for bad in (0, c.MIDI_CONFIG_ENTRIES + 1):
            with pytest.raises(ValueError, match="entry_index"):
                builder.build_midi_config_entry(
                    entry_index=bad, msg_type=c.MSG_LOAD_CC, channel=1, data1=1
                )

    def test_value_out_of_range(self):
        builder = PacerSysExBuilder(0x17)
        with pytest.raises(ValueError, match="data1"):
            builder.build_midi_config_entry(
                entry_index=1, msg_type=c.MSG_LOAD_CC, channel=1, data1=128
            )
        with pytest.raises(ValueError, match="channel"):
            builder.build_midi_config_entry(
                entry_index=1, msg_type=c.MSG_LOAD_CC, channel=17, data1=1
            )
