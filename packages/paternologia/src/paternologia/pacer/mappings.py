# ABOUTME: Mapping Paternologia models to MIDI parameters for Pacer.
# ABOUTME: Converts Action types to SysEx message parameters.

import re

from ..models import Action, ActionType, Device
from . import constants as c

# Mapping note names to semitone offsets (C=0, C#=1, D=2, etc.)
NOTE_NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Pattern: note name (C-G, A-B), optional accidental (#/b), octave (-1 to 9)
NOTE_PATTERN = re.compile(r"^([A-Ga-g])([#b]?)(-?[0-9])$")


def note_to_midi(note: str | int) -> int:
    """Konwertuj notację muzyczną na numer nuty MIDI.

    Args:
        note: Notacja muzyczna (np. "C4", "F#3", "Bb5") lub numer MIDI (0-127)

    Returns:
        Numer nuty MIDI (0-127)

    Raises:
        ValueError: Gdy notacja jest nieprawidłowa lub nuta poza zakresem

    Konwersja: C4 = 60 (middle C), A4 = 69 (concert pitch)
    Formuła: midi_number = (octave + 1) * 12 + semitone
    """
    if isinstance(note, int):
        if note < 0 or note > 127:
            raise ValueError(f"Numer nuty MIDI musi być 0-127, otrzymano: {note}")
        return note

    # Numeryczny string (np. "60")
    try:
        midi_num = int(note)
        if midi_num < 0 or midi_num > 127:
            raise ValueError(f"Numer nuty MIDI musi być 0-127, otrzymano: {midi_num}")
        return midi_num
    except ValueError:
        pass

    # Notacja muzyczna (np. "C4", "F#3")
    match = NOTE_PATTERN.match(note)
    if not match:
        raise ValueError(f"Nieprawidłowa notacja nuty: {note}")

    note_name, accidental, octave_str = match.groups()
    semitone = NOTE_NAMES[note_name.upper()]

    if accidental == "#":
        semitone += 1
    elif accidental == "b":
        semitone -= 1

    octave = int(octave_str)
    midi_number = (octave + 1) * 12 + semitone

    if midi_number < 0 or midi_number > 127:
        raise ValueError(f"Nuta {note} poza zakresem MIDI (0-127): {midi_number}")

    return midi_number


def build_device_channel_map(devices: list[Device]) -> dict[str, int]:
    """Buduj mapę device_id → MIDI channel z listy urządzeń.

    Używa Device.midi_channel z modelu.
    """
    channel_map = {}
    for device in devices:
        channel_map[device.id] = device.midi_channel
    return channel_map


def get_device_channel(device_id: str, channel_map: dict[str, int]) -> int:
    """Get MIDI channel for device, fallback to 0 if unknown."""
    return channel_map.get(device_id, 0)


def pattern_to_program(value: int | str | None) -> int:
    """Konwertuj pattern ID na Program Change number.

    Obsługuje formaty:
    - int: bezpośrednio jako program number (np. 77 → 77)
    - str numeryczny: konwertuje na int (np. "77" → 77)
    - str alfanumeryczny: M:S format A01-F16 (np. "D1" → 48)

    M:S mapping: A01-A16 (0-15), B01-B16 (16-31), ..., F01-F16 (80-95)
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Najpierw sprawdź czy to czysta liczba (np. "77")
        try:
            return int(value)
        except ValueError:
            pass
        # Format "A01", "B02", "D1", etc.
        if len(value) >= 2 and value[0].isalpha():
            bank = ord(value[0].upper()) - ord("A")  # A=0, B=1, ..., F=5
            if bank < 0 or bank > 5:
                return 0  # Invalid bank (not A-F)
            try:
                pattern = int(value[1:]) - 1  # 01→0, 02→1, ..., 16→15
                if pattern < 0 or pattern > 15:
                    return 0  # Invalid pattern number
                return bank * 16 + pattern
            except ValueError:
                return 0
    return 0  # fallback


def action_to_midi(
    action: Action, device_channel_map: dict[str, int]
) -> tuple[int, int, int, int, int]:
    """Konwertuj Action na parametry MIDI.

    Args:
        action: Akcja do skonwertowania
        device_channel_map: Mapa device_id → MIDI channel

    Returns:
        (msg_type, channel, data1, data2, data3)

    Dla MSG_SW_PRG_STEP: data1=unused, data2=start, data3=end (start=end dla immediate)
    Dla MSG_SW_MIDI_CC: data1=controller, data2=down (naciśnięcie), data3=up (puszczenie)
    """
    channel = get_device_channel(action.device, device_channel_map)

    if action.type == ActionType.PRESET:
        program = action.value if isinstance(action.value, int) else 0

        # MSG_SW_PRG_BANK wysyła Program Change + Bank Select
        # MSG_SW_PRG_STEP jest do stepowania przez zakresy (nie do pojedynczych PC!)
        # Format: data1=program (0-127), data2=bank LSB, data3=bank MSB
        bank_msb = program // 128
        prog = program % 128
        return (
            c.MSG_SW_PRG_BANK,
            channel,
            prog,  # data1 = program (0-127)
            0,  # data2 = bank LSB
            bank_msb,  # data3 = bank MSB
        )

    elif action.type == ActionType.PATTERN:
        # Pattern na Model:Samples = Program Step
        # M:S używa PC 0-95 do wyboru pattern 1-96
        program = pattern_to_program(action.value)
        return (c.MSG_SW_PRG_STEP, channel, 0, program, program)

    elif action.type == ActionType.CC:
        # CC Trigger dla stompswitch: data1=controller, data2=down, data3=up
        # Wysyła wartość "down" przy naciśnięciu przycisku, "up" przy puszczeniu
        # Dla RC-600 w trybie MOMENT: down=127 (ON), up=0 (OFF)
        cc_value = action.value if isinstance(action.value, int) else 127
        return (c.MSG_SW_MIDI_CC, channel, action.cc or 0, cc_value, 0)

    elif action.type == ActionType.NOTE:
        # Note: data1=note, data2=velocity, data3=unused
        midi_note = note_to_midi(action.note) if action.note else 60
        velocity = action.velocity if action.velocity else 100
        return (c.MSG_SW_NOTE, channel, midi_note, velocity, 0)

    else:
        raise ValueError(f"Nieobsługiwany typ akcji: {action.type}")
