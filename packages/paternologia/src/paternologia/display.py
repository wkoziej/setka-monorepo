# ABOUTME: Display-number conversion for preset values using a hidden per-device offset.
# ABOUTME: Bridges the raw MIDI value stored in YAML and the number shown on the device.

from paternologia.models import Device


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
