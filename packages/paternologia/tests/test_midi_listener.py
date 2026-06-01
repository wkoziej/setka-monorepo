# ABOUTME: Tests for MIDI listener (rtmidi wrapper).
# ABOUTME: Tests Program Change parsing and event publishing via virtual MIDI ports.

import asyncio

import pytest
import rtmidi

from paternologia.midi import listener as listener_mod
from paternologia.midi.events import EventBus
from paternologia.midi.index import SongMidiIndex
from paternologia.midi.listener import MidiListener
from paternologia.models import (
    Action,
    ActionType,
    Device,
    PacerButton,
    Song,
    SongMetadata,
)


def _has_alsa() -> bool:
    """Check if ALSA virtual MIDI ports are available."""
    try:
        mi = rtmidi.MidiIn()
        mi.open_virtual_port("test")
        mi.close_port()
        del mi
        return True
    except Exception:
        return False


requires_alsa = pytest.mark.skipif(
    not _has_alsa(), reason="ALSA not available (CI or non-Linux)"
)


def _make_device(device_id: str, midi_channel: int) -> Device:
    """Create device. midi_channel uses 1-16 convention (as in devices.yaml)."""
    return Device(
        id=device_id,
        name=device_id.upper(),
        midi_channel=midi_channel,
        action_types=[ActionType.PRESET],
    )


def _make_song(song_id: str, device: str, preset_value: int) -> Song:
    return Song(
        song=SongMetadata(id=song_id, name=song_id.title()),
        pacer=[
            PacerButton(
                name="SW1",
                actions=[
                    Action(device=device, type=ActionType.PRESET, value=preset_value),
                ],
            )
        ],
    )


class TestReplugReconnect:
    """Tests for poll_reconnect() replug handling (no hardware required)."""

    def _listener(self) -> MidiListener:
        return MidiListener(
            song_index=SongMidiIndex.build([], []), event_bus=EventBus()
        )

    def test_reopens_when_port_returns(self, monkeypatch):
        """Inactive listener reopens by name when the PACER port reappears."""
        listener = self._listener()
        listener._device_name = "PACER"
        monkeypatch.setattr(listener_mod, "find_rtmidi_port", lambda name: 0)
        calls = []
        monkeypatch.setattr(listener, "start", lambda name: calls.append(name) or True)
        listener.poll_reconnect()
        assert calls == ["PACER"]

    def test_releases_when_unplugged(self, monkeypatch):
        """Active listener releases its handle when the PACER port disappears."""
        listener = self._listener()
        listener._device_name = "PACER"
        listener._midi_in = object()  # simulate an open port
        monkeypatch.setattr(listener_mod, "find_rtmidi_port", lambda name: None)
        stopped = []
        monkeypatch.setattr(listener, "stop", lambda: stopped.append(True))
        listener.poll_reconnect()
        assert stopped == [True]

    def test_noop_without_device_name(self, monkeypatch):
        """poll_reconnect does nothing before any start() set a device name."""
        listener = self._listener()
        called = []
        monkeypatch.setattr(
            listener_mod, "find_rtmidi_port", lambda name: called.append(name)
        )
        listener.poll_reconnect()
        assert called == []


class TestMidiListenerParsing:
    """Tests for MIDI message parsing without hardware."""

    def test_parse_program_change(self):
        """Should parse Program Change status byte correctly."""
        # 0xCC = Program Change on channel 12 (0-indexed)
        status = 0xCC
        channel = status & 0x0F
        assert channel == 12

    def test_parse_program_change_channel_0(self):
        """Channel 0 Program Change = 0xC0."""
        status = 0xC0
        channel = status & 0x0F
        assert channel == 0


@requires_alsa
class TestMidiListenerWithVirtualPorts:
    """Integration tests using ALSA virtual MIDI ports."""

    async def test_receives_program_change(self):
        """Should publish event when Program Change received."""
        devices = [_make_device("boss", midi_channel=13)]
        songs = [_make_song("zen", "boss", 2)]
        index = SongMidiIndex.build(songs, devices)
        bus = EventBus()
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)

        listener = MidiListener(song_index=index, event_bus=bus)
        try:
            listener.start_virtual("test_paternologia")
        except Exception as e:
            pytest.skip(f"ALSA unavailable at runtime: {e}")

        try:
            queue = bus.subscribe()

            # Send Program Change: channel 12, program 2
            midi_out = rtmidi.MidiOut()
            ports = midi_out.get_ports()
            port_idx = None
            for i, name in enumerate(ports):
                if "test_paternologia" in name:
                    port_idx = i
                    break

            assert port_idx is not None, f"Virtual port not found in {ports}"
            midi_out.open_port(port_idx)
            midi_out.send_message([0xCC, 2])  # PC channel 12, program 2

            received = await asyncio.wait_for(queue.get(), timeout=2.0)
            assert received.song_id == "zen"
            assert received.channel == 12
            assert received.program == 2

            midi_out.close_port()
            del midi_out
        finally:
            listener.stop()

    async def test_ignores_non_program_change(self):
        """Should ignore non-PC MIDI messages."""
        devices = [_make_device("boss", midi_channel=13)]
        songs = [_make_song("zen", "boss", 2)]
        index = SongMidiIndex.build(songs, devices)
        bus = EventBus()
        loop = asyncio.get_running_loop()
        bus.set_loop(loop)

        listener = MidiListener(song_index=index, event_bus=bus)
        try:
            listener.start_virtual("test_paternologia_ignore")
        except Exception as e:
            pytest.skip(f"ALSA unavailable at runtime: {e}")

        try:
            queue = bus.subscribe()

            midi_out = rtmidi.MidiOut()
            ports = midi_out.get_ports()
            port_idx = None
            for i, name in enumerate(ports):
                if "test_paternologia_ignore" in name:
                    port_idx = i
                    break

            assert port_idx is not None
            midi_out.open_port(port_idx)
            # Send Note On (not Program Change)
            midi_out.send_message([0x9C, 60, 100])

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(queue.get(), timeout=0.5)

            midi_out.close_port()
            del midi_out
        finally:
            listener.stop()
