# ABOUTME: Unit tests for the translator core: pad presses -> RC-600 CC, LED messages and log lines.
# ABOUTME: Uses the shipped assign.toml and real mido messages; no ports.
from dataclasses import replace
from pathlib import Path

import mido
import pytest

from launchpad_rc600.assign import CONTROL_CHANNEL, AssignConfig, load_config
from launchpad_rc600.launchpad import (
    FADER_ON,
    FX_OFF,
    FX_ON,
    OFF,
    note_to_pad,
    pad_to_note,
)
from launchpad_rc600.translator import LEVELS, Translator, cc_for_level

REPO_CONFIG = Path(__file__).parents[2] / "assign.toml"
RC600_CHANNEL = CONTROL_CHANNEL - 1


@pytest.fixture
def config():
    return load_config(REPO_CONFIG, check=True)


@pytest.fixture
def translator(config):
    return Translator(config)


def press(row, col):
    return mido.Message("note_on", channel=0, note=pad_to_note(row, col), velocity=127)


def cc(control, value):
    return mido.Message(
        "control_change", channel=RC600_CHANNEL, control=control, value=value
    )


def leds_by_pad(leds):
    return {note_to_pad(m.note): m.velocity for m in leds}


def column(leds, col):
    by_pad = leds_by_pad(leds)
    return [by_pad[(row, col)] for row in range(8)]


def round_half_up_level(value, slot):
    """Linear map ACT LO/HI -> TARGET MIN/MAX with round half up, in integers."""
    span_in = slot.act_hi - slot.act_lo
    span_out = slot.target_max - slot.target_min
    return slot.target_min + (2 * (value - slot.act_lo) * span_out + span_in) // (
        2 * span_in
    )


def test_levels():
    assert LEVELS == (0, 14, 29, 43, 57, 71, 86, 100)


@pytest.mark.parametrize(
    "level,value",
    [(0, 0), (14, 18), (29, 37), (43, 55), (57, 73), (71, 90), (86, 109), (100, 127)],
)
def test_cc_for_level(level, value):
    assert cc_for_level(level) == value


def test_cc_for_unknown_level():
    with pytest.raises(ValueError):
        cc_for_level(50)


@pytest.mark.parametrize("level", LEVELS)
def test_cc_for_level_maps_back_to_level_with_config_rule(config, level):
    slot = config.slot_for_target("TRK1 LEVEL")
    assert round_half_up_level(cc_for_level(level), slot) == level


def test_start_state(translator):
    assert translator.levels == [71] * 6
    assert translator.fx == [False] * 4


def test_startup_sends_start_state_and_full_led_frame(translator):
    out = translator.startup()
    assert out.rc600 == [cc(64 + n, 90) for n in range(6)] + [
        cc(70 + n, 0) for n in range(4)
    ]
    assert all(m.channel == 12 for m in out.rc600)
    assert len(out.leds) == 64
    by_pad = leds_by_pad(out.leds)
    for col in range(6):
        assert (
            column(out.leds, col) == [OFF] * 2 + [FADER_ON] * 6
        )  # start level 71 = row 2
    for pad in [(0, 6), (0, 7), (1, 6), (1, 7)]:
        assert by_pad[pad] == FX_OFF
    unused = [(r, c) for r in range(2, 8) for c in (6, 7)]
    assert all(by_pad[pad] == OFF for pad in unused)
    assert len(out.log) >= 1


def test_press_bottom_row_sets_level_0_and_column_dark(translator):
    out = translator.handle(press(7, 0))
    assert out.rc600 == [cc(64, cc_for_level(0))]
    assert column(out.leds, 0) == [OFF] * 8
    assert len(out.leds) == 8
    assert translator.levels[0] == 0


def test_press_top_row_sets_level_100_and_full_bar(translator):
    translator.handle(press(7, 5))
    out = translator.handle(press(0, 5))
    assert out.rc600 == [cc(69, cc_for_level(100))]
    assert column(out.leds, 5) == [FADER_ON] * 8
    assert translator.levels[5] == 100


def test_press_middle_row_lights_rows_down_to_bottom(translator):
    out = translator.handle(press(4, 2))
    assert out.rc600 == [cc(66, 55)]
    assert column(out.leds, 2) == [OFF] * 4 + [FADER_ON] * 4
    assert translator.levels[2] == 43
    assert out.log == ["pad (4,2) → TRK3 LEVEL 43 (CC 66=55)"]


