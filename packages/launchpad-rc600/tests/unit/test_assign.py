# ABOUTME: Unit tests for loading and validating the RC-600 ASSIGN config (assign.toml).
# ABOUTME: Each rule from R5/R12 has a broken config that must produce a named violation.
from pathlib import Path

import pytest

from launchpad_rc600.assign import (
    CONTROL_CHANNEL,
    FX_TARGETS,
    LEVEL_TARGETS,
    ConfigError,
    is_assign_source_cc,
    load_config,
    parse_config,
    validate,
)

REPO_CONFIG = Path(__file__).parents[2] / "assign.toml"

PACER = [{"slot": n, "cc": n, "owner": "Pacer"} for n in range(1, 5)]


def level_slot(slot, cc, target="TRK1 LEVEL", **extra):
    data = {
        "slot": slot,
        "source_cc": cc,
        "source_mode": "MOMENT",
        "act_lo": 0,
        "act_hi": 127,
        "target": target,
        "target_min": 0,
        "target_max": 100,
    }
    data.update(extra)
    return data


def violations_for(*slots):
    return validate(parse_config({"reserved": PACER, "slot": list(slots)}))


def test_shipped_config_is_valid_with_ten_slots():
    config = load_config(REPO_CONFIG)
    assert validate(config) == []
    assert len(config.slots) == 10
    assert [s.source_cc for s in config.slots] == list(range(64, 74))
    assert [s.target for s in config.slots] == list(LEVEL_TARGETS) + list(FX_TARGETS)


def test_shipped_fx_slots_use_moment_and_off_on():
    config = load_config(REPO_CONFIG)
    fx = config.slot_for_target("T FX A")
    assert fx.source_mode == "MOMENT"
    assert (fx.act_lo, fx.act_hi) == (64, 127)  # verified on the RC-600
    assert (fx.target_min, fx.target_max) == (0, 1)


def test_control_channel_is_13():
    assert CONTROL_CHANNEL == 13


def test_lookup_by_cc_and_target():
    config = load_config(REPO_CONFIG)
    assert config.slot_for_cc(66).target == "TRK3 LEVEL"
    assert config.slot_for_cc(20) is None
    assert config.slot_for_target("TRK6 LEVEL").source_cc == 69
    assert config.reserved_for_cc(2).owner == "Pacer"
    assert config.reserved_for_cc(64) is None


def test_cc_outside_assign_range():
    v = violations_for(level_slot(5, 40))
    assert any("slot 5" in m and "CC 40" in m and "1–31/64–95" in m for m in v)


def test_cc_used_by_pacer():
    v = violations_for(level_slot(5, 2))
    assert any("slot 5" in m and "CC 2" in m and "Pacer" in m for m in v)


def test_slot_reserved_for_pacer():
    v = violations_for(level_slot(3, 64))
    assert any("slot 3" in m and "reserved" in m and "Pacer" in m for m in v)


def test_slot_outside_1_16():
    v = violations_for(level_slot(17, 64))
    assert any("slot 17" in m and "1–16" in m for m in v)


def test_duplicate_slot():
    v = violations_for(level_slot(5, 64), level_slot(5, 65, "TRK2 LEVEL"))
    assert any("slot 5" in m and "duplicate" in m for m in v)


def test_duplicate_cc_names_both_slots():
    v = violations_for(level_slot(5, 64), level_slot(6, 64, "TRK2 LEVEL"))
    assert any("CC 64" in m and "slot 5" in m and "slot 6" in m for m in v)


@pytest.mark.parametrize(
    "cc,ok", [(31, True), (64, True), (32, False), (96, False), (0, False), (95, True)]
)
def test_cc_range_edges(cc, ok):
    assert is_assign_source_cc(cc) is ok
    v = violations_for(level_slot(5, cc))
    assert (not any("1–31/64–95" in m for m in v)) is ok


def test_unknown_target():
    v = violations_for(level_slot(5, 64, "TRK9 LEVEL"))
    assert any("slot 5" in m and "unknown target" in m for m in v)


def test_min_greater_than_max():
    v = violations_for(level_slot(5, 64, target_min=100, target_max=0))
    assert any("slot 5" in m and "min" in m and "max" in m for m in v)


def test_act_lo_greater_than_hi():
    v = violations_for(level_slot(5, 64, act_lo=100, act_hi=10))
    assert any("slot 5" in m and "ACT LO" in m for m in v)


def test_act_outside_0_127():
    v = violations_for(level_slot(5, 64, act_hi=200))
    assert any("slot 5" in m and "0–127" in m for m in v)


def test_unknown_source_mode():
    v = violations_for(level_slot(5, 64, source_mode="LATCH"))
    assert any("slot 5" in m and "source mode" in m for m in v)


def test_several_errors_are_all_reported():
    v = violations_for(level_slot(3, 40), level_slot(17, 2, "TRK2 LEVEL"))
    assert len(v) >= 4


def test_load_valid_raises_with_all_violations(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text(REPO_CONFIG.read_text().replace("slot = 5\n", "slot = 3\n", 1))
    with pytest.raises(ConfigError) as err:
        load_config(bad, check=True)
    assert any("slot 3" in m for m in err.value.violations)
