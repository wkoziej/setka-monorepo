# ABOUTME: Unit tests for the cross-platform native SysEx sender (Unit 1, macOS plan).
# ABOUTME: Mocks rtmidi.MidiOut and time.sleep - no real MIDI hardware required.

import pytest

from paternologia.midi import sysex_sender
from paternologia.midi.sysex_sender import (
    PacerPortNotFoundError,
    send_sysex,
    split_sysex_messages,
)
from paternologia.models import Device, Song, SongMetadata
from paternologia.pacer import constants as c
from paternologia.pacer.export import export_song_to_syx


def frame(payload: bytes) -> bytes:
    """Build a minimal valid SysEx frame for tests (0xF0 ... 0xF7)."""
    return bytes([c.SYSEX_START]) + payload + bytes([c.SYSEX_END])


class FakeMidiOut:
    """Fake rtmidi.MidiOut recording calls for assertions."""

    #: shared across instances created within one test via monkeypatch
    calls: list[tuple[str, object]] = []
    ports: list[str] = ["Midi Through:Midi Through Port-0 14:0", "PACER MIDI1 20:0"]
    fail_on: str | None = None
    #: if set, each get_ports() call across all instances pops the next list
    #: (sticking to the last once exhausted) - simulates the port list
    #: changing between two separate MidiOut() enumerations.
    ports_sequence: list[list[str]] | None = None

    def get_ports(self):
        self.calls.append(("get_ports", None))
        if FakeMidiOut.ports_sequence:
            result = FakeMidiOut.ports_sequence[0]
            if len(FakeMidiOut.ports_sequence) > 1:
                FakeMidiOut.ports_sequence.pop(0)
            return list(result)
        return list(self.ports)

    def open_port(self, idx):
        self.calls.append(("open_port", idx))
        if self.fail_on == "open_port":
            raise RuntimeError("device unplugged")

    def send_message(self, message):
        self.calls.append(("send_message", tuple(message)))
        if self.fail_on == "send_message" and len(
            [c for c in self.calls if c[0] == "send_message"]
        ) == 2:
            raise RuntimeError("device unplugged mid-send")

    def close_port(self):
        self.calls.append(("close_port", None))

    def delete(self):
        self.calls.append(("delete", None))


@pytest.fixture
def fake_rtmidi(monkeypatch):
    """Patch rtmidi.MidiOut everywhere it's imported (ports.py and sysex_sender.py
    both do `import rtmidi` at call time, so patching the rtmidi module object
    covers both)."""
    import rtmidi

    FakeMidiOut.calls = []
    FakeMidiOut.fail_on = None
    FakeMidiOut.ports = [
        "Midi Through:Midi Through Port-0 14:0",
        "PACER MIDI1 20:0",
    ]
    FakeMidiOut.ports_sequence = None
    monkeypatch.setattr(rtmidi, "MidiOut", FakeMidiOut)
    return FakeMidiOut