@pytest.mark.parametrize("row", range(8))
def test_every_fader_row(translator, row):
    out = translator.handle(press(row, 3))
    level = LEVELS[7 - row]
    assert out.rc600 == [cc(67, cc_for_level(level))]
    lit = 0 if level == 0 else 8 - row
    assert column(out.leds, 3) == [OFF] * (8 - lit) + [FADER_ON] * lit


def test_fx_a_twice_flips_on_then_off(translator):
    first = translator.handle(press(0, 6))
    assert first.rc600 == [cc(70, 127)]
    assert leds_by_pad(first.leds) == {(0, 6): FX_ON}
    assert translator.fx == [True, False, False, False]
    assert first.log == ["pad (0,6) → T FX A ON (CC 70=127)"]
    second = translator.handle(press(0, 6))
    assert second.rc600 == [cc(70, 0)]
    assert leds_by_pad(second.leds) == {(0, 6): FX_OFF}
    assert translator.fx == [False] * 4
    assert second.log == ["pad (0,6) → T FX A OFF (CC 70=0)"]


@pytest.mark.parametrize(
    "pad,index", [((0, 6), 0), ((0, 7), 1), ((1, 6), 2), ((1, 7), 3)]
)
def test_fx_pad_map(translator, pad, index):
    out = translator.handle(press(*pad))
    assert out.rc600 == [cc(70 + index, 127)]
    expected = [False] * 4
    expected[index] = True
    assert translator.fx == expected


def test_fx_state_shows_in_later_startup_frame(translator):
    translator.handle(press(1, 7))
    translator.handle(press(4, 0))
    by_pad = leds_by_pad(translator.startup().leds)
    assert by_pad[(1, 7)] == FX_ON
    assert column(translator.startup().leds, 0) == [OFF] * 4 + [FADER_ON] * 4


def assert_ignored(out, reason):
    assert out.rc600 == []
    assert out.leds == []
    assert len(out.log) == 1
    assert "ignored" in out.log[0]
    assert reason in out.log[0]


@pytest.mark.parametrize("pad", [(2, 6), (6, 7), (7, 6)])
def test_unused_pad_is_ignored(translator, pad):
    out = translator.handle(press(*pad))
    assert_ignored(out, f"pad ({pad[0]},{pad[1]})")


def test_note_off_is_ignored(translator):
    out = translator.handle(
        mido.Message("note_off", channel=0, note=pad_to_note(4, 2), velocity=0)
    )
    assert_ignored(out, "note off")
    assert translator.levels == [71] * 6


def test_note_on_velocity_0_is_note_off(translator):
    out = translator.handle(
        mido.Message("note_on", channel=0, note=pad_to_note(4, 2), velocity=0)
    )
    assert_ignored(out, "note off")
    assert translator.levels == [71] * 6


@pytest.mark.parametrize("note", [8, 120])
def test_right_round_button_is_ignored(translator, note):
    out = translator.handle(mido.Message("note_on", channel=0, note=note, velocity=127))
    assert_ignored(out, "right button")


def test_top_button_is_ignored(translator):
    out = translator.handle(
        mido.Message("control_change", channel=0, control=104, value=127)
    )
    assert_ignored(out, "top button CC 104")


def test_other_cc_is_ignored(translator):
    out = translator.handle(
        mido.Message("control_change", channel=0, control=7, value=127)
    )
    assert_ignored(out, "CC 7")


def test_note_outside_layout_is_ignored(translator):
    out = translator.handle(mido.Message("note_on", channel=0, note=9, velocity=127))
    assert_ignored(out, "note 9")


def test_wrong_channel_is_ignored(translator):
    out = translator.handle(
        mido.Message("note_on", channel=1, note=pad_to_note(4, 2), velocity=127)
    )
    assert_ignored(out, "channel 2, expected 1")
    assert translator.levels == [71] * 6


def test_message_without_channel_is_ignored(translator):
    out = translator.handle(mido.Message("clock"))
    assert_ignored(out, "clock")


def test_cc_numbers_come_from_config(config):
    moved = AssignConfig(
        config.reserved,
        tuple(replace(s, source_cc=s.source_cc + 10) for s in config.slots),
    )
    t = Translator(moved)
    assert [m.control for m in t.startup().rc600] == list(range(74, 84))
    assert t.handle(press(4, 2)).rc600 == [cc(76, 55)]
    assert t.handle(press(1, 7)).rc600 == [cc(83, 127)]


def test_every_grid_pad_uses_only_config_cc_on_channel_13(config, translator):
    config_ccs = {s.source_cc for s in config.slots}
    for row in range(8):
        for col in range(8):
            for m in translator.handle(press(row, col)).rc600:
                assert m.type == "control_change"
                assert m.channel == 12
                assert m.control in config_ccs
