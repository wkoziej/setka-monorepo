# ABOUTME: Async event bus for broadcasting MIDI events to SSE subscribers.
# ABOUTME: Thread-safe publish from rtmidi callback thread to asyncio event loop.

import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MidiEvent:
    """A detected MIDI event mapped to a song."""

    song_id: str
    channel: int
    program: int
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Async broadcast bus for MIDI events.

    Subscribers get an asyncio.Queue. Published events are
    delivered to all active queues. Thread-safe via
    loop.call_soon_threadsafe for rtmidi callback thread.
    """

    def __init__(self):
        self._subscribers: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the asyncio event loop for thread-safe publishing."""
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        """Create and return a new subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        logger.debug("New SSE subscriber (total: %d)", len(self._subscribers))
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        self._subscribers.discard(queue)
        logger.debug("SSE unsubscribe (total: %d)", len(self._subscribers))

    async def publish(self, event: MidiEvent) -> None:
        """Publish event to all subscribers (async context)."""
        for queue in self._subscribers:
            await queue.put(event)

    def publish_threadsafe(self, event: MidiEvent) -> None:
        """Publish event from a non-asyncio thread (rtmidi callback)."""
        if self._loop is None:
            logger.warning("EventBus: no event loop set, dropping event")
            return
        self._loop.call_soon_threadsafe(self._publish_sync, event)

    def _publish_sync(self, event: MidiEvent) -> None:
        """Synchronous publish called via call_soon_threadsafe."""
        for queue in self._subscribers:
            queue.put_nowait(event)
