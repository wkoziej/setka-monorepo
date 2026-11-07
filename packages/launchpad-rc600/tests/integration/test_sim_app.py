# ABOUTME: Integration tests for the virtual RC-600 app (rc600-sim) run as a real process.
# ABOUTME: Messages go to its ALSA virtual port through real mido/rtmidi ports; assertions use its output.
import os
import pty
import re
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

import mido
import pytest

pytestmark = pytest.mark.integration

REPO = Path(__file__).parents[2]
REPO_CONFIG = REPO / "assign.toml"
PORT = "RC-600 SIM"
SIM = [sys.executable, "-m", "launchpad_rc600.sim_app"]

# mido channels are 0-based: RC-600 channel 13 is channel=12.
CH13 = 12


def cc(control, value, channel=CH13):
    return mido.Message("control_change", channel=channel, control=control, value=value)


def sim_ports() -> list[str]:
    return [name for name in mido.get_output_names() if PORT in name]


@pytest.fixture
def sim(start_app):
    assert sim_ports() == [], (
        "another RC-600 SIM port is open; stop it before the tests"
    )
    app = start_app(*SIM, "--plain", "--config", str(REPO_CONFIG))
    app.wait_for("ready")
    return app


@pytest.fixture
def to_sim(sim, find_port):
    with mido.open_output(find_port(mido.get_output_names(), PORT)) as out:
        yield out


def test_cc66_127_on_channel_13_sets_trk3_level_100(sim, to_sim):
    to_sim.send(cc(66, 127))
    line = sim.wait_for("TRK3 LEVEL")
    assert "TRK3 LEVEL ? → 100" in line
    # Each line has a time stamp and the raw bytes.
    assert re.match(r"\d\d:\d\d:\d\d\.\d{3} ", line)
    assert "BC 42 7F" in line


def test_cc_on_channel_1_is_ignored_with_channel_reason(sim, to_sim):
    to_sim.send(cc(66, 127, channel=0))
    line = sim.wait_for("ignored")
    assert "channel 1, expected 13" in line


def test_fx_change_line(sim, to_sim):
    to_sim.send(cc(70, 127))
    assert "T FX A ? → on" in sim.wait_for("T FX A")
    to_sim.send(cc(70, 0))
    assert "T FX A on → off" in sim.wait_for("T FX A")


def test_program_change_line(sim, to_sim):
    to_sim.send(mido.Message("program_change", channel=CH13, program=3))
    assert "PC 3: memory change, state not modeled" in sim.wait_for("PC 3")


def test_ready_line_shows_port_and_mapping(sim):
    ready = sim.stdout[0]
    assert "ready" in ready
    assert PORT in ready
    assert "ch13 · CC64–69 → TRK1–6 LEVEL · CC70–73 → T FX A–D" in ready


def test_port_is_visible_in_aconnect_while_running(start_app):
    # The default --config is assign.toml in the working directory.
    app = start_app(*SIM, "--plain", cwd=REPO)
    app.wait_for("ready")
    listing = subprocess.run(
        ["aconnect", "-l"], capture_output=True, text=True, timeout=5, check=True
    ).stdout
    assert f"'{PORT}'" in listing
    assert app.stop() == 0


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT, signal.SIGHUP])
def test_signal_stops_cleanly_and_closes_port(sim, sig):
    assert len(sim_ports()) == 1
    assert sim.stop(sig) == 0
    assert sim.stderr == []
    assert sim_ports() == []


def test_config_with_reserved_slot_stops_before_port_opens(start_app, tmp_path):
    text = REPO_CONFIG.read_text()
    broken = tmp_path / "assign.toml"
    broken.write_text(
        text.replace("slot = 5\nsource_cc = 64", "slot = 3\nsource_cc = 64")
    )
    app = start_app(*SIM, "--plain", "--config", str(broken))
    assert app.wait() != 0
    assert any("slot 3: slot reserved for Pacer" in line for line in app.stderr)
    assert not any("ready" in line for line in app.stdout)
    assert sim_ports() == []


def test_config_errors_are_all_printed(start_app, tmp_path):
    text = REPO_CONFIG.read_text()
    broken = tmp_path / "assign.toml"
    broken.write_text(
        text.replace("slot = 5\nsource_cc = 64", "slot = 3\nsource_cc = 40")
    )
    app = start_app(*SIM, "--plain", "--config", str(broken))
    assert app.wait() != 0
    errors = "\n".join(app.stderr)
    assert "slot 3: slot reserved for Pacer" in errors
    assert "slot 3: CC 40 outside 1–31/64–95" in errors


def test_missing_config_file_stops_with_message(start_app, tmp_path):
    app = start_app(*SIM, "--plain", "--config", str(tmp_path / "nothing.toml"))
    assert app.wait() != 0
    assert any("nothing.toml" in line for line in app.stderr)


ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def read_pty_until(fd: int, texts: list[str], timeout: float = 5.0) -> str:
    """Read terminal output until every text is in it (ANSI codes removed)."""
    raw = b""
    deadline = time.monotonic() + timeout
    while True:
        screen = ANSI.sub("", raw.decode("utf-8", errors="replace"))
        if all(text in screen for text in texts):
            return screen
        remaining = deadline - time.monotonic()
        assert remaining > 0, f"missing {texts} in terminal output:\n{screen}"
        ready, _, _ = select.select([fd], [], [], remaining)
        if ready:
            try:
                raw += os.read(fd, 65536)
            except OSError:
                # EIO: the process closed the terminal before the texts appeared.
                raise AssertionError(
                    f"terminal closed, missing {texts} in output:\n{screen}"
                ) from None


def drain_pty(fd: int, proc: subprocess.Popen, timeout: float = 5.0) -> None:
    """Read the terminal until the process ends, so its last screen write never blocks."""
    deadline = time.monotonic() + timeout
    while proc.poll() is None and time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.05)
        if ready:
            try:
                os.read(fd, 65536)
            except OSError:
                return


def test_tui_renders_in_a_terminal(find_port):
    assert sim_ports() == []
    master, slave = pty.openpty()
    env = dict(
        os.environ,
        TERM="xterm-256color",
        COLUMNS="100",
        LINES="40",
        PYTHONIOENCODING="utf-8",
    )
    proc = subprocess.Popen(
        [*SIM, "--config", str(REPO_CONFIG)], stdout=slave, stderr=slave, env=env
    )
    os.close(slave)
    try:
        read_pty_until(
            master, ["ready", "ch13 · CC64–69 → TRK1–6 LEVEL · CC70–73 → T FX A–D"]
        )
        with mido.open_output(find_port(mido.get_output_names(), PORT)) as out:
            out.send(cc(66, 127))
        screen = read_pty_until(master, ["TRK3 LEVEL ? → 100"])
        assert "current bank" in screen
        assert "on = value ≥ 64" in screen
        proc.send_signal(signal.SIGTERM)
        drain_pty(master, proc)
        assert proc.wait(5) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        os.close(master)
    assert sim_ports() == []
