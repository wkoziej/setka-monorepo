# ABOUTME: Tests for the /health endpoint reporting MIDI/OBS subsystem state.
# ABOUTME: Uses a minimal app with faked app.state, no real ALSA/OBS required.

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from paternologia.routers.health import router


def _client(**state) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    for key, value in state.items():
        setattr(app.state, key, value)
    return TestClient(app)


def test_health_reports_all_fields():
    """/health returns the full state object when everything is wired."""
    client = _client(
        midi_listener=SimpleNamespace(input_subscribed=True),
        midi_bridge=SimpleNamespace(is_active=True),
        obs_connected=True,
        last_heartbeat_ts=123.0,
    )
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "pacer_input_open": True,
        "bridge_port_active": True,
        "obs_connected": True,
        "last_heartbeat_ts": 123.0,
    }


def test_health_pacer_input_open_reflects_subscription():
    """pacer_input_open follows the real ALSA subscription, not just an open handle.

    After PACER re-enumeration a stale handle keeps is_active True while the
    subscription is gone; /health must report the honest input_subscribed value.
    """
    client = _client(
        midi_listener=SimpleNamespace(input_subscribed=False),
        midi_bridge=SimpleNamespace(is_active=True),
    )
    body = client.get("/health").json()
    assert body["pacer_input_open"] is False


def test_health_obs_connected_false_when_absent():
    """obs_connected defaults to False and heartbeat to None when unset."""
    client = _client(
        midi_listener=SimpleNamespace(input_subscribed=True),
        midi_bridge=SimpleNamespace(is_active=True),
    )
    body = client.get("/health").json()
    assert body["obs_connected"] is False
    assert body["last_heartbeat_ts"] is None


def test_health_pacer_unplugged_keeps_bridge_active():
    """An unplugged PACER shows pacer_input_open=false but bridge stays active."""
    client = _client(
        midi_listener=SimpleNamespace(input_subscribed=False),
        midi_bridge=SimpleNamespace(is_active=True),
    )
    body = client.get("/health").json()
    assert body["pacer_input_open"] is False
    assert body["bridge_port_active"] is True


def test_health_handles_missing_subsystems():
    """Missing listener/bridge report inactive instead of erroring."""
    body = _client().get("/health").json()
    assert body["pacer_input_open"] is False
    assert body["bridge_port_active"] is False
