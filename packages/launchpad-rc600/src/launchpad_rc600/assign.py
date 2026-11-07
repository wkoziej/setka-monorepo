# ABOUTME: Loads and validates the RC-600 ASSIGN config (assign.toml), the single source of the CC mapping.
# ABOUTME: Validation returns every rule violation (R5, R12), each naming the slot and the rule.
import tomllib
from dataclasses import dataclass
from pathlib import Path

# RX CH CTL on the RC-600 (wiki: "CTL channel — Pacer vs LCXL3"). 1-based MIDI channel.
CONTROL_CHANNEL = 13

LEVEL_TARGETS = tuple(f"TRK{n} LEVEL" for n in range(1, 7))
FX_TARGETS = tuple(f"T FX {x}" for x in "ABCD")
SOURCE_MODES = ("MOMENT", "TOGGLE")
FX_VALUES = {"OFF": 0, "ON": 1}
SLOT_RANGE = range(1, 17)
ACT_RANGE = range(128)


def is_assign_source_cc(cc: int) -> bool:
    """RC-600 manual, ASSIGN SOURCE: only MIDI CC#01–31 and CC#64–95."""
    return 1 <= cc <= 31 or 64 <= cc <= 95


class ConfigError(Exception):
    def __init__(self, violations: list[str]):
        super().__init__("\n".join(violations))
        self.violations = violations


@dataclass(frozen=True)
class Reserved:
    slot: int
    cc: int
    owner: str


@dataclass(frozen=True)
class Slot:
    slot: int
    source_cc: int
    source_mode: str
    act_lo: int
    act_hi: int
    target: str
    target_min: int
    target_max: int

    @property
    def is_fx(self) -> bool:
        return self.target in FX_TARGETS


@dataclass(frozen=True)
class AssignConfig:
    reserved: tuple[Reserved, ...]
    slots: tuple[Slot, ...]

    def slot_for_cc(self, cc: int) -> Slot | None:
        return next((s for s in self.slots if s.source_cc == cc), None)

    def slot_for_target(self, target: str) -> Slot:
        return next(s for s in self.slots if s.target == target)

    def reserved_for_cc(self, cc: int) -> Reserved | None:
        return next((r for r in self.reserved if r.cc == cc), None)


def _target_value(value) -> int:
    """FX targets use OFF/ON in the sheet; the model stores them as 0/1."""
    if isinstance(value, str):
        if value not in FX_VALUES:
            raise ConfigError(
                [f"unknown target value {value!r}, expected OFF/ON or a number"]
            )
        return FX_VALUES[value]
    return value


def parse_config(data: dict) -> AssignConfig:
    reserved = tuple(
        Reserved(r["slot"], r["cc"], r["owner"]) for r in data.get("reserved", [])
    )
    slots = tuple(
        Slot(
            slot=s["slot"],
            source_cc=s["source_cc"],
            source_mode=s["source_mode"],
            act_lo=s["act_lo"],
            act_hi=s["act_hi"],
            target=s["target"],
            target_min=_target_value(s["target_min"]),
            target_max=_target_value(s["target_max"]),
        )
        for s in data.get("slot", [])
    )
    return AssignConfig(reserved, slots)


def validate(config: AssignConfig) -> list[str]:
    violations: list[str] = []
    reserved_slots = {r.slot: r for r in config.reserved}
    seen_slots: set[int] = set()
    cc_owners: dict[int, list[int]] = {}

    for s in config.slots:
        name = f"slot {s.slot}"
        if s.slot not in SLOT_RANGE:
            violations.append(f"{name}: slot outside 1–16")
        if s.slot in reserved_slots:
            violations.append(
                f"{name}: slot reserved for {reserved_slots[s.slot].owner}"
            )
        if s.slot in seen_slots:
            violations.append(f"{name}: duplicate slot number")
        seen_slots.add(s.slot)
        if not is_assign_source_cc(s.source_cc):
            violations.append(f"{name}: CC {s.source_cc} outside 1–31/64–95")
        owner = config.reserved_for_cc(s.source_cc)
        if owner is not None:
            violations.append(f"{name}: CC {s.source_cc} used by {owner.owner}")
        cc_owners.setdefault(s.source_cc, []).append(s.slot)
        if s.source_mode not in SOURCE_MODES:
            violations.append(
                f"{name}: unknown source mode {s.source_mode!r}, expected MOMENT or TOGGLE"
            )
        if s.act_lo not in ACT_RANGE or s.act_hi not in ACT_RANGE:
            violations.append(f"{name}: ACT LO/HI must be in 0–127")
        elif s.act_lo > s.act_hi:
            violations.append(f"{name}: ACT LO {s.act_lo} > ACT HI {s.act_hi}")
        if s.target not in LEVEL_TARGETS + FX_TARGETS:
            violations.append(f"{name}: unknown target {s.target!r}")
        if s.target_min > s.target_max:
            violations.append(f"{name}: target min {s.target_min} > max {s.target_max}")

    for cc, slots in cc_owners.items():
        if len(slots) > 1:
            names = ", ".join(f"slot {n}" for n in slots)
            violations.append(f"CC {cc} used by more than one slot: {names}")
    return violations


def load_config(path: Path | str, check: bool = False) -> AssignConfig:
    with open(path, "rb") as f:
        config = parse_config(tomllib.load(f))
    if check:
        violations = validate(config)
        if violations:
            raise ConfigError(violations)
    return config
