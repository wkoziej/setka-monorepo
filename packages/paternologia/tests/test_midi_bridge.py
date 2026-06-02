# ABOUTME: Tests for the MIDI bridge (virtual output port) and listener fan-out.
# ABOUTME: Verifies raw forwarding to the bridge port and PC->song-change publishing.

import asyncio

import pytest
import rtmidi

from paternologia.midi.bridge import MidiBridge
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
        mo = rtmidi.MidiOut()
        mo.open_virtual_port("test")
        mo.close_port()
        del mo
        return True
    except Exception:
        return False


requires_alsa = pytest.mark.skipif(
    not _has_alsa(), reason="ALSA not available (CI or non-Linux)"
)


def _make_device(device_id: str, midi_channel: int) -> Device:
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


def _open_reader(port_name: str) -> rtmidi.MidiIn:
    """Open a MidiIn subscribed to the bridge's virtual output port."""
    reader = rtmidi.MidiIn()
    # Listen to everything, including realtime, so negative tests are meaningful.
    reader.ignore_types(sysex=False, timing=False, active_sense=False)
    idx = next((i for i, n in enumerate(reader.get_ports()) if port_name in n), None)
    assert idx is not None, f"Bridge port '{port_name}' not in {reader.get_ports()}"
    reader.open_port(idx)
    return reader


def _open_writer(port_name: str) -> rtmidi.MidiOut:
    """Open a MidiOut connected to the listener's virtual input port."""
    writer = rtmidi.MidiOut()
    idx = next((i for i, n in enumerate(writer.get_ports()) if port_name in n), None)
    assert idx is not None, f"Listener port '{port_name}' not in {writer.get_ports()}"
    writer.open_port(idx)
    return writer


