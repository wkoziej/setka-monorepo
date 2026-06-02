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
        # delete() frees the ALSA seq client immediately; plain `del` leaks it.
        midi_in.delete()
    except Exception as e:
        logger.warning("Cannot enumerate rtmidi ports: %s", e)
        return None

    for i, port_name in enumerate(ports):
        if device_name.upper() in port_name.upper():
            logger.info("Found rtmidi port %d: %s", i, port_name)
            return i

    logger.warning("No rtmidi port matching '%s' in: %s", device_name, ports)
    return None


def find_rtmidi_ports(device_name: str) -> list[int]:
    """Find ALL rtmidi input port indices matching device_name.

    A single hardware device (e.g. PACER) often exposes several ports
    (MIDI1, MIDI2); Model A must read all of them.

    Returns:
        List of port indices for rtmidi.MidiIn.open_port() (possibly empty).
    """
    try:
        import rtmidi

        midi_in = rtmidi.MidiIn()
        ports = midi_in.get_ports()
        midi_in.delete()
    except Exception as e:
        logger.warning("Cannot enumerate rtmidi ports: %s", e)
        return []

    matches = [i for i, name in enumerate(ports) if device_name.upper() in name.upper()]
    if matches:
        logger.info(
            "Found %d rtmidi port(s) for '%s': %s", len(matches), device_name, matches
        )
    else:
        logger.warning("No rtmidi port matching '%s' in: %s", device_name, ports)
    return matches


def find_rtmidi_output_port(name_substring: str) -> int | None:
    """Find the first rtmidi OUTPUT port index whose name contains name_substring.

    Used to target a snd-virmidi port (visible to Bitwig as raw MIDI) for the
    bridge output. Returns None if no match.
    """
    try:
        import rtmidi

        midi_out = rtmidi.MidiOut()
        ports = midi_out.get_ports()
        midi_out.delete()
    except Exception as e:
        logger.warning("Cannot enumerate rtmidi output ports: %s", e)
        return None

    for i, port_name in enumerate(ports):
        if name_substring.upper() in port_name.upper():
            logger.info("Found rtmidi output port %d: %s", i, port_name)
            return i
    return None
