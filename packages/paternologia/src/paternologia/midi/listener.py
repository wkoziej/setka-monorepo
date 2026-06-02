# ABOUTME: MIDI listener using python-rtmidi for live song detection.
# ABOUTME: Listens for Program Change messages and publishes events via EventBus.

import logging

import rtmidi

from paternologia.midi.bridge import MidiBridge
from paternologia.midi.events import EventBus, MidiEvent
from paternologia.midi.index import SongMidiIndex
from paternologia.midi.ports import find_rtmidi_ports

logger = logging.getLogger(__name__)

# System Real-Time messages (clock, start/stop, active sensing, reset) start here.
_SYSTEM_REALTIME_MIN = 0xF8


class MidiListener:
    """Listens for MIDI Program Change and publishes matching song events."""

    def __init__(
        self,
        song_index: SongMidiIndex,
        event_bus: EventBus,
        bridge: MidiBridge | None = None,
    ):
        self._index = song_index
        self._bus = event_bus
        self._bridge = bridge
        self._midi_ins: list[rtmidi.MidiIn] = []
        self._device_name: str | None = None
        self._on_record_trigger = None
        self._trigger_channel: int | None = None
        self._start_note: int | None = None
        self._stop_note: int | None = None

    def configure_record_trigger(
        self, channel: int, start_note: int, stop_note: int, callback
    ) -> None:
        """Wire PACER record triggers: Note On(start/stop) on `channel` -> callback.

        callback is invoked from the rtmidi C thread with "start" / "stop"; the
        caller is responsible for marshalling off this thread (network I/O).
        """
        self._trigger_channel = channel
        self._start_note = start_note
        self._stop_note = stop_note
        self._on_record_trigger = callback

    @property
    def song_index(self) -> SongMidiIndex:
        return self._index

    @song_index.setter
    def song_index(self, index: SongMidiIndex) -> None:
        self._index = index

    @property
    def is_active(self) -> bool:
        """True when at least one hardware input port is currently open."""
        return len(self._midi_ins) > 0

    def start(self, device_name: str) -> bool:
        """Open ALL ports matching device_name (e.g. PACER MIDI1 + MIDI2).

        A footswitch trigger may arrive on a secondary port (a note on MIDI2),
        so Model A must read every matching port. Returns True if any opened.
        """
        self._device_name = device_name
        port_indices = find_rtmidi_ports(device_name)
        if not port_indices:
            logger.warning(
                "MIDI port for '%s' not found, listener inactive", device_name
            )
            return False

        for port_idx in port_indices:
            try:
                midi_in = rtmidi.MidiIn()
                midi_in.open_port(port_idx)
                midi_in.set_callback(self._callback)
                self._midi_ins.append(midi_in)
                logger.info(
                    "MIDI listener started on port %d (%s)", port_idx, device_name
                )
            except Exception as e:
                logger.warning("Failed to open MIDI port %d: %s", port_idx, e)

        return self.is_active

    def start_virtual(self, port_name: str) -> None:
        """Start listening on a virtual MIDI port (for testing)."""
        midi_in = rtmidi.MidiIn()
        midi_in.open_virtual_port(port_name)
        midi_in.set_callback(self._callback)
        self._midi_ins.append(midi_in)
        logger.info("MIDI listener started on virtual port '%s'", port_name)

    def stop(self) -> None:
        """Stop listening and close all MIDI ports."""
        if not self._midi_ins:
            return
        for midi_in in self._midi_ins:
            midi_in.close_port()
            # delete() frees the underlying ALSA seq client immediately; plain
            # `del` leaks it (reference cycle) and exhausts /dev/snd/seq.
            midi_in.delete()
        self._midi_ins.clear()
        logger.info("MIDI listener stopped")

    def poll_reconnect(self) -> None:
        """Reopen the PACER inputs after replug, or release stale handles.

        ALSA port indices shift on replug, so we re-match by name. The bridge
        output port is unaffected and stays open the whole time.
        """
        if self._device_name is None:
            return
        ports_present = bool(find_rtmidi_ports(self._device_name))
        if self.is_active and not ports_present:
            logger.warning(
                "PACER '%s' disappeared; releasing inputs", self._device_name
            )
            self.stop()
        elif not self.is_active and ports_present:
            logger.info("PACER '%s' reappeared; reopening inputs", self._device_name)
            self.start(self._device_name)

    def _callback(self, event, data=None) -> None:
        """rtmidi callback - called from a separate thread."""
        message, _deltatime = event
        if not message:
            return

        status = message[0]

        # Fan-out (Model A): relay everything except System Real-Time to the
        # bridge so Bitwig sees the full PACER stream (CC/PC/Note triggers).
        if self._bridge is not None and status < _SYSTEM_REALTIME_MIN:
            self._bridge.send(message)

        # Record triggers: Note On (velocity > 0) on the configured channel/notes.
        if (
            self._on_record_trigger is not None
            and (status & 0xF0) == 0x90
            and len(message) >= 3
            and message[2] > 0
            and (status & 0x0F) == self._trigger_channel
        ):
            if message[1] == self._start_note:
                logger.info("PACER record trigger: START")
                self._on_record_trigger("start")
            elif message[1] == self._stop_note:
                logger.info("PACER record trigger: STOP")
                self._on_record_trigger("stop")

        # Program Change: 0xCn where n is channel (0-15)
        if len(message) < 2 or (status & 0xF0) != 0xC0:
            return

        channel = status & 0x0F
        program = message[1]

        logger.debug("Program Change: ch=%d prog=%d", channel, program)

        song_id = self._index.lookup(channel, program)
        if song_id is None:
            logger.debug("No song mapped to ch=%d prog=%d", channel, program)
            return

        logger.info("MIDI → song '%s' (ch=%d, prog=%d)", song_id, channel, program)
        self._bus.publish_threadsafe(
            MidiEvent(
                song_id=song_id,
                channel=channel,
                program=program,
            )
        )
