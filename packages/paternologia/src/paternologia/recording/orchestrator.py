# ABOUTME: Recording orchestrator — starts/stops OBS on PACER record triggers.
# ABOUTME: Bitwig transport record rides the MIDI bridge (MIDI-learn), not code.

import logging

from paternologia.recording.obs_client import ObsClient

logger = logging.getLogger(__name__)


class RecordingOrchestrator:
    """Translates PACER record triggers into OBS start/stop.

    Only OBS is driven from code. The same trigger note is also forwarded to
    Bitwig over the bridge, where it is MIDI-learned to Transport Record — so the
    two starts are coordinated by the single footswitch press, not by this class.
    Idempotency is delegated to the OBS client.
    """

    def __init__(self, obs_client: ObsClient):
        self._obs = obs_client

    def start(self) -> bool:
        """Start OBS recording (idempotent). Returns whether a start was issued."""
        issued = self._obs.start_record()
        logger.info("Orchestrator START (obs start issued=%s)", issued)
        return issued

    def stop(self) -> str | None:
        """Stop OBS recording (idempotent). Returns the output path, or None."""
        output_path = self._obs.stop_record()
        logger.info("Orchestrator STOP (output_path=%s)", output_path)
        return output_path
