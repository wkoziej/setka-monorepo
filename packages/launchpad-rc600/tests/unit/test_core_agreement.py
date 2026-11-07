# ABOUTME: Pure integration tests: translator core output applied to the RC-600 model.
# ABOUTME: Regression guard that the model state always equals the translator state.
from pathlib import Path

import mido
import pytest

from launchpad_rc600.assign import load_config
from launchpad_rc600.launchpad import pad_to_note
from launchpad_rc600.rc600 import Rc600Model
from launchpad_rc600.translator import Translator

CONFIG = load_config(Path(__file__).parents[2] / "assign.toml", check=True)


def apply(model, messages):
    for msg in messages:
        model.handle(msg)


def assert_same_state(translator, model):
    assert model.levels == translator.levels
    assert model.fx == translator.fx


def test_startup_brings_model_to_translator_state():
    translator, model = Translator(CONFIG), Rc600Model(CONFIG)
    apply(model, translator.startup().rc600)
    assert_same_state(translator, model)


@pytest.mark.parametrize("row", range(8))
@pytest.mark.parametrize("col", range(8))
def test_every_pad_press_keeps_model_equal_to_translator(row, col):
    translator, model = Translator(CONFIG), Rc600Model(CONFIG)
    apply(model, translator.startup().rc600)
    press = mido.Message("note_on", channel=0, note=pad_to_note(row, col), velocity=127)
    apply(model, translator.handle(press).rc600)
    assert_same_state(translator, model)
