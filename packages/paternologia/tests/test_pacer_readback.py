# ABOUTME: Unit tests for Pacer read-back verification after sending a preset.
# ABOUTME: Tests dump request frame, SysEx frame splitting and missing-frame detection.

from paternologia.pacer import constants as c
from paternologia.pacer.readback import missing_frames, split_sysex_frames
from paternologia.pacer.sysex import PacerSysExBuilder


def _step(preset: int, data1: int) -> bytes:
    return PacerSysExBuilder(preset).build_control_step(
        c.STOMPSWITCHES[0], 1, c.MSG_SW_PRG_BANK, 13, data1
    )


class TestDumpRequest:
    def test_preset_dump_request_matches_protocol(self):
        """Request dumpu D5 użyty na sprzęcie: F0 00 01 77 7F 02 01 17 7F 67 F7."""
        assert PacerSysExBuilder(0x17).build_preset_dump_request() == bytes.fromhex(
            "F0 00 01 77 7F 02 01 17 7F 67 F7"
        )


class TestSplitSysexFrames:
    def test_splits_concatenated_frames(self):
        a, b = _step(0x17, 1), _step(0x17, 2)
        assert split_sysex_frames(a + b) == [a, b]

    def test_skips_non_sysex_bytes_between_frames(self):
        """Pacer potrafi wtrącić CC (np. B0 0B 00 z wejścia EXP) przed dumpem."""
        a, b = _step(0x17, 1), _step(0x17, 2)
        assert split_sysex_frames(bytes([0xB0, 0x0B, 0x00]) + a + b) == [a, b]

    def test_drops_unterminated_frame(self):
        a = _step(0x17, 1)
        assert split_sysex_frames(a + a[:5]) == [a]


class TestMissingFrames:
    def test_all_frames_present(self):
        sent = _step(0x17, 1) + _step(0x17, 2)
        assert missing_frames(sent, dump=sent) == []

    def test_reports_frame_not_stored(self):
        stored, lost = _step(0x17, 1), _step(0x17, 2)
        assert missing_frames(stored + lost, dump=stored) == [lost]

    def test_ignores_preset_name_frame(self):
        """Pacer zwraca nazwę w innym układzie niż przyjmuje — nie porównujemy jej."""
        name = PacerSysExBuilder(0x17).build_preset_name("Zima")
        step = _step(0x17, 1)
        assert missing_frames(name + step, dump=step) == []

    def test_empty_dump_reports_everything(self):
        sent = _step(0x17, 1) + _step(0x17, 2)
        assert len(missing_frames(sent, dump=b"")) == 2
