# ABOUTME: Read-back verification of a preset sent to the Pacer.
# ABOUTME: Dumps the preset via amidi (listener paused) and reports frames the Pacer did not store.

import subprocess
import time
from contextlib import AbstractContextManager, nullcontext
from tempfile import NamedTemporaryFile

from . import constants as c
from .sysex import PacerSysExBuilder

# Pacer potrzebuje chwili na zapis presetu przed odpowiedzią na dump.
SETTLE_SECONDS = 1.0
# amidi -t: koniec odbioru po tylu sekundach bez danych.
DUMP_IDLE_SECONDS = 2
# Twardy limit całego dumpu: szum z wejścia EXP Pacera potrafi nie dopuścić
# do ciszy, a listener jest w tym czasie wstrzymany.
DUMP_TIMEOUT_SECONDS = DUMP_IDLE_SECONDS + 6
# Pozycja bajtu obiektu: F0, Manufacturer ID, Device ID, CMD, target, preset.
_OBJECT_ID_OFFSET = 1 + len(c.MANUFACTURER_ID) + 4


def split_sysex_frames(data: bytes) -> list[bytes]:
    """Wytnij ramki F0…F7; bajty spoza SysEx (np. CC) i ramkę niedokończoną pomiń."""
    frames = []
    start = None
    for i, byte in enumerate(data):
        if byte == c.SYSEX_START:
            start = i
        elif byte == c.SYSEX_END and start is not None:
            frames.append(data[start : i + 1])
            start = None
    return frames


def missing_frames(sent: bytes, dump: bytes) -> list[bytes]:
    """Ramki wysłane, których nie ma w dumpie presetu.

    Ramkę nazwy pomijamy: Pacer zwraca nazwę w innym układzie (element 0x01
    z długością) niż przyjmuje (element 0x00).
    """
    stored = set(split_sysex_frames(dump))
    return [
        frame
        for frame in split_sysex_frames(sent)
        if frame[_OBJECT_ID_OFFSET] != c.CONTROL_NAME and frame not in stored
    ]


def read_back_preset(
    port: str,
    preset_index: int,
    pause_inputs: AbstractContextManager | None = None,
) -> bytes:
    """Pobierz dump presetu z Pacera przez amidi.

    Args:
        port: Port amidi (hw:X,Y,Z)
        preset_index: Indeks presetu (PRESET_INDICES)
        pause_inputs: Kontekst zwalniający wejścia Pacera na czas dumpu
            (subskrybent ALSA seq blokuje `amidi -r`: Device or resource busy)

    Raises:
        RuntimeError: amidi zakończył się błędem, przekroczył limit czasu
            albo nie jest zainstalowany.
    """
    request = PacerSysExBuilder(preset_index).build_preset_dump_request()
    time.sleep(SETTLE_SECONDS)
    with (
        pause_inputs or nullcontext(),
        NamedTemporaryFile(suffix=".syx") as dump_file,
    ):
        try:
            run = subprocess.run(
                [
                    "amidi",
                    "-p",
                    port,
                    "-S",
                    request.hex(" ").upper(),
                    "-r",
                    dump_file.name,
                    "-t",
                    str(DUMP_IDLE_SECONDS),
                ],
                capture_output=True,
                text=True,
                timeout=DUMP_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"amidi dump timed out after {DUMP_TIMEOUT_SECONDS}s"
            ) from e
        except FileNotFoundError as e:
            raise RuntimeError("amidi not found - install alsa-utils package") from e
        if run.returncode != 0:
            raise RuntimeError(f"amidi dump failed: {run.stderr.strip()}")
        return dump_file.read()
