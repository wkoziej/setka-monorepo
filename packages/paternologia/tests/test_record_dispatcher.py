# ABOUTME: Tests for RecordDispatcher serialization and coalescing.
# ABOUTME: Guards against the observed double-fire of the PACER record footswitch.

import asyncio

from paternologia.recording.dispatcher import RecordDispatcher


class FakeOrch:
    def __init__(self):
        self.calls = []

    def start(self):
        self.calls.append("start")

    def stop(self):
        self.calls.append("stop")


async def _drain(dispatcher: RecordDispatcher) -> None:
    # submit() schedules the enqueue via call_soon_threadsafe (it is normally
    # called from the rtmidi C thread), so pump the loop until the puts land
    # before waiting on the queue to be fully processed.
    for _ in range(5):
        await asyncio.sleep(0)
    await asyncio.wait_for(dispatcher._queue.join(), timeout=1.0)


async def test_duplicate_start_is_coalesced():
    """Two rapid 'start' notes (footswitch bounce) issue a single OBS start."""
    orch = FakeOrch()
    d = RecordDispatcher(asyncio.get_running_loop(), orch)
    d.start_consumer()
    d.submit("start")
    d.submit("start")
    await _drain(d)
    await d.aclose()
    assert orch.calls == ["start"]


async def test_start_then_stop_both_run_in_order():
    orch = FakeOrch()
    d = RecordDispatcher(asyncio.get_running_loop(), orch)
    d.start_consumer()
    d.submit("start")
    d.submit("stop")
    await _drain(d)
    await d.aclose()
    assert orch.calls == ["start", "stop"]


async def test_consumer_survives_an_action_failure():
    """A raising start (OBS dropped) must not kill the consumer; stop still runs."""

    class Boom:
        def __init__(self):
            self.calls = []

        def start(self):
            self.calls.append("start")
            raise RuntimeError("obs down")

        def stop(self):
            self.calls.append("stop")

    orch = Boom()
    d = RecordDispatcher(asyncio.get_running_loop(), orch)
    d.start_consumer()
    d.submit("start")
    d.submit("stop")
    await _drain(d)
    await d.aclose()
    assert orch.calls == ["start", "stop"]


async def test_start_retry_allowed_after_failure():
    """After a failed start, the coalesce guard is cleared so a retry runs."""

    class FlakyStart:
        def __init__(self):
            self.calls = []
            self._fail = True

        def start(self):
            self.calls.append("start")
            if self._fail:
                self._fail = False
                raise RuntimeError("transient")

        def stop(self):
            self.calls.append("stop")

    orch = FlakyStart()
    d = RecordDispatcher(asyncio.get_running_loop(), orch)
    d.start_consumer()
    d.submit("start")  # fails
    await _drain(d)
    d.submit("start")  # retry must not be coalesced
    await _drain(d)
    await d.aclose()
    assert orch.calls == ["start", "start"]
