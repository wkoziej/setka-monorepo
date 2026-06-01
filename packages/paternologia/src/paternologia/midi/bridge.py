# ABOUTME: Virtual MIDI output port that fans PACER messages out to Bitwig.
# ABOUTME: Process-owned ALSA seq port (open_virtual_port); survives PACER replug.

import logging

import rtmidi

logger = logging.getLogger(__name__)

BRIDGE_PORT_NAME = "setka-bridge"


class MidiBridge:
    """Owns a virtual MIDI output port and forwards raw messages to it.

    The port is created by this process via python-rtmidi ``open_virtual_port``,
    so it lives as long as the process (independent of PACER replug) and is
    subscribable by other ALSA seq clients such as Bitwig. Using a stable name
    lets Bitwig re-match the port across process restarts.
    """

    def __init__(self, port_name: str = BRIDGE_PORT_NAME):
        self._port_name = port_name
        self._midi_out: rtmidi.MidiOut | None = None

    @property
    def port_name(self) -> str:
        return self._port_name

    @property
    def is_active(self) -> bool:
        return self._midi_out is not None

    def open(self) -> bool:
        """Create the virtual output port. Returns True on success."""
        try:
            self._midi_out = rtmidi.MidiOut()
            self._midi_out.open_virtual_port(self._port_name)
        except Exception as e:
            logger.warning(
                "Failed to open bridge virtual port '%s': %s", self._port_name, e
            )
            self._midi_out = None
            return False
        logger.info("MIDI bridge active on virtual port '%s'", self._port_name)
        return True

    def send(self, message) -> None:
        """Forward a raw MIDI message to the bridge port (no-op if inactive)."""
        if self._midi_out is None:
            return
        self._midi_out.send_message(message)

    def close(self) -> None:
        """Close and release the virtual output port."""
        if self._midi_out is not None:
            self._midi_out.close_port()
            # delete() frees the underlying ALSA seq client immediately; plain
            # `del` leaks it (reference cycle) and exhausts /dev/snd/seq.
            self._midi_out.delete()
            self._midi_out = None
            logger.info("MIDI bridge closed")
