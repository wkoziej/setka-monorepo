# ABOUTME: Display conversion: preset numbers via a hidden per-device offset, patterns
# ABOUTME: in canonical M:S spelling; bridges raw YAML values and what the user sees.

from paternologia.models import Device
from paternologia.pacer.mappings import PATTERN_ID, pattern_to_program


def to_display(value: int | str | None, device: Device) -> int | str | None:
    """Raw stored value → number shown to the user (device-screen number).

    Applies ``device.preset_display_offset`` only to integer preset values.
    Patterns (strings) and empty values pass through unchanged so callers can
    invoke this generically without branching on action type.
    """
    if isinstance(value, bool):  # bool is an int subclass; never an offset target
        return value
    if isinstance(value, int):
        return value + device.preset_display_offset
    return value


def to_stored(value: int | str | None, device: Device) -> int | str | None:
    """Number entered in the UI (device-screen number) → raw value to store.

    Inverse of :func:`to_display`. Callers parse form strings to ``int`` before
    calling for preset values; patterns and empty values pass through unchanged.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value - device.preset_display_offset
    return value


def pattern_display(value: int | str | None) -> int | str | None:
    """Pattern M:S w kanonicznej pisowni slotu: "d01" → "D01", "e9" → "E09", 48 → "D01".

    Wartość, która nie jest slotem A01-F16, zostaje bez zmian.
    """
    is_number = isinstance(value, int) or (isinstance(value, str) and value.isdigit())
    is_slot = isinstance(value, str) and bool(PATTERN_ID.match(value))
    if not (is_number or is_slot):
        return value
    program = pattern_to_program(value)
    if not 0 <= program <= 95:
        return value
    return f"{'ABCDEF'[program // 16]}{program % 16 + 1:02d}"
