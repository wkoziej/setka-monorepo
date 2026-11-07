# ABOUTME: Unit tests for Pacer read-back verification after sending a preset.
# ABOUTME: Tests dump request frame, SysEx frame splitting and missing-frame detection.

import subprocess
from contextlib import contextmanager

import pytest
from paternologia.pacer import constants as c
from paternologia.pacer import readback
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


class _FakeAmidi:
    """Zastępuje subprocess.run: zapisuje argv/kwargs i dump do pliku -r."""

    def __init__(self, dump=b"", returncode=0, stderr="", raises=None, log=None):
        self.dump, self.returncode, self.stderr = dump, returncode, stderr
        self.raises, self.log = raises, log if log is not None else []
        self.argv, self.kwargs = None, None

    def __call__(self, argv, **kwargs):
        self.argv, self.kwargs = argv, kwargs
        self.log.append("amidi")
        if self.raises is not None:
            raise self.raises
        with open(argv[argv.index("-r") + 1], "wb") as f:
            f.write(self.dump)
        return subprocess.CompletedProcess(argv, self.returncode, "", self.stderr)


@pytest.fixture
def no_settle(monkeypatch):
    monkeypatch.setattr(readback.time, "sleep", lambda s: None)


class TestReadBackPreset:
    def test_runs_amidi_dump_request_and_returns_dump(self, monkeypatch, no_settle):
        fake = _FakeAmidi(dump=b"\xf0dump\xf7")
        monkeypatch.setattr(readback.subprocess, "run", fake)

        assert readback.read_back_preset("hw:7,0,0", 0x17) == b"\xf0dump\xf7"
        assert fake.argv[:3] == ["amidi", "-p", "hw:7,0,0"]
        assert (
            fake.argv[fake.argv.index("-S") + 1] == "F0 00 01 77 7F 02 01 17 7F 67 F7"
        )

    def test_has_hard_timeout(self, monkeypatch, no_settle):
        """`-t` to tylko timeout ciszy; szum z EXP mógłby trzymać amidi w nieskończoność."""
        fake = _FakeAmidi()
        monkeypatch.setattr(readback.subprocess, "run", fake)

        readback.read_back_preset("hw:7,0,0", 0x17)

        assert fake.kwargs["timeout"] > readback.DUMP_IDLE_SECONDS

    def test_amidi_error_raises_runtime_error(self, monkeypatch, no_settle):
        monkeypatch.setattr(
            readback.subprocess, "run", _FakeAmidi(returncode=1, stderr="busy")
        )
        with pytest.raises(RuntimeError, match="busy"):
            readback.read_back_preset("hw:7,0,0", 0x17)

    @pytest.mark.parametrize(
        "error",
        [subprocess.TimeoutExpired("amidi", 5), FileNotFoundError("amidi")],
    )
    def test_timeout_and_missing_amidi_raise_runtime_error(
        self, monkeypatch, no_settle, error
    ):
        monkeypatch.setattr(readback.subprocess, "run", _FakeAmidi(raises=error))
        with pytest.raises(RuntimeError):
            readback.read_back_preset("hw:7,0,0", 0x17)

    def test_amidi_runs_inside_pause(self, monkeypatch, no_settle):
        log = []
        monkeypatch.setattr(readback.subprocess, "run", _FakeAmidi(log=log))

        @contextmanager
        def pause():
            log.append("pause")
            yield
            log.append("resume")

        readback.read_back_preset("hw:7,0,0", 0x17, pause())

        assert log == ["pause", "amidi", "resume"]

    def test_pause_exits_when_amidi_times_out(self, monkeypatch, no_settle):
        log = []
        monkeypatch.setattr(
            readback.subprocess,
            "run",
            _FakeAmidi(raises=subprocess.TimeoutExpired("amidi", 5), log=log),
        )

        @contextmanager
        def pause():
            log.append("pause")
            try:
                yield
            finally:
                log.append("resume")

        with pytest.raises(RuntimeError):
            readback.read_back_preset("hw:7,0,0", 0x17, pause())
        assert log == ["pause", "amidi", "resume"]
