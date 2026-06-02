# ABOUTME: Virtual MIDI output port that fans PACER messages out to Bitwig.
# ABOUTME: Process-owned ALSA seq port (open_virtual_port); survives PACER replug.

import logging

import rtmidi

from paternologia.midi.ports import find_rtmidi_output_port

logger = logging.getLogger(__name__)

BRIDGE_PORT_NAME = "setka-bridge"
# Bitwig (and most Linux DAWs) only see hardware/rawmidi ports, not virtual ALSA
# seq ports. snd-virmidi exposes Bitwig-visible raw ports; the bridge targets the
# first one. Bitwig must then read "Virtual Raw MIDI 1".
VIRMIDI_PORT_HINT = "VirMIDI"


class MidiBridge:
    """Forwards raw PACER messages to a Bitwig-visible MIDI output port.

    Preferred target is a snd-virmidi port (raw MIDI, visible to Bitwig). When no
    virmidi port exists, it falls back to a process-owned virtual seq port
    (``open_virtual_port``) — usable by seq-aware consumers but invisible to Bitwig.
    Either way the port is owned by this process, so it survives PACER replug.
    """

    def __init__(
        self, port_name: str = BRIDGE_PORT_NAME, virmidi_hint: str = VIRMIDI_PORT_HINT
    ):
        self._port_name = port_name
        self._virmidi_hint = virmidi_hint
        self._midi_out: rtmidi.MidiOut | None = None
        self._mode: str | None = None  # "virmidi" | "virtual"

    @property
    def port_name(self) -> str:
        return self._port_name

    @property
    def is_active(self) -> bool:
        return self._midi_out is not None

    @property
    def mode(self) -> str | None:
        """How the bridge is exposed: 'virmidi' (Bitwig-visible) or 'virtual'."""
        return self._mode

    def open(self) -> bool:
        """Open the bridge output port. Returns True on success."""
        try:
            self._midi_out = rtmidi.MidiOut()
            virmidi_idx = find_rtmidi_output_port(self._virmidi_hint)
            if virmidi_idx is not None:
                self._midi_out.open_port(virmidi_idx)
                self._mode = "virmidi"
                logger.info(
                    "MIDI bridge → virmidi port idx %d (Bitwig-visible)", virmidi_idx
                )
            else:
                self._midi_out.open_virtual_port(self._port_name)
                self._mode = "virtual"
                logger.info(
                    "MIDI bridge → virtual seq port '%s' (no virmidi; Bitwig won't see it)",
                    self._port_name,
                )
        except Exception as e:
            logger.warning("Failed to open bridge output: %s", e)
            self._midi_out = None
            self._mode = None
            return False
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
            self._mode = None
            logger.info("MIDI bridge closed")
