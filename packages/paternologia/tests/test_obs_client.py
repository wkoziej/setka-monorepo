# ABOUTME: Tests for the OBS websocket client wrapper (obsws-python).
# ABOUTME: Uses injected fake req/event clients; no running OBS required.

from types import SimpleNamespace

from paternologia.recording.obs_client import ObsClient


class FakeReq:
    """Stand-in for obsws ReqClient."""

    def __init__(self, recording=False, output_path="/rec/out.mkv"):
        self._recording = recording
        self._output_path = output_path
        self.calls = []

    def get_record_status(self):
        return SimpleNamespace(output_active=self._recording)

    def start_record(self):
        self.calls.append("start")
        self._recording = True

    def stop_record(self):
        self.calls.append("stop")
        self._recording = False
        return SimpleNamespace(output_path=self._output_path)

    def disconnect(self):
        self.calls.append("disconnect")


class FakeCallback:
    def __init__(self):
        self.registered = []

    def register(self, fn):
        self.registered.append(fn)


class FakeEvent:
    """Stand-in for obsws EventClient."""

    def __init__(self):
        self.callback = FakeCallback()

    def disconnect(self):
        pass


def _client(req=None, **kwargs):
    req = req or FakeReq()
    event = FakeEvent()
    client = ObsClient(
        req_factory=lambda h, p, w: req,
        event_factory=lambda h, p, w: event,
        **kwargs,
    )
    return client, req, event


def test_connect_registers_event_callback():
    client, _req, event = _client()
    assert client.connect() is True
    assert client.connected is True
    assert len(event.callback.registered) == 1


def test_connect_failure_leaves_disconnected():
    def boom(h, p, w):
        raise OSError("connection refused")

    client = ObsClient(req_factory=boom, event_factory=boom)
    assert client.connect() is False
    assert client.connected is False  # no crash


def test_start_record_when_idle_issues_start():
    client, req, _ = _client(req=FakeReq(recording=False))
    client.connect()
    assert client.start_record() is True
    assert req.calls == ["start"]


def test_start_record_is_idempotent_when_recording():
    client, req, _ = _client(req=FakeReq(recording=True))
    client.connect()
    assert client.start_record() is False  # no-op
    assert "start" not in req.calls


def test_stop_record_returns_output_path():
    client, req, _ = _client(req=FakeReq(recording=True, output_path="/rec/take.mkv"))
    client.connect()
    assert client.stop_record() == "/rec/take.mkv"
    assert "stop" in req.calls


def test_stop_record_noop_when_not_recording():
    client, req, _ = _client(req=FakeReq(recording=False))
    client.connect()
    assert client.stop_record() is None
    assert "stop" not in req.calls


def test_commands_safe_when_not_connected():
    client, req, _ = _client()
    # No connect() call.
    assert client.start_record() is False
    assert client.stop_record() is None
    assert client.is_recording() is False
    assert req.calls == []


def test_record_state_event_forwarded():
    received = []
    client, _req, event = _client(on_record_state=received.append)
    client.connect()
    handler = event.callback.registered[0]
    payload = SimpleNamespace(
        output_active=True, output_state="OBS_WEBSOCKET_OUTPUT_STARTED"
    )
    handler(payload)
    assert received == [payload]


def test_state_synced_on_connect_while_recording():
    """A process that connects while OBS is already recording sees it."""
    client, _req, _ = _client(req=FakeReq(recording=True))
    client.connect()
    assert client.is_recording() is True
