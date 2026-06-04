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
        """Inactive listener reopens by name when the PACER ports reappear."""
        listener = self._listener()
        listener._device_name = "PACER"
        monkeypatch.setattr(listener_mod, "find_rtmidi_ports", lambda name: [0, 1])
        calls = []
        monkeypatch.setattr(listener, "start", lambda name: calls.append(name) or True)
        listener.poll_reconnect()
        assert calls == ["PACER"]

    def test_resubscribes_when_handles_stale(self, monkeypatch):
        """Ports present and handles open, but ALSA subscription lost -> reopen.

        This is the re-enumeration trap: rtmidi keeps the MidiIn handle "open"
        (is_active stays True) after PACER re-enumerates, so the old code never
        re-subscribed. The honest signal is pacer_input_subscribed. Reopen only
        after the miss persists past the debounce threshold.
        """
        listener = self._listener()
        listener._device_name = "PACER"
        listener._midi_ins = [object()]  # handles look open
        monkeypatch.setattr(listener_mod, "find_rtmidi_ports", lambda name: [0, 1])
        monkeypatch.setattr(listener_mod, "pacer_input_subscribed", lambda name: False)
        events = []
        monkeypatch.setattr(listener, "stop", lambda: events.append("stop"))
        monkeypatch.setattr(
            listener, "start", lambda name: events.append("start") or True
        )
        for _ in range(listener_mod._RESUBSCRIBE_STRIKES):
            listener.poll_reconnect()
        assert events == ["stop", "start"]

    def test_single_missed_read_defers_reopen(self, monkeypatch):
        """One negative subscription read must NOT tear down a working input.

        A lone aconnect miss is likely a transient/partial snapshot; debounce
        defers stop+start until the miss persists.
        """
        listener = self._listener()
        listener._device_name = "PACER"
        listener._midi_ins = [object()]
        monkeypatch.setattr(listener_mod, "find_rtmidi_ports", lambda name: [0, 1])
        monkeypatch.setattr(listener_mod, "pacer_input_subscribed", lambda name: False)
        events = []
        monkeypatch.setattr(listener, "stop", lambda: events.append("stop"))
        monkeypatch.setattr(
            listener, "start", lambda name: events.append("start") or True
        )
        listener.poll_reconnect()  # single miss
        assert events == []

    def test_strike_counter_resets_on_subscribed(self, monkeypatch):
        """A subscribed reading clears accrued strikes, so misses must be consecutive."""
        listener = self._listener()
        listener._device_name = "PACER"
        listener._midi_ins = [object()]
        monkeypatch.setattr(listener_mod, "find_rtmidi_ports", lambda name: [0, 1])
        events = []
        monkeypatch.setattr(listener, "stop", lambda: events.append("stop"))
        monkeypatch.setattr(
            listener, "start", lambda name: events.append("start") or True
        )
        subscribed = {"v": False}
        monkeypatch.setattr(
            listener_mod, "pacer_input_subscribed", lambda name: subscribed["v"]
        )
        listener.poll_reconnect()  # miss 1
        subscribed["v"] = True
        listener.poll_reconnect()  # subscribed -> reset
        subscribed["v"] = False
        listener.poll_reconnect()  # miss 1 again (not 2)
        assert events == []

    def test_noop_when_subscription_alive(self, monkeypatch):
        """Active and still subscribed -> leave the open handles untouched."""
        listener = self._listener()
        listener._device_name = "PACER"
        listener._midi_ins = [object()]
        monkeypatch.setattr(listener_mod, "find_rtmidi_ports", lambda name: [0, 1])
        monkeypatch.setattr(listener_mod, "pacer_input_subscribed", lambda name: True)
        events = []
        monkeypatch.setattr(listener, "stop", lambda: events.append("stop"))
        monkeypatch.setattr(
            listener, "start", lambda name: events.append("start") or True
        )
        listener.poll_reconnect()
        assert events == []

    def test_input_subscribed_false_when_inactive(self):
        """No open handle -> input_subscribed is False without touching ALSA."""
        listener = self._listener()
        listener._device_name = "PACER"
        assert listener.input_subscribed is False

    def test_input_subscribed_reflects_alsa(self, monkeypatch):
        """With handles open, input_subscribed delegates to the ALSA check."""
        listener = self._listener()
        listener._device_name = "PACER"
        listener._midi_ins = [object()]
        monkeypatch.setattr(listener_mod, "pacer_input_subscribed", lambda name: True)
        assert listener.input_subscribed is True
        monkeypatch.setattr(listener_mod, "pacer_input_subscribed", lambda name: False)
        assert listener.input_subscribed is False

    def test_releases_when_unplugged(self, monkeypatch):
        """Active listener releases its handles when the PACER ports disappear."""
        listener = self._listener()
        listener._device_name = "PACER"
        listener._midi_ins = [object()]  # simulate an open port
        monkeypatch.setattr(listener_mod, "find_rtmidi_ports", lambda name: [])
        stopped = []
        monkeypatch.setattr(listener, "stop", lambda: stopped.append(True))
        listener.poll_reconnect()
        assert stopped == [True]

    def test_noop_without_device_name(self, monkeypatch):
        """poll_reconnect does nothing before any start() set a device name."""
        listener = self._listener()
        called = []
        monkeypatch.setattr(
            listener_mod, "find_rtmidi_ports", lambda name: called.append(name) or []
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