@pytest.fixture
def no_sleep(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(sysex_sender.time, "sleep", lambda s: sleeps.append(s))
    return sleeps


class TestSplitSysexMessages:
    def test_three_frames(self):
        frames = [frame(b"\x00\x01\x02"), frame(b"\x03\x04"), frame(b"\x05")]
        blob = b"".join(frames)
        assert split_sysex_messages(blob) == frames

    def test_export_song_frame_count_matches_builder(self):
        """Regression: split_sysex_messages(export_song_to_syx(...)) returns as
        many frames as export.py actually built (frame count == F7 count)."""
        devices = [Device(id="boss", name="Boss RC-600", midi_channel=0)]
        song = Song(song=SongMetadata(id="test", name="TESTSONG"), pacer=[])
        blob = export_song_to_syx(song, devices, "A1")

        frames = split_sysex_messages(blob)

        assert len(frames) == blob.count(bytes([c.SYSEX_END]))
        assert b"".join(frames) == blob

    def test_empty_blob_returns_no_frames(self):
        assert split_sysex_messages(b"") == []

    def test_truncated_last_frame_raises(self):
        blob = frame(b"\x00\x01") + bytes([c.SYSEX_START]) + b"\x02\x03"
        with pytest.raises(ValueError, match="Truncated"):
            split_sysex_messages(blob)

    def test_garbage_byte_at_frame_boundary_raises(self):
        """A byte other than 0xF0 where a frame should start (not just a
        missing trailing 0xF7) must be rejected, not silently included."""
        blob = frame(b"\x00\x01") + b"\x01\x02\xf7"
        with pytest.raises(ValueError, match="Expected SysEx start"):
            split_sysex_messages(blob)


class TestSendSysex:
    def test_happy_path_sends_frames_in_order_with_pacing_between(
        self, fake_rtmidi, no_sleep
    ):
        frames = [frame(b"\x00\x01"), frame(b"\x02\x03"), frame(b"\x04\x05")]
        blob = b"".join(frames)

        port_name = send_sysex(blob, device_name="PACER", interval_ms=20)

        sent = [call for call in fake_rtmidi.calls if call[0] == "send_message"]
        assert [tuple(f) for f in frames] == [c[1] for c in sent]
        assert port_name == "PACER MIDI1 20:0"
        assert no_sleep == [0.02, 0.02]  # 2 sleeps for 3 frames, not 3, not 0

    def test_empty_blob_does_not_open_port(self, fake_rtmidi, no_sleep):
        result = send_sysex(b"", device_name="PACER", interval_ms=20)

        assert result is None
        assert fake_rtmidi.calls == []
        assert no_sleep == []

    def test_truncated_blob_raises_before_any_send(self, fake_rtmidi, no_sleep):
        blob = frame(b"\x00\x01") + bytes([c.SYSEX_START]) + b"\x02\x03"

        with pytest.raises(ValueError, match="Truncated"):
            send_sysex(blob, device_name="PACER", interval_ms=20)

        assert fake_rtmidi.calls == []

    def test_port_not_found_raises_without_opening_output(self, fake_rtmidi, no_sleep):
        fake_rtmidi.ports = ["Midi Through:Midi Through Port-0 14:0"]
        blob = frame(b"\x00\x01")

        with pytest.raises(PacerPortNotFoundError) as exc_info:
            send_sysex(blob, device_name="PACER", interval_ms=20)

        assert exc_info.value.device_name == "PACER"
        # find_rtmidi_output_port's own lookup calls get_ports() once; no
        # open_port/send_message ever happens.
        assert all(call[0] != "open_port" for call in fake_rtmidi.calls)
        assert all(call[0] != "send_message" for call in fake_rtmidi.calls)

    def test_exception_mid_send_still_releases_port(self, fake_rtmidi, no_sleep):
        fake_rtmidi.fail_on = "send_message"
        frames = [frame(b"\x00"), frame(b"\x01"), frame(b"\x02")]
        blob = b"".join(frames)

        with pytest.raises(RuntimeError, match="unplugged mid-send"):
            send_sysex(blob, device_name="PACER", interval_ms=20)

        close_calls = [c for c in fake_rtmidi.calls if c[0] == "close_port"]
        delete_calls = [c for c in fake_rtmidi.calls if c[0] == "delete"]
        # 1 close_port (the real send MidiOut) + 2 delete (that one, plus the
        # throwaway probe MidiOut find_rtmidi_output_port deletes internally).
        assert len(close_calls) == 1
        assert len(delete_calls) == 2

    def test_port_list_changed_between_lookup_and_open_raises(
        self, fake_rtmidi, no_sleep
    ):
        """Regression: find_rtmidi_output_port() enumerates ports on its own
        throwaway MidiOut instance; send_sysex opens a second, independent
        instance and must not blindly reuse that index. If the port list
        changed in between (replug, another app opening/closing a virtual
        CoreMIDI port), reusing the index would silently send real SysEx to
        whatever now sits at that position instead of raising."""
        fake_rtmidi.ports_sequence = [
            ["Midi Through:Midi Through Port-0 14:0", "PACER MIDI1 20:0"],
            ["Midi Through:Midi Through Port-0 14:0", "Some Other Device 99:0"],
        ]
        blob = frame(b"\x00\x01")

        with pytest.raises(PacerPortNotFoundError):
            send_sysex(blob, device_name="PACER", interval_ms=20)

        assert all(call[0] != "open_port" for call in fake_rtmidi.calls)
        assert all(call[0] != "send_message" for call in fake_rtmidi.calls)

    def test_open_port_raises_still_releases_port(self, fake_rtmidi, no_sleep):
        fake_rtmidi.fail_on = "open_port"
        blob = frame(b"\x00\x01")

        with pytest.raises(RuntimeError, match="unplugged"):
            send_sysex(blob, device_name="PACER", interval_ms=20)

        close_calls = [c for c in fake_rtmidi.calls if c[0] == "close_port"]
        delete_calls = [c for c in fake_rtmidi.calls if c[0] == "delete"]
        assert len(close_calls) == 1
        assert len(delete_calls) == 2
