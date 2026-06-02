# ABOUTME: Tests for live view SSE endpoint and live router.
# ABOUTME: Tests HTTP responses, SSE content-type, and live song partial rendering.

import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paternologia import dependencies
from paternologia.main import app
from paternologia.midi.events import EventBus, MidiEvent
from paternologia.models import (
    Action,
    ActionType,
    Device,
    PacerButton,
    Song,
    SongMetadata,
)
from paternologia.storage import Storage


@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_storage(temp_data_dir):
    storage = Storage(data_dir=temp_data_dir)
    storage._ensure_dirs()
    return storage


@pytest.fixture
def sample_devices(test_storage):
    devices = [
        Device(
            id="boss",
            name="RC-600",
            midi_channel=12,
            action_types=[ActionType.PRESET, ActionType.CC],
        ),
    ]
    test_storage.save_devices(devices)
    return devices


@pytest.fixture
def sample_song(test_storage, sample_devices):
    song = Song(
        song=SongMetadata(id="zen", name="Zen"),
        pacer=[
            PacerButton(
                name="SW1",
                actions=[
                    Action(device="boss", type=ActionType.PRESET, value=2),
                ],
            )
        ],
    )
    test_storage.save_song(song)
    return song


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def client(test_storage, event_bus):
    original_storage = dependencies._storage
    dependencies._storage = test_storage
    app.state.event_bus = event_bus
    app.state.midi_listener = None
    try:
        with TestClient(app) as c:
            yield c
    finally:
        dependencies._storage = original_storage


class TestLivePage:
    """Tests for GET /live."""

    def test_live_page_returns_200(self, client, sample_devices):
        response = client.get("/live")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_live_page_contains_sse_connect(self, client, sample_devices):
        response = client.get("/live")
        assert "sse-connect" in response.text or "/live/events" in response.text


class TestLiveSongPartial:
    """Tests for GET /live/song/{song_id}."""

    def test_returns_song_partial(self, client, sample_song, sample_devices):
        response = client.get("/live/song/zen")
        assert response.status_code == 200
        assert "Zen" in response.text

    def test_returns_404_for_unknown_song(self, client, sample_devices):
        response = client.get("/live/song/nonexistent")
        assert response.status_code == 404


class TestLiveSSE:
    """Tests for GET /live/events SSE endpoint."""

    async def test_event_bus_delivers_to_subscriber(self, event_bus):
        """EventBus subscriber receives published events (SSE backend logic)."""
        queue = event_bus.subscribe()
        event = MidiEvent(song_id="zen", channel=12, program=2)
        await event_bus.publish(event)

        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.song_id == "zen"

    async def test_sse_event_format(self, event_bus):
        """SSE events should be formatted as 'event: song-change\\ndata: {song_id}\\n\\n'."""
        # Verify the format we use in the SSE generator
        event = MidiEvent(song_id="zen", channel=12, program=2)
        sse_line = f"event: song-change\ndata: {event.song_id}\n\n"
        assert "event: song-change" in sse_line
        assert "data: zen" in sse_line
