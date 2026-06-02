# ABOUTME: Tests for the recording orchestrator and PACER record-trigger detection.
# ABOUTME: Orchestrator delegates to the OBS client; listener maps notes to actions.

from paternologia.midi.events import EventBus
from paternologia.midi.index import SongMidiIndex
from paternologia.midi.listener import MidiListener
from paternologia.recording.orchestrator import RecordingOrchestrator


class FakeObs:
    def __init__(self, start_result=True, stop_result="/rec/out.mkv"):
        self._start_result = start_result
        self._stop_result = stop_result
        self.calls = []

    def start_record(self):
        self.calls.append("start")
        return self._start_result

    def stop_record(self):
        self.calls.append("stop")
        return self._stop_result


class TestOrchestrator:
    def test_start_delegates_to_obs(self):
        obs = FakeObs(start_result=True)
        orch = RecordingOrchestrator(obs)
        assert orch.start() is True
        assert obs.calls == ["start"]

    def test_stop_returns_output_path(self):
        obs = FakeObs(stop_result="/rec/take.mkv")
        orch = RecordingOrchestrator(obs)
        assert orch.stop() == "/rec/take.mkv"
        assert obs.calls == ["stop"]


class TestRecordTriggerDetection:
    """Drives MidiListener._callback directly — no ALSA required."""

    def _listener(self):
        return MidiListener(
            song_index=SongMidiIndex.build([], []), event_bus=EventBus()
        )

    def _fire(self, listener, message):
        listener._callback((message, 0.0))

    def test_start_note_fires_start(self):
        listener = self._listener()
        actions = []
        listener.configure_record_trigger(0, 94, 93, actions.append)
        self._fire(listener, [0x90, 94, 127])  # Note On 94, ch 0
        assert actions == ["start"]

    def test_stop_note_fires_stop(self):
        listener = self._listener()
        actions = []
        listener.configure_record_trigger(0, 94, 93, actions.append)
        self._fire(listener, [0x90, 93, 127])  # Note On 93, ch 0
        assert actions == ["stop"]

    def test_note_off_does_not_fire(self):
        listener = self._listener()
        actions = []
        listener.configure_record_trigger(0, 94, 93, actions.append)
        self._fire(listener, [0x90, 94, 0])  # Note On velocity 0 == note off
        self._fire(listener, [0x80, 94, 0])  # Note Off
        assert actions == []

    def test_wrong_channel_does_not_fire(self):
        listener = self._listener()
        actions = []
        listener.configure_record_trigger(0, 94, 93, actions.append)
        self._fire(listener, [0x91, 94, 127])  # Note On 94 on ch 1
        assert actions == []

    def test_unrelated_note_does_not_fire(self):
        listener = self._listener()
        actions = []
        listener.configure_record_trigger(0, 94, 93, actions.append)
        self._fire(listener, [0x90, 60, 127])  # Note On 60
        assert actions == []

    def test_no_trigger_configured_is_safe(self):
        listener = self._listener()
        # No configure_record_trigger() call.
        self._fire(listener, [0x90, 94, 127])  # must not raise
