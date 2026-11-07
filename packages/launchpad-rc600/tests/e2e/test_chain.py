# ABOUTME: End-to-end test of the full chain: test-owned Launchpad port → lp-rc600 → rc600-sim.
# ABOUTME: Both apps run as real processes with real ALSA ports; assertions use their stdout.
import sys
import uuid
from pathlib import Path

import mido
import pytest

from launchpad_rc600.launchpad import pad_to_note

pytestmark = pytest.mark.integration

REPO_CONFIG = Path(__file__).parents[2] / "assign.toml"
TRACKS = [f"TRK{n} LEVEL" for n in range(1, 7)]
FX = [f"T FX {x}" for x in "ABCD"]


def press(pads, row, col):
    pads.send(
        mido.Message("note_on", channel=0, note=pad_to_note(row, col), velocity=127)
    )
    pads.send(
        mido.Message("note_off", channel=0, note=pad_to_note(row, col), velocity=0)
    )


@pytest.fixture
def chain(start_app):
    """Simulator first, then the translator; each one waits for its ready line."""
    name = f"e2e-{uuid.uuid4().hex[:8]}-pad"
    with (
        mido.open_output(name, virtual=True) as pads,
        mido.open_input(name, virtual=True),
    ):
        sim = start_app(
            sys.executable,
            "-m",
            "launchpad_rc600.sim_app",
            "--plain",
            "--config",
            str(REPO_CONFIG),
        )
        sim.wait_for("ready")
        translator = start_app(
            sys.executable,
            "-m",
            "launchpad_rc600.translator_app",
            "--launchpad",
            name,
            "--out",
            "RC-600 SIM",
            "--config",
            str(REPO_CONFIG),
        )
        translator.wait_for("ready")
        yield sim, translator, pads
        assert translator.stop() == 0
        assert sim.stop() == 0


def test_startup_brings_unknown_simulator_to_start_state(chain):
    sim, _, _ = chain
    for target in TRACKS:
        sim.wait_for(f"{target} ? → 71")
    for target in FX:
        sim.wait_for(f"{target} ? → off")


def test_fader_presses_set_exact_levels(chain):
    sim, _, pads = chain
    sim.wait_for("T FX D ? → off")
    press(pads, 7, 0)
    sim.wait_for("TRK1 LEVEL 71 → 0")
    press(pads, 4, 2)
    sim.wait_for("TRK3 LEVEL 71 → 43")
    press(pads, 0, 5)
    sim.wait_for("TRK6 LEVEL 71 → 100")


def test_fx_pad_twice_turns_fx_on_then_off(chain):
    sim, _, pads = chain
    sim.wait_for("T FX D ? → off")
    press(pads, 0, 7)
    sim.wait_for("T FX B off → on")
    press(pads, 0, 7)
    sim.wait_for("T FX B on → off")


def test_unused_pad_changes_nothing(chain):
    sim, translator, pads = chain
    sim.wait_for("T FX D ? → off")
    press(pads, 5, 6)
    translator.wait_for("ignored: pad (5,6)")
    press(pads, 7, 0)  # a marker press: the next simulator line must be this one
    line = sim.wait_for("BC")
    assert "TRK1 LEVEL 71 → 0" in line
