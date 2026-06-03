# ABOUTME: MIDI port detection utilities for amidi (SysEx) and rtmidi (live input).
# ABOUTME: Shared by pacer router (amidi) and MIDI listener (rtmidi).

import logging
import os
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


def pacer_input_subscribed(device_name: str) -> bool:
    """True if device_name's MIDI OUTPUT still has a live ALSA subscription.

    rtmidi keeps a MidiIn handle "open" after the device re-enumerates (replug,
    suspend/resume, card-number change), but ALSA silently drops the
    subscription — so the open-handle count is NOT an honest signal that input
    actually flows. The reliable signal is whether the device's output port is
    still subscribed by a consumer, which we read from `aconnect -l`.

    Assumes the live rig is the single consumer of the device's output (true for
    PACER -> bridge). aconnect runs under LC_ALL=C for stable English labels
    ("Connecting To:"). On any failure (aconnect missing/erroring) returns True,
    degrading to the handle-based behaviour instead of churning reconnects.
    """
    try:
        result = subprocess.run(
            ["aconnect", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True
    if result.returncode != 0:
        return True

    in_device_block = False
    for line in result.stdout.splitlines():
        if line.startswith("client "):
            # A new client header ends the previous block; match by device name.
            in_device_block = device_name.upper() in line.upper()
            continue
        if in_device_block and line.strip().startswith("Connecting To:"):
            return True
    return False


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
