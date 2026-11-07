# ABOUTME: Integration tests for the lp-rc600 translator app: a real subprocess with real ALSA virtual ports.
# ABOUTME: Test-owned ports act as the Launchpad (pads in, LEDs out) and as the target that receives CC on ch13.
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import mido
import pytest

from launchpad_rc600.assign import CONTROL_CHANNEL
from launchpad_rc600.launchpad import pad_to_note, reset
from launchpad_rc600.translator import cc_for_level
from launchpad_rc600.translator_app import discard_pending

pytestmark = pytest.mark.integration

REPO_CONFIG = Path(__file__).parents[2] / "assign.toml"
RC600_CHANNEL = CONTROL_CHANNEL - 1
TIMEOUT = 5.0


class App:
    """The translator app as a real process; stdout lines are collected by a reader thread."""

    def __init__(self, *args: str):
        cmd = [sys.executable, "-m", "launchpad_rc600.translator_app", *args]
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=REPO_CONFIG.parent,
        )
        self.lines: list[str] = []
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self):
        for line in self.proc.stdout:
            self._queue.put(line.rstrip("\n"))
        self._queue.put(None)

    def wait_for_line(self, part: str) -> str:
        deadline = time.monotonic() + TIMEOUT
        while (left := deadline - time.monotonic()) > 0:
            try:
                line = self._queue.get(timeout=left)
            except queue.Empty:
                break
            if line is None:
                break
            self.lines.append(line)
            if part in line:
                return line
        raise AssertionError(
            f"no line with {part!r}; stdout so far: {self.lines}; stderr: {self._stderr()}"
        )

    def _stderr(self) -> str:
        return (
            self.proc.stderr.read()
            if self.proc.poll() is not None
            else "(still running)"
        )

    def stop(self, sig: int) -> int:
        self.proc.send_signal(sig)
        code = self.proc.wait(timeout=TIMEOUT)
        self._reader.join(timeout=TIMEOUT)
        while (line := self._queue.get_nowait()) is not None:
            self.lines.append(line)
        return code

    def kill(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=TIMEOUT)
        self.proc.stdout.close()
        self.proc.stderr.close()


def run_to_exit(*args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "launchpad_rc600.translator_app", *args]
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        cwd=REPO_CONFIG.parent,
    )


def receive(port, count: int) -> list[mido.Message]:
    """Collect `count` messages from a test-owned input port, or fail after TIMEOUT."""
    messages: list[mido.Message] = []
    deadline = time.monotonic() + TIMEOUT
    while len(messages) < count and time.monotonic() < deadline:
        msg = port.poll()
        if msg is None:
            time.sleep(0.005)
        else:
            messages.append(msg)
    assert len(messages) == count, (
        f"got {len(messages)} of {count} messages: {messages}"
    )
    return messages


def cc(control: int, value: int) -> mido.Message:
    return mido.Message(
        "control_change", channel=RC600_CHANNEL, control=control, value=value
    )


@pytest.fixture
def tag():
    """Unique name part, so the test ports never match other ports in the system."""
    return f"lpt-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def launchpad(tag):
    """Test-owned Launchpad: `pads` sends to the app, `leds` receives from the app. Same name part."""
    name = f"{tag}-pad"
    with (
        mido.open_output(name, virtual=True) as pads,
        mido.open_input(name, virtual=True) as leds,
    ):
        yield name, pads, leds


@pytest.fixture
def target(tag):
    name = f"{tag}-target"
    with mido.open_input(name, virtual=True) as port:
        yield name, port


@pytest.fixture
def apps():
    started: list[App] = []

    def start(*args: str) -> App:
        app = App(*args)
        started.append(app)
        return app

    yield start
    for app in started:
        app.kill()


@pytest.fixture
def running(launchpad, target, apps):
    """A started app that printed its ready line."""
    lp_name, pads, leds = launchpad
    out_name, out = target
    app = apps("--launchpad", lp_name, "--out", out_name, "--config", str(REPO_CONFIG))
    app.wait_for_line("ready")
    return app, pads, leds, out


