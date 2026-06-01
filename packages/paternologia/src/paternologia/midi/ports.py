# ABOUTME: MIDI port detection utilities for amidi (SysEx) and rtmidi (live input).
# ABOUTME: Shared by pacer router (amidi) and MIDI listener (rtmidi).

import logging
import subprocess

logger = logging.getLogger(__name__)


def find_amidi_port(device_name: str) -> str | None:
    """Find amidi port by device name (parses `amidi -l` output).

    Args:
        device_name: Fragment of device name to search for (e.g. "PACER")

    Returns:
        Port string like "hw:4,0,0" or None if not found.
    """
    try:
        result = subprocess.run(
            ["amidi", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.strip().split("\n"):
            if device_name.upper() in line.upper():
                parts = line.split()
                if len(parts) >= 2 and parts[1].startswith("hw:"):
                    return parts[1]
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def find_rtmidi_port(device_name: str) -> int | None:
    """Find rtmidi input port index by device name.

    Args:
        device_name: Fragment of device name to search for (e.g. "PACER")

    Returns:
        Port index for rtmidi.MidiIn.open_port() or None if not found.
    """
    try:
        import rtmidi

        midi_in = rtmidi.MidiIn()
        ports = midi_in.get_ports()
        del midi_in
    except Exception as e:
        logger.warning("Cannot enumerate rtmidi ports: %s", e)
        return None

    for i, port_name in enumerate(ports):
        if device_name.upper() in port_name.upper():
            logger.info("Found rtmidi port %d: %s", i, port_name)
            return i

    logger.warning("No rtmidi port matching '%s' in: %s", device_name, ports)
    return None
