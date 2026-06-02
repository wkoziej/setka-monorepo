# ABOUTME: Serializes PACER record triggers onto a single async OBS worker.
# ABOUTME: Coalesces rapid duplicate notes so a footswitch bounce can't double-fire.

import asyncio
import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class RecordDispatcher:
    """Runs OBS record actions one at a time from a single consumer task.

    PACER record-trigger notes arrive on the rtmidi C thread and routinely double
    (footswitch bounce — the observed "kilka MIDI zdarzeń"). submit() marshals each
    action onto the event loop; a single consumer runs them serially off the loop
    via to_thread, so two near-simultaneous "start" notes can never race the OBS
    idempotency check. Consecutive identical actions are coalesced; opposite
    actions are always honored.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, orchestrator):
        self._loop = loop
        self._orch = orchestrator
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._last_action: str | None = None

    def start_consumer(self) -> None:
        """Start the single consumer task (idempotent)."""
        if self._task is None:
            self._task = self._loop.create_task(self._run())

    def submit(self, action: str) -> None:
        """Enqueue a record action ("start"/"stop") from any thread."""
        self._loop.call_soon_threadsafe(self._queue.put_nowait, action)

    async def _run(self) -> None:
        while True:
            action = await self._queue.get()
            try:
                if action == self._last_action:
                    logger.info("record action '%s' coalesced (duplicate)", action)
                    continue
                self._last_action = action
                target: Callable[[], object] = (
                    self._orch.start if action == "start" else self._orch.stop
                )
                try:
                    await asyncio.to_thread(target)
                except Exception as e:
                    # An OBS failure must not kill the consumer; allow a retry of
                    # the same action by clearing the coalesce guard.
                    logger.warning("record action '%s' failed: %s", action, e)
                    self._last_action = None
            finally:
                self._queue.task_done()

    async def aclose(self) -> None:
        """Cancel the consumer task and wait for it to finish."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