def test_missing_out_port_stops_with_available_ports(launchpad, target):
    lp_name, _, _ = launchpad
    out_name, _ = target
    result = run_to_exit("--launchpad", lp_name, "--out", "no-such-port-xyz")
    assert result.returncode != 0
    assert "no-such-port-xyz" in result.stderr
    assert out_name in result.stderr  # the list of available output ports


def test_missing_launchpad_port_stops_with_available_ports(launchpad, target):
    lp_name, _, _ = launchpad
    out_name, _ = target
    result = run_to_exit("--launchpad", "no-such-port-xyz", "--out", out_name)
    assert result.returncode != 0
    assert "no-such-port-xyz" in result.stderr
    assert lp_name in result.stderr  # the list of available input ports


def test_ambiguous_port_name_stops_with_matching_ports(launchpad, tag):
    lp_name, _, _ = launchpad
    with (
        mido.open_input(f"{tag}-target-a", virtual=True),
        mido.open_input(f"{tag}-target-b", virtual=True),
    ):
        result = run_to_exit("--launchpad", lp_name, "--out", f"{tag}-target")
    assert result.returncode != 0
    assert f"{tag}-target-a" in result.stderr
    assert f"{tag}-target-b" in result.stderr


def test_bad_config_stops_with_violations(tmp_path, launchpad, target):
    bad = tmp_path / "assign.toml"
    bad.write_text(REPO_CONFIG.read_text().replace("slot = 5\n", "slot = 3\n", 1))
    result = run_to_exit(
        "--launchpad", launchpad[0], "--out", target[0], "--config", str(bad)
    )
    assert result.returncode != 0
    assert "slot 3: slot reserved for Pacer" in result.stderr


def test_startup_sends_start_state_and_led_frame(running):
    _, _, leds, out = running
    startup = receive(out, 10)
    assert startup == [cc(64 + n, cc_for_level(57)) for n in range(6)] + [
        cc(70 + n, 0) for n in range(4)
    ]
    frame = receive(leds, 64)
    assert sorted(m.note for m in frame) == sorted(
        pad_to_note(r, c) for r in range(8) for c in range(8)
    )
    assert all(m.type == "note_on" and m.channel == 0 for m in frame)


def test_pad_press_is_translated_and_logged(running):
    app, pads, leds, out = running
    receive(out, 10)
    receive(leds, 64)
    pads.send(mido.Message("note_on", channel=0, note=112, velocity=127))
    assert receive(out, 1) == [cc(64, cc_for_level(0))]
    app.wait_for_line(" in   note_on channel=0 note=112 velocity=127")
    app.wait_for_line(" out  control_change channel=12 control=64 value=0")


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM, signal.SIGHUP])
def test_signal_resets_leds_and_exits_cleanly(running, sig):
    app, _, leds, out = running
    receive(out, 10)
    receive(leds, 64)
    assert app.stop(sig) == 0
    assert receive(leds, 1) == [reset()]


def test_log_tag_is_separated_from_text(running):
    app, _, _, _ = running
    line = app.lines[-1]
    assert re.fullmatch(r"\d\d:\d\d:\d\d\.\d{3} info ready: .*", line), line


def test_startup_logs_discarded_stale_input(running):
    app, _, _, _ = running
    assert any("discarded 0 stale Launchpad messages" in line for line in app.lines), (
        app.lines
    )


def test_discard_pending_drops_buffered_messages(tag):
    """Messages that wait in the input before startup are dropped, so they cannot change the start state."""
    name = f"{tag}-stale"
    with mido.open_output(name, virtual=True) as pads, mido.open_input(name) as pad_in:
        time.sleep(0.05)
        for note in (17, 52, 48):
            pads.send(mido.Message("note_on", channel=0, note=note, velocity=127))
        assert discard_pending(pad_in) == 3
        assert list(pad_in.iter_pending()) == []
