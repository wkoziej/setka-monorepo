# ABOUTME: Unit tests for Launchpad Mini (1st gen) pad addressing and LED message builders.
# ABOUTME: Expected values are the ones that worked on the real device (aseqdump capture, LED tests).
import mido
import pytest

from launchpad_rc600.launchpad import (
    FADER_ON,
    FX_OFF,
    FX_ON,
    OFF,
    color,
    frame,
    is_right_button,
    is_top_button,
    led,
    note_to_pad,
    pad_to_note,
    reset,
)


@pytest.mark.parametrize(
    "note,pad", [(0, (0, 0)), (119, (7, 7)), (112, (7, 0)), (53, (3, 5)), (7, (0, 7))]
)
def test_note_to_pad(note, pad):
    assert note_to_pad(note) == pad


def test_pad_to_note_and_back():
    assert pad_to_note(3, 5) == 53
    assert note_to_pad(pad_to_note(3, 5)) == (3, 5)


def test_every_grid_pad_round_trips():
    for row in range(8):
        for col in range(8):
            assert note_to_pad(pad_to_note(row, col)) == (row, col)


@pytest.mark.parametrize("row,col", [(-1, 0), (8, 0), (0, -1), (0, 8)])
def test_pad_to_note_outside_grid(row, col):
    with pytest.raises(ValueError):
        pad_to_note(row, col)


@pytest.mark.parametrize("note", [8, 24, 120])
def test_right_round_button_is_not_a_grid_pad(note):
    assert is_right_button(note)
    assert note_to_pad(note) is None


@pytest.mark.parametrize("note", [0, 7, 112, 119])
def test_grid_pad_is_not_a_right_button(note):
    assert not is_right_button(note)


@pytest.mark.parametrize("note", [9, 15, 127])
def test_notes_outside_launchpad_layout(note):
    assert note_to_pad(note) is None
    assert not is_right_button(note)


@pytest.mark.parametrize(
    "cc,ok", [(104, True), (111, True), (103, False), (112, False), (0, False)]
)
def test_top_button(cc, ok):
    assert is_top_button(cc) is ok


@pytest.mark.parametrize(
    "red,green,velocity", [(3, 0, 0x0F), (0, 3, 0x3C), (3, 3, 0x3F), (0, 0, 12)]
)
def test_color(red, green, velocity):
    assert color(red, green) == velocity


@pytest.mark.parametrize("red,green", [(4, 0), (0, 4), (-1, 0), (0, -1)])
def test_color_component_outside_0_3(red, green):
    with pytest.raises(ValueError):
        color(red, green)


def test_named_colors():
    assert OFF == color(0, 0)
    assert FADER_ON == color(0, 3)
    assert FX_ON == color(3, 0)  # full red
    assert FX_OFF == color(0, 1)  # dim green


def test_led_message():
    assert led(7, 0, FADER_ON) == mido.Message(
        "note_on", channel=0, note=112, velocity=0x3C
    )


def test_frame_covers_all_64_pads_and_unlisted_are_off():
    msgs = frame({(0, 0): FX_ON, (7, 7): FADER_ON})
    assert len(msgs) == 64
    assert all(m.type == "note_on" and m.channel == 0 for m in msgs)
    by_pad = {note_to_pad(m.note): m.velocity for m in msgs}
    assert set(by_pad) == {(r, c) for r in range(8) for c in range(8)}
    assert by_pad[(0, 0)] == FX_ON
    assert by_pad[(7, 7)] == FADER_ON
    assert by_pad[(3, 3)] == OFF


def test_reset_is_cc_0_value_0_on_channel_1():
    assert reset() == mido.Message("control_change", channel=0, control=0, value=0)
