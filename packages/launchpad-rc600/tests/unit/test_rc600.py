# ABOUTME: Unit tests for the pure RC-600 ASSIGN model (levels, Track FX, ignore reasons).
# ABOUTME: Input is real mido messages; the shipped assign.toml is the ASSIGN table.
from pathlib import Path

import mido
import pytest

from launchpad_rc600.assign import load_config, parse_config
from launchpad_rc600.rc600 import (
    FX_ON_THRESHOLD,
    Event,
    Rc600Model,
    level_for_value,
    mapping_line,
)

REPO_CONFIG = Path(__file__).parents[2] / "assign.toml"

# mido channels are 0-based: RC-600 channel 13 is channel=12.
CH13 = 12


def cc(control, value, channel=CH13):
    return mido.Message("control_change", channel=channel, control=control, value=value)


@pytest.fixture
def config():
    return load_config(REPO_CONFIG, check=True)


@pytest.fixture
def model(config):
    return Rc600Model(config)


def custom_slot(**extra):
    data = {
        "slot": 5,
        "source_cc": 64,
        "source_mode": "MOMENT",
        "act_lo": 0,
        "act_hi": 127,
        "target": "TRK1 LEVEL",
        "target_min": 0,
        "target_max": 100,
    }
    data.update(extra)
    return parse_config({"slot": [data]}).slots[0]


def test_start_state_is_unknown(model):
    assert model.levels == [None] * 6
    assert model.fx == [None] * 4


def test_cc65_127_sets_trk2_level_100(model):
    event = model.handle(cc(65, 127))
    assert event == Event("TRK2 LEVEL ? → 100", True)
    assert model.levels[1] == 100


def test_cc64_0_sets_trk1_level_0(model):
    event = model.handle(cc(64, 0))
    assert event == Event("TRK1 LEVEL ? → 0", True)
    assert model.levels[0] == 0


def test_level_change_shows_old_value(model):
    model.handle(cc(66, 127))
    event = model.handle(cc(66, 55))
    assert event == Event("TRK3 LEVEL 100 → 43", True)


def test_same_level_again_is_not_a_change(model):
    model.handle(cc(66, 127))
    event = model.handle(cc(66, 127))
    assert event == Event("TRK3 LEVEL 100 → 100", False)


def test_fx_c_on_then_off(model):
    assert model.handle(cc(72, 127)) == Event("T FX C ? → on", True)
    assert model.fx == [None, None, True, None]
    assert model.handle(cc(72, 0)) == Event("T FX C on → off", True)
    assert model.fx == [None, None, False, None]


def test_fx_same_state_again_is_not_a_change(model):
    model.handle(cc(70, 0))
    assert model.handle(cc(70, 0)) == Event("T FX A off → off", False)


def test_fx_threshold_is_64():
    assert FX_ON_THRESHOLD == 64


@pytest.mark.parametrize(
    "value,state", [(63, False), (64, True), (0, False), (127, True)]
)
def test_fx_threshold_edges(model, value, state):
    model.handle(cc(73, value))
    assert model.fx[3] is state


def test_wrong_channel_is_ignored(model):
    event = model.handle(cc(65, 127, channel=0))
    assert event == Event("ignored: channel 1, expected 13", False)
    assert model.levels == [None] * 6


def test_channel_is_checked_before_message_type(model):
    note = mido.Message("note_on", channel=0, note=60, velocity=127)
    assert model.handle(note).text == "ignored: channel 1, expected 13"


def test_note_on_channel_13_is_not_a_cc(model):
    note = mido.Message("note_on", channel=CH13, note=60, velocity=127)
    assert model.handle(note) == Event("ignored: not a CC", False)


def test_message_without_channel_is_not_a_cc(model):
    assert model.handle(mido.Message("clock")) == Event("ignored: not a CC", False)
    assert model.handle(mido.Message("sysex", data=[1, 2])).text == "ignored: not a CC"


