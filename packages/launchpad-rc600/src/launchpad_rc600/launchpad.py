# ABOUTME: Pure Launchpad Mini (1st gen) model: pad note <-> (row, col), button kinds, LED colors.
# ABOUTME: Builds the LED messages (one pad, full 8x8 frame, reset); all on MIDI channel 1 (mido channel 0).
import mido

# Launchpad facts checked on the real device: pad note = row * 16 + col, row 0 is the top row,
# col 8 holds the right round buttons, the top round buttons are CC 104–111.
GRID = range(8)
RIGHT_BUTTON_COL = 8
TOP_BUTTONS = range(104, 112)
CHANNEL = 0
COLOR_RANGE = range(4)


def note_to_pad(note: int) -> tuple[int, int] | None:
    row, col = divmod(note, 16)
    if row in GRID and col in GRID:
        return row, col
    return None


def pad_to_note(row: int, col: int) -> int:
    if row not in GRID or col not in GRID:
        raise ValueError(f"pad ({row},{col}) outside the 8x8 grid")
    return row * 16 + col


def is_right_button(note: int) -> bool:
    row, col = divmod(note, 16)
    return row in GRID and col == RIGHT_BUTTON_COL


def is_top_button(cc: int) -> bool:
    return cc in TOP_BUTTONS


def color(red: int, green: int) -> int:
    """LED velocity = 16 * green + red + 12 (flags: copy + clear buffer); red and green 0–3."""
    if red not in COLOR_RANGE or green not in COLOR_RANGE:
        raise ValueError(f"color red={red} green={green}: each component must be 0–3")
    return 16 * green + red + 12


OFF = color(0, 0)
FADER_ON = color(0, 3)
FX_ON = color(3, 0)  # full red
FX_OFF = color(1, 1)  # dim amber


def led(row: int, col: int, velocity: int) -> mido.Message:
    return mido.Message(
        "note_on", channel=CHANNEL, note=pad_to_note(row, col), velocity=velocity
    )


def frame(colors: dict[tuple[int, int], int]) -> list[mido.Message]:
    return [led(row, col, colors.get((row, col), OFF)) for row in GRID for col in GRID]


def reset() -> mido.Message:
    """B0 00 00: turns off all LEDs."""
    return mido.Message("control_change", channel=CHANNEL, control=0, value=0)
