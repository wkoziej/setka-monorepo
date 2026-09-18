# ABOUTME: Native cross-platform SysEx sender for Nektar Pacer, replacing amidi.
# ABOUTME: Parses a .syx blob into frames and sends them via python-rtmidi (CoreMIDI/ALSA seq).

import logging
import time

from .ports import find_rtmidi_output_port
from ..pacer import constants as c

logger = logging.getLogger(__name__)


class PacerPortNotFoundError(Exception):
    """Raised when no rtmidi output port matches the configured device name."""

    def __init__(self, device_name: str):
        self.device_name = device_name
        super().__init__(f"No MIDI output port found for device '{device_name}'")


def split_sysex_messages(data: bytes) -> list[bytes]:
    """Split a raw .syx blob into individual complete SysEx frames.

    Scans for 0xF0 ... 0xF7 boundaries — the same framing `pacer/sysex.py`
    builds and `pacer/export.py` concatenates via `b"".join`.

    Returns:
        List of frames (each including its own 0xF0/0xF7 bytes), in order.
        Empty list for an empty blob.

    Raises:
        ValueError: a frame starts (0xF0) but the blob ends before 0xF7 is
            found (truncated file), or a byte outside a frame isn't 0xF0.
    """
    frames = []
    i = 0
    n = len(data)
    while i < n:
        if data[i] != c.SYSEX_START:
            raise ValueError(
                f"Expected SysEx start 0x{c.SYSEX_START:02x} at offset {i}, "
                f"found 0x{data[i]:02x}"
            )
        end = data.find(bytes([c.SYSEX_END]), i)
        if end == -1:
            raise ValueError(
                f"Truncated SysEx frame starting at offset {i}: missing 0xF7"
            )
        frames.append(data[i : end + 1])
        i = end + 1
    return frames


def send_sysex(data: bytes, device_name: str, interval_ms: int) -> str | None:
    """Send a .syx blob to device_name via rtmidi, paced by interval_ms.

    Replaces `amidi -p <port> --sysex-interval=<ms> -s <file>`: splits data
    into frames and sends each via `send_message()`, sleeping `interval_ms`
    between messages (not after the last one) — identical pacing semantics
    to `amidi --sysex-interval` (per-message, not per-byte).

    Args:
        data: Raw SysEx bytes (as produced by `export_song_to_syx()`).
        device_name: Fragment of the rtmidi output port name to match.
        interval_ms: Milliseconds to sleep between messages.

    Returns:
        The rtmidi port name the data was sent to, or None if `data`
        contained no SysEx frames (no port is opened in that case).

    Raises:
        ValueError: `data` is malformed (see `split_sysex_messages`).
        PacerPortNotFoundError: no output port matches `device_name`.
        Exception: whatever `rtmidi` raises on `open_port`/`send_message`
            (e.g. device unplugged mid-send) — propagated after the port is
            always released via `close_port()` + `delete()`.
    """
    frames = split_sysex_messages(data)
    if not frames:
        logger.warning("send_sysex: no SysEx frames in data, nothing to send")
        return None

    port_idx = find_rtmidi_output_port(device_name)
    if port_idx is None:
        raise PacerPortNotFoundError(device_name)

    import rtmidi

    midi_out = rtmidi.MidiOut()
    try:
        port_name = midi_out.get_ports()[port_idx]
        midi_out.open_port(port_idx)
        interval_s = interval_ms / 1000
        last_index = len(frames) - 1
        for i, frame in enumerate(frames):
            midi_out.send_message(list(frame))
            if i != last_index:
                time.sleep(interval_s)
        logger.info("Sent %d SysEx frame(s) to '%s'", len(frames), port_name)
        return port_name
    finally:
        # delete() frees the underlying ALSA seq/CoreMIDI client immediately;
        # plain `del` leaks it (same pattern as MidiBridge.close()).
        midi_out.close_port()
        midi_out.delete()
