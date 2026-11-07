# ABOUTME: Pure translator core: Launchpad pad presses -> RC-600 CC on channel 13, LED messages, log lines.
# ABOUTME: Holds 6 track levels and 4 Track FX flags; CC numbers come from the ASSIGN config. No I/O.
from dataclasses import dataclass, field

import mido

from launchpad_rc600 import launchpad
from launchpad_rc600.assign import (
    CONTROL_CHANNEL,
    FX_TARGETS,
    LEVEL_TARGETS,
    AssignConfig,
)

# Index 0 is the bottom row (row 7), index 7 is the top row (row 0).
LEVELS = (0, 14, 29, 43, 57, 71, 86, 100)
START_LEVEL = 57  # about 57%, leaves room to raise to unity (100)
FADER_COLS = range(len(LEVEL_TARGETS))
# FX pads: 2x2 block in the top right corner. A B / C D.
FX_PADS = {(0, 6): 0, (0, 7): 1, (1, 6): 2, (1, 7): 3}
FX_ON_VALUE = 127
FX_OFF_VALUE = 0
LAUNCHPAD_CHANNEL = 0
RC600_CHANNEL = CONTROL_CHANNEL - 1  # mido channels are 0-based

# Level -> CC value. Linear rule ACT 0–127 -> 0–100; the values give the same level with floor
# and with round where such a value exists. For 71 and 86 only the round values (90, 109) work;
# the real RC-600 rounding is a deferred check on the device.
_LEVEL_CC = dict(zip(LEVELS, (0, 18, 37, 55, 73, 90, 109, 127)))


def cc_for_level(level: int) -> int:
    if level not in _LEVEL_CC:
        raise ValueError(f"level {level} is not one of {LEVELS}")
    return _LEVEL_CC[level]


def _level_for_row(row: int) -> int:
    return LEVELS[7 - row]


def _row_for_level(level: int) -> int:
    return 7 - LEVELS.index(level)


@dataclass
class Output:
    rc600: list[mido.Message] = field(default_factory=list)
    leds: list[mido.Message] = field(default_factory=list)
    log: list[str] = field(default_factory=list)


def _ignored(reason: str) -> Output:
    return Output(log=[f"ignored: {reason}"])


class Translator:
    def __init__(self, config: AssignConfig):
        self.levels = [START_LEVEL] * len(LEVEL_TARGETS)
        self.fx = [False] * len(FX_TARGETS)
        self._level_cc = [config.slot_for_target(t).source_cc for t in LEVEL_TARGETS]
        self._fx_cc = [config.slot_for_target(t).source_cc for t in FX_TARGETS]

    def startup(self) -> Output:
        rc600 = [
            self._cc(self._level_cc[n], cc_for_level(level))
            for n, level in enumerate(self.levels)
        ]
        rc600 += [
            self._cc(self._fx_cc[n], self._fx_value(on)) for n, on in enumerate(self.fx)
        ]
        log = [f"startup: TRK1–6 LEVEL {self.levels}, T FX A–D {self.fx}"]
        return Output(rc600, launchpad.frame(self._colors()), log)

    def handle(self, msg: mido.Message) -> Output:
        if not hasattr(msg, "channel"):
            return _ignored(f"{msg.type} is not a pad press")
        if msg.channel != LAUNCHPAD_CHANNEL:
            return _ignored(
                f"{msg.type} on channel {msg.channel + 1}, expected {LAUNCHPAD_CHANNEL + 1}"
            )
        if msg.type == "control_change":
            if launchpad.is_top_button(msg.control):
                return _ignored(f"top button CC {msg.control}")
            return _ignored(f"CC {msg.control} is not a Launchpad button")
        if msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            return _ignored(f"note off {msg.note}")
        if msg.type != "note_on":
            return _ignored(f"{msg.type} is not a pad press")
        if launchpad.is_right_button(msg.note):
            return _ignored(f"right button note {msg.note}")
        pad = launchpad.note_to_pad(msg.note)
        if pad is None:
            return _ignored(f"note {msg.note} is not a Launchpad pad")
        row, col = pad
        if col in FADER_COLS:
            return self._fader(row, col)
        if pad in FX_PADS:
            return self._toggle_fx(row, col)
        return _ignored(f"pad ({row},{col}) is not used")

    def _fader(self, row: int, col: int) -> Output:
        level = _level_for_row(row)
        self.levels[col] = level
        value = cc_for_level(level)
        control = self._level_cc[col]
        colors = self._colors()
        leds = [
            launchpad.led(r, col, colors.get((r, col), launchpad.OFF))
            for r in launchpad.GRID
        ]
        log = f"pad ({row},{col}) → {LEVEL_TARGETS[col]} {level} (CC {control}={value})"
        return Output([self._cc(control, value)], leds, [log])

    def _toggle_fx(self, row: int, col: int) -> Output:
        index = FX_PADS[(row, col)]
        self.fx[index] = not self.fx[index]
        value = self._fx_value(self.fx[index])
        control = self._fx_cc[index]
        led = launchpad.led(row, col, self._colors()[(row, col)])
        state = "ON" if self.fx[index] else "OFF"
        log = f"pad ({row},{col}) → {FX_TARGETS[index]} {state} (CC {control}={value})"
        return Output([self._cc(control, value)], [led], [log])

    def _colors(self) -> dict[tuple[int, int], int]:
        """LED color of every lit pad for the current state; pads not listed are off."""
        colors = {}
        for col, level in enumerate(self.levels):
            if level == 0:
                continue  # level 0 (bottom row) -> whole column dark
            for row in range(_row_for_level(level), 8):
                colors[(row, col)] = launchpad.FADER_ON
        for pad, index in FX_PADS.items():
            colors[pad] = launchpad.FX_ON if self.fx[index] else launchpad.FX_OFF
        return colors

    @staticmethod
    def _fx_value(on: bool) -> int:
        return FX_ON_VALUE if on else FX_OFF_VALUE

    @staticmethod
    def _cc(control: int, value: int) -> mido.Message:
        return mido.Message(
            "control_change", channel=RC600_CHANNEL, control=control, value=value
        )
