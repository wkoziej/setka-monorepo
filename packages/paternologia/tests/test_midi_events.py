# ABOUTME: Tests for MIDI event bus (asyncio broadcast).
# ABOUTME: Tests publish/subscribe, multiple subscribers, and unsubscribe.

import asyncio

import pytest

from paternologia.midi.events import EventBus, MidiEvent


@pytest.fixture
def event_bus():
    return EventBus()


class TestMidiEvent:
    """Tests for MidiEvent dataclass."""

    def test_create_event(self):
        event = MidiEvent(song_id="zen", channel=12, program=2)
        assert event.song_id == "zen"
        assert event.channel == 12
        assert event.program == 2
        assert event.timestamp > 0


class TestEventBus:
    """Tests for async event bus."""

    async def test_subscribe_and_publish(self, event_bus):
        """Subscriber should receive published event."""
        queue = event_bus.subscribe()
        event = MidiEvent(song_id="zen", channel=12, program=2)

        await event_bus.publish(event)
        received = await asyncio.wait_for(queue.get(), timeout=1.0)

        assert received.song_id == "zen"

    async def test_multiple_subscribers(self, event_bus):
        """All subscribers should receive the same event."""
        q1 = event_bus.subscribe()
        q2 = event_bus.subscribe()

        event = MidiEvent(song_id="zen", channel=12, program=2)
        await event_bus.publish(event)

        r1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        r2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert r1.song_id == "zen"
        assert r2.song_id == "zen"

    async def test_unsubscribe(self, event_bus):
        """Unsubscribed queue should not receive new events."""
        queue = event_bus.subscribe()
        event_bus.unsubscribe(queue)

        event = MidiEvent(song_id="zen", channel=12, program=2)
        await event_bus.publish(event)

        assert queue.empty()

    async def test_unsubscribe_nonexistent_is_safe(self, event_bus):
        """Unsubscribing a queue that was never subscribed should not raise."""
        queue: asyncio.Queue = asyncio.Queue()
        event_bus.unsubscribe(queue)

    async def test_publish_threadsafe(self, event_bus):
        """publish_threadsafe should work from another thread."""
        queue = event_bus.subscribe()
        event = MidiEvent(song_id="zen", channel=12, program=2)

        loop = asyncio.get_running_loop()
        event_bus.set_loop(loop)
        event_bus.publish_threadsafe(event)

        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.song_id == "zen"
