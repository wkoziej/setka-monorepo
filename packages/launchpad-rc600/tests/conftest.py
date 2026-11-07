# ABOUTME: Shared fixtures for tests that run the apps as real processes with real ALSA MIDI ports.
# ABOUTME: start_app starts a process and waits for its stdout lines with a timeout; find_port finds a port by a name part.
import os
import signal
import subprocess
import threading
import time

import pytest

# Every wait in the process tests has a limit, so a broken app fails the test and never hangs it.
TIMEOUT = 5.0


class AppProcess:
    """A real app process; reader threads collect its stdout and stderr lines."""

    def __init__(self, args: list[str], cwd=None):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        self.proc = subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.stdout: list[str] = []
        self.stderr: list[str] = []
        self._next = 0
        self._stdout_done = False
        self._cond = threading.Condition()
        self._readers = [
            threading.Thread(
                target=self._read, args=(self.proc.stdout, self.stdout), daemon=True
            ),
            threading.Thread(
                target=self._read, args=(self.proc.stderr, self.stderr), daemon=True
            ),
        ]
        for reader in self._readers:
            reader.start()

    def _read(self, stream, lines: list[str]) -> None:
        for line in stream:
            with self._cond:
                lines.append(line.rstrip("\n"))
                self._cond.notify_all()
        with self._cond:
            if lines is self.stdout:
                self._stdout_done = True
            self._cond.notify_all()

    def wait_for(self, text: str, timeout: float = TIMEOUT) -> str:
        """Return the next stdout line that contains text; lines before it are skipped."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                for i in range(self._next, len(self.stdout)):
                    if text in self.stdout[i]:
                        self._next = i + 1
                        return self.stdout[i]
                remaining = deadline - time.monotonic()
                if self._stdout_done or remaining <= 0:
                    raise AssertionError(
                        f"no stdout line with {text!r} (waited {timeout}s)\n"
                        f"stdout: {self.stdout}\nstderr: {self.stderr}"
                    )
                self._cond.wait(remaining)

    def wait(self, timeout: float = TIMEOUT) -> int:
        """Wait for the exit, collect all output, and return the exit code."""
        code = self.proc.wait(timeout)
        for reader in self._readers:
            reader.join(timeout)
        self.proc.stdout.close()
        self.proc.stderr.close()
        return code

    def stop(self, sig: int = signal.SIGTERM, timeout: float = TIMEOUT) -> int:
        """Send a signal and return the exit code."""
        if self.proc.poll() is None:
            self.proc.send_signal(sig)
        return self.wait(timeout)

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
        self.wait()


@pytest.fixture
def start_app():
    """Factory: start_app(*args, cwd=None) -> AppProcess. Processes still running at teardown are killed."""
    apps: list[AppProcess] = []

    def start(*args: str, cwd=None) -> AppProcess:
        app = AppProcess(list(args), cwd=cwd)
        apps.append(app)
        return app

    yield start
    for app in apps:
        if not app.proc.stdout.closed:
            app.kill()


def _find_port(names: list[str], part: str) -> str:
    matches = [name for name in names if part in name]
    assert len(matches) == 1, (
        f"expected one port with {part!r}, found {matches} in {names}"
    )
    return matches[0]


@pytest.fixture
def find_port():
    """find_port(names, part) -> the only port name that contains part; fails on zero or several matches."""
    return _find_port
