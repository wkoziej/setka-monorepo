# ABOUTME: MIDI listener using python-rtmidi for live song detection.
# ABOUTME: Listens for Program Change messages and publishes events via EventBus.

import logging

import rtmidi

from paternologia.midi.events import EventBus, MidiEvent
from paternologia.midi.index import SongMidiIndex
from paternologia.midi.ports import find_rtmidi_port

logger = logging.getLogger(__name__)


class MidiListener:
    """Listens for MIDI Program Change and publishes matching song events."""

    def __init__(self, song_index: SongMidiIndex, event_bus: EventBus):
        self._index = song_index
        self._bus = event_bus
        self._midi_in: rtmidi.MidiIn | None = None

    @property
    def song_index(self) -> SongMidiIndex:
        return self._index

    @song_index.setter
    def song_index(self, index: SongMidiIndex) -> None:
        self._index = index

    def start(self, device_name: str) -> bool:
        """Start listening on the first port matching device_name.

        Returns True if port found and opened, False otherwise.
        """
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
            del self._midi_in
            self._midi_in = None
            logger.info("MIDI listener stopped")

    def _callback(self, event, data=None) -> None:
        """rtmidi callback - called from a separate thread."""
        message, _deltatime = event
        if len(message) < 2:
            return

        status = message[0]
        # Program Change: 0xCn where n is channel (0-15)
        if (status & 0xF0) != 0xC0:
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
