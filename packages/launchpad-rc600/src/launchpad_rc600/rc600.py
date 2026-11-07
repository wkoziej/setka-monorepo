# ABOUTME: Pure model of the RC-600 ASSIGN behavior for TRK1–6 LEVEL and T FX A–D (one FX bank).
# ABOUTME: Each MIDI message gives one Event: the state change or the reason why it is ignored.
from dataclasses import dataclass

import mido

from launchpad_rc600.assign import (
    CONTROL_CHANNEL,
    FX_TARGETS,
    LEVEL_TARGETS,
    AssignConfig,
    Slot,
    is_assign_source_cc,
)

# Assumption, not from the manual: the manual does not say how a CC value maps to FX on/off.
# Value >= 64 -> on. The translator sends only 0 and 127, so any threshold gives the same result.
FX_ON_THRESHOLD = 64


@dataclass(frozen=True)
class Event:
    text: str
    changed: bool


def level_for_value(slot: Slot, value: int) -> int:
    """Map a CC value to a PLAY LEVEL.

    RC-600 manual, ASSIGN: "SOURCE ACT. LO/HI ... Target parameters are controlled within the
    range set with ACT LOW and ACT HIGH"; TARGET MIN/MAX is the target range; "TRK1–6 LEVEL:
    Control the PLAY LEVEL ... in the range of 0–200". The manual does not give the curve or
    the rounding: the model uses a linear map with round half up (to verify on the device).
    Values outside ACT LO/HI clamp to TARGET MIN/MAX. If ACT LO = ACT HI, the map is a step:
    below ACT LO -> MIN, else MAX.
    """
    span = slot.act_hi - slot.act_lo
    if span == 0:
        return slot.target_max if value >= slot.act_hi else slot.target_min
    value = min(max(value, slot.act_lo), slot.act_hi)
    scaled = (value - slot.act_lo) * (slot.target_max - slot.target_min)
    return slot.target_min + (2 * scaled + span) // (2 * span)


def _show(value) -> str:
    if value is None:
        return "?"
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value)


class Rc600Model:
    def __init__(self, config: AssignConfig):
        self.config = config
        # Start state is unknown: the real device state is also unknown to the translator.
        self.levels: list[int | None] = [None] * len(LEVEL_TARGETS)
        self.fx: list[bool | None] = [None] * len(FX_TARGETS)

    def handle(self, msg: mido.Message) -> Event:
        # Messages without a channel (clock, sysex, ...) cannot be ASSIGN sources.
        if not hasattr(msg, "channel"):
            return _ignored("not a CC")
        # RX CH CTL = 13 (wiki: "CTL channel — Pacer vs LCXL3"); mido channels are 0-based.
        if msg.channel + 1 != CONTROL_CHANNEL:
            return _ignored(f"channel {msg.channel + 1}, expected {CONTROL_CHANNEL}")
        if msg.type == "program_change":
            # RC-600 manual, ASSIGN NOTE: settings are stored in memory; per-memory state is not modeled.
            return Event(f"PC {msg.program}: memory change, state not modeled", False)
        if msg.type != "control_change":
            return _ignored("not a CC")
        if not is_assign_source_cc(msg.control):
            return _ignored(f"CC {msg.control} cannot be an ASSIGN source")
        reserved = self.config.reserved_for_cc(msg.control)
        if reserved is not None:
            return _ignored(
                f"{reserved.owner} slot (not modeled): slot {reserved.slot}, CC {msg.control}"
            )
        slot = self.config.slot_for_cc(msg.control)
        if slot is None:
            return _ignored(f"no ASSIGN slot for CC {msg.control}")
        if slot.is_fx:
            # RC-600 manual, TARGET "T FX A–D": track FX on/off for the currently selected FX bank.
            return self._apply(
                self.fx,
                FX_TARGETS.index(slot.target),
                slot.target,
                msg.value >= FX_ON_THRESHOLD,
            )
        return self._apply(
            self.levels,
            LEVEL_TARGETS.index(slot.target),
            slot.target,
            level_for_value(slot, msg.value),
        )

    def _apply(self, states: list, index: int, target: str, new) -> Event:
        old = states[index]
        states[index] = new
        return Event(f"{target} {_show(old)} → {_show(new)}", old != new)


def _ignored(reason: str) -> Event:
    return Event(f"ignored: {reason}", False)


def _target_kind_and_index(target: str) -> tuple[str, int]:
    if target in LEVEL_TARGETS:
        return "level", LEVEL_TARGETS.index(target)
    return "fx", FX_TARGETS.index(target)


def _run_text(first: Slot, last: Slot) -> str:
    sources = (
        f"CC{first.source_cc}"
        if first is last
        else f"CC{first.source_cc}–{last.source_cc}"
    )
    if first is last:
        return f"{sources} → {first.target}"
    if first.is_fx:
        return f"{sources} → T FX {first.target[-1]}–{last.target[-1]}"
    return f"{sources} → TRK{first.target[3]}–{last.target[3]} LEVEL"


def mapping_line(config: AssignConfig) -> str:
    """Short mapping line: contiguous CC runs with contiguous targets of one kind are grouped."""
    runs: list[list[Slot]] = []
    for slot in sorted(config.slots, key=lambda s: s.source_cc):
        if runs:
            prev = runs[-1][-1]
            prev_kind, prev_index = _target_kind_and_index(prev.target)
            kind, index = _target_kind_and_index(slot.target)
            if (
                slot.source_cc == prev.source_cc + 1
                and kind == prev_kind
                and index == prev_index + 1
            ):
                runs[-1].append(slot)
                continue
        runs.append([slot])
    parts = [f"ch{CONTROL_CHANNEL}"] + [_run_text(run[0], run[-1]) for run in runs]
    return " · ".join(parts)