async def _wait_message(reader: rtmidi.MidiIn, timeout: float = 2.0) -> list | None:
    """Poll the reader for an incoming MIDI message within timeout seconds."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        msg = reader.get_message()
        if msg is not None:
            return msg[0]
        await asyncio.sleep(0.01)
    return None


class TestMidiBridgeUnit:
    """Tests that do not require a full ALSA loopback."""

    def test_default_port_name_is_stable(self):
        """The bridge exposes a stable default port name across instances."""
        assert MidiBridge().port_name == MidiBridge().port_name

    def test_send_when_inactive_is_noop(self):
        """Sending before open() must not raise."""
        bridge = MidiBridge("setka-bridge-inactive", virmidi_hint="__no_virmidi_test__")
        assert bridge.is_active is False
        bridge.send([0xB0, 1, 1])  # no exception

    def test_open_prefers_virmidi(self, monkeypatch):
        """When a virmidi port exists, the bridge opens it (Bitwig-visible)."""
        from paternologia.midi import bridge as bridge_mod

        opened = {}

        class FakeOut:
            def open_port(self, idx):
                opened["port"] = idx

            def open_virtual_port(self, name):
                opened["virtual"] = name

        monkeypatch.setattr(bridge_mod.rtmidi, "MidiOut", FakeOut)
        monkeypatch.setattr(bridge_mod, "find_rtmidi_output_port", lambda hint: 3)
        bridge = MidiBridge("setka-x", virmidi_hint="VirMIDI")
        assert bridge.open() is True
        assert bridge.mode == "virmidi"
        assert opened == {"port": 3}

    def test_open_falls_back_to_virtual(self, monkeypatch):
        """Without a virmidi port, the bridge creates its own virtual seq port."""
        from paternologia.midi import bridge as bridge_mod

        opened = {}

        class FakeOut:
            def open_port(self, idx):
                opened["port"] = idx

            def open_virtual_port(self, name):
                opened["virtual"] = name

        monkeypatch.setattr(bridge_mod.rtmidi, "MidiOut", FakeOut)
        monkeypatch.setattr(bridge_mod, "find_rtmidi_output_port", lambda hint: None)
        bridge = MidiBridge("setka-x", virmidi_hint="nope")
        assert bridge.open() is True
        assert bridge.mode == "virtual"
        assert opened == {"virtual": "setka-x"}


@requires_alsa
class TestMidiBridgeLoopback:
    """Integration tests using ALSA virtual MIDI ports."""

    def test_open_creates_subscribable_port(self):
        """open() creates a virtual port visible to other ALSA seq clients."""
        bridge = MidiBridge("setka-bridge-open", virmidi_hint="__no_virmidi_test__")
        try:
            assert bridge.open() is True
            assert bridge.is_active is True
            reader = rtmidi.MidiIn()
            assert any("setka-bridge-open" in n for n in reader.get_ports())
            reader.delete()
        finally:
            bridge.close()
            assert bridge.is_active is False

    async def test_cc_forwarded_byte_for_byte(self):
        """A CC message arrives byte-for-byte on the bridge port."""
        bridge = MidiBridge("setka-bridge-cc", virmidi_hint="__no_virmidi_test__")
        index = SongMidiIndex.build([], [])
        bus = EventBus()
        bus.set_loop(asyncio.get_running_loop())
        listener = MidiListener(song_index=index, event_bus=bus, bridge=bridge)

        assert bridge.open()
        listener.start_virtual("pacer-in-cc")
        reader = _open_reader("setka-bridge-cc")
        writer = _open_writer("pacer-in-cc")
        try:
            writer.send_message([0xB0, 7, 100])
            received = await _wait_message(reader)
            assert received == [0xB0, 7, 100]
        finally:
            writer.close_port()
            writer.delete()
            reader.close_port()
            reader.delete()
            listener.stop()
            bridge.close()

    async def test_pc_forwarded_and_published(self):
        """A Program Change is both forwarded raw and published as song-change."""
        bridge = MidiBridge("setka-bridge-pc", virmidi_hint="__no_virmidi_test__")
        devices = [_make_device("boss", midi_channel=13)]  # channel index 12
        index = SongMidiIndex.build([_make_song("zen", "boss", 2)], devices)
        bus = EventBus()
        bus.set_loop(asyncio.get_running_loop())
        listener = MidiListener(song_index=index, event_bus=bus, bridge=bridge)

        assert bridge.open()
        listener.start_virtual("pacer-in-pc")
        reader = _open_reader("setka-bridge-pc")
        writer = _open_writer("pacer-in-pc")
        try:
            queue = bus.subscribe()
            writer.send_message([0xCC, 2])  # PC channel 12, program 2

            received = await _wait_message(reader)
            assert received == [0xCC, 2]

            event = await asyncio.wait_for(queue.get(), timeout=2.0)
            assert event.song_id == "zen"
            assert event.channel == 12
            assert event.program == 2
        finally:
            writer.close_port()
            writer.delete()
            reader.close_port()
            reader.delete()
            listener.stop()
            bridge.close()

    async def test_note_forwarded_but_not_published(self):
        """Non-PC messages (e.g. Note On) are forwarded but never published."""
        bridge = MidiBridge("setka-bridge-note", virmidi_hint="__no_virmidi_test__")
        index = SongMidiIndex.build([], [])
        bus = EventBus()
        bus.set_loop(asyncio.get_running_loop())
        listener = MidiListener(song_index=index, event_bus=bus, bridge=bridge)

        assert bridge.open()
        listener.start_virtual("pacer-in-note")
        reader = _open_reader("setka-bridge-note")
        writer = _open_writer("pacer-in-note")
        try:
            queue = bus.subscribe()
            writer.send_message([0x9C, 60, 100])  # Note On

            received = await _wait_message(reader)
            assert received == [0x9C, 60, 100]

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(queue.get(), timeout=0.5)
        finally:
            writer.close_port()
            writer.delete()
            reader.close_port()
            reader.delete()
            listener.stop()
            bridge.close()

    async def test_realtime_not_forwarded(self):
        """System Real-Time messages (>=0xF8) are not relayed to the bridge."""
        bridge = MidiBridge("setka-bridge-rt", virmidi_hint="__no_virmidi_test__")
        index = SongMidiIndex.build([], [])
        bus = EventBus()
        bus.set_loop(asyncio.get_running_loop())
        listener = MidiListener(song_index=index, event_bus=bus, bridge=bridge)

        assert bridge.open()
        listener.start_virtual("pacer-in-rt")
        reader = _open_reader("setka-bridge-rt")
        writer = _open_writer("pacer-in-rt")
        try:
            writer.send_message([0xF8])  # MIDI clock
            received = await _wait_message(reader, timeout=0.5)
            assert received is None
        finally:
            writer.close_port()
            writer.delete()
            reader.close_port()
            reader.delete()
            listener.stop()
            bridge.close()

    def test_bridge_active_even_without_pacer(self):
        """Bridge opens its output port even when no PACER input exists."""
        bridge = MidiBridge("setka-bridge-nopacer", virmidi_hint="__no_virmidi_test__")
        index = SongMidiIndex.build([], [])
        bus = EventBus()
        listener = MidiListener(song_index=index, event_bus=bus, bridge=bridge)
        try:
            assert bridge.open() is True
            # No such hardware device -> listener stays inactive, no crash.
            assert listener.start("DEFINITELY-NO-SUCH-DEVICE") is False
            assert bridge.is_active is True
        finally:
            bridge.close()