@pytest.mark.parametrize("control", [0, 32, 40, 63, 96, 127])
def test_cc_outside_assign_range_is_ignored(model, control):
    event = model.handle(cc(control, 127))
    assert event == Event(f"ignored: CC {control} cannot be an ASSIGN source", False)


def test_pacer_cc_is_ignored_as_not_modeled(model):
    event = model.handle(cc(2, 127))
    assert event.text.startswith("ignored: Pacer slot (not modeled)")
    assert "slot 2" in event.text and "CC 2" in event.text
    assert event.changed is False


def test_cc_without_slot_is_ignored(model):
    assert model.handle(cc(20, 127)) == Event(
        "ignored: no ASSIGN slot for CC 20", False
    )
    assert model.handle(cc(74, 127)).text == "ignored: no ASSIGN slot for CC 74"


def test_program_change_on_channel_13_is_memory_change(model):
    model.handle(cc(64, 127))
    event = model.handle(mido.Message("program_change", channel=CH13, program=5))
    assert "memory change, state not modeled" in event.text
    assert event.changed is False
    assert model.levels == [100, None, None, None, None, None]
    assert model.fx == [None] * 4


def test_program_change_on_other_channel_is_wrong_channel(model):
    event = model.handle(mido.Message("program_change", channel=0, program=5))
    assert event.text == "ignored: channel 1, expected 13"


def test_ignored_messages_do_not_change_state(model):
    for msg in [cc(65, 127, channel=0), cc(40, 127), cc(2, 127), cc(20, 127)]:
        model.handle(msg)
    assert model.levels == [None] * 6
    assert model.fx == [None] * 4


@pytest.mark.parametrize(
    "value,level",
    [(0, 0), (18, 14), (37, 29), (55, 43), (73, 57), (90, 71), (109, 86), (127, 100)],
)
def test_level_for_value_matches_the_eight_rows(config, value, level):
    assert level_for_value(config.slot_for_target("TRK1 LEVEL"), value) == level


def test_level_for_value_rounds_half_up():
    slot = custom_slot(act_lo=0, act_hi=2, target_min=0, target_max=1)
    assert level_for_value(slot, 1) == 1


def test_level_for_value_uses_act_and_target_range():
    slot = custom_slot(act_lo=27, act_hi=127, target_min=50, target_max=200)
    assert level_for_value(slot, 27) == 50
    assert level_for_value(slot, 77) == 125
    assert level_for_value(slot, 127) == 200


def test_level_for_value_clamps_outside_act_range():
    slot = custom_slot(act_lo=20, act_hi=100, target_min=0, target_max=100)
    assert level_for_value(slot, 0) == 0
    assert level_for_value(slot, 127) == 100


def test_level_for_value_with_equal_act_lo_and_hi_is_a_step():
    slot = custom_slot(act_lo=64, act_hi=64, target_min=0, target_max=100)
    assert level_for_value(slot, 63) == 0
    assert level_for_value(slot, 64) == 100


def test_mapping_line_for_shipped_config(config):
    assert mapping_line(config) == "ch13 · CC64–69 → TRK1–6 LEVEL · CC70–73 → T FX A–D"


def test_mapping_line_splits_non_contiguous_runs():
    def slot(n, source_cc, target, lo=0, hi=100):
        return {
            "slot": n,
            "source_cc": source_cc,
            "source_mode": "MOMENT",
            "act_lo": 0,
            "act_hi": 127,
            "target": target,
            "target_min": lo,
            "target_max": hi,
        }

    config = parse_config(
        {
            "slot": [
                slot(6, 66, "TRK3 LEVEL"),
                slot(5, 64, "TRK1 LEVEL"),
                slot(7, 67, "TRK4 LEVEL"),
                slot(8, 68, "T FX B", "OFF", "ON"),
            ]
        }
    )
    assert (
        mapping_line(config)
        == "ch13 · CC64 → TRK1 LEVEL · CC66–67 → TRK3–4 LEVEL · CC68 → T FX B"
    )
