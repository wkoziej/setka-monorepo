# ABOUTME: MIDI listener using python-rtmidi for live song detection.
# ABOUTME: Listens for Program Change messages and publishes events via EventBus.

import logging

import rtmidi

from paternologia.midi.bridge import MidiBridge
from paternologia.midi.events import EventBus, MidiEvent
from paternologia.midi.index import SongMidiIndex
from paternologia.midi.ports import find_rtmidi_port

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
        self._midi_in: rtmidi.MidiIn | None = None
        self._device_name: str | None = None

    @property
    def song_index(self) -> SongMidiIndex:
        return self._index

    @song_index.setter
    def song_index(self, index: SongMidiIndex) -> None:
        self._index = index

    @property
    def is_active(self) -> bool:
        """True when a hardware input port is currently open."""
        return self._midi_in is not None

    def start(self, device_name: str) -> bool:
        """Start listening on the first port matching device_name.

        Returns True if port found and opened, False otherwise.
        """
        self._device_name = device_name
        port_idx = find_rtmidi_port(device_name)
        if port_idx is None:
            logger.warning(
                "MIDI port for '%s' not found, listener inactive", device_name
            )
            return False

        try:
            self._midi_in = rtmidi.MidiIn()
            self._midi_in.open_port(port_idx)
            self._midi_in.set_callback(self._callback)
        except Exception as e:
            logger.warning("Failed to open MIDI port %d: %s", port_idx, e)
            self._midi_in = None
            return False

        logger.info("MIDI listener started on port %d (%s)", port_idx, device_name)
        return True

    def start_virtual(self, port_name: str) -> None:
        """Start listening on a virtual MIDI port (for testing)."""
        self._midi_in = rtmidi.MidiIn()
        self._midi_in.open_virtual_port(port_name)
        self._midi_in.set_callback(self._callback)
        logger.info("MIDI listener started on virtual port '%s'", port_name)

    def stop(self) -> None:
        """Stop listening and close MIDI port."""
        if self._midi_in is not None:
            self._midi_in.close_port()
            # delete() frees the underlying ALSA seq client immediately; plain
            # `del` leaks it (reference cycle) and exhausts /dev/snd/seq.
            self._midi_in.delete()
            self._midi_in = None
            logger.info("MIDI listener stopped")

    def poll_reconnect(self) -> None:
        """Reopen the PACER input after replug, or release a stale handle.

        ALSA port indices shift on replug, so we re-match by name. The bridge
        output port is unaffected and stays open the whole time.
        """
        if self._device_name is None:
            return
        port_present = find_rtmidi_port(self._device_name) is not None
        if self.is_active and not port_present:
            logger.warning("PACER '%s' disappeared; releasing input", self._device_name)
            self.stop()
        elif not self.is_active and port_present:
            logger.info("PACER '%s' reappeared; reopening input", self._device_name)
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
