# ABOUTME: Reverse mapping from MIDI (channel, program) to song_id.
# ABOUTME: Built from songs and devices data for live song detection.

import logging

from paternologia.models import ActionType, Device, Song

logger = logging.getLogger(__name__)


class SongMidiIndex:
    """Maps (midi_channel, program_number) → song_id for live detection."""

    def __init__(self, mapping: dict[tuple[int, int], str]):
        self._mapping = mapping

    @classmethod
    def build(cls, songs: list[Song], devices: list[Device]) -> "SongMidiIndex":
        """Build index from songs and devices.

        Scans all songs for preset actions and maps
        (device.midi_channel, action.value % 128) → song.song.id.
        First match wins on conflicts.
        """
        device_map = {d.id: d for d in devices}
        mapping: dict[tuple[int, int], str] = {}

        for song in songs:
            for button in song.pacer:
                for action in button.actions:
                    if action.type != ActionType.PRESET:
                        continue
                    if action.value is None:
                        continue

                    device = device_map.get(action.device)
                    if device is None:
                        logger.warning(
                            "Song '%s': unknown device '%s', skipping",
                            song.song.id,
                            action.device,
                        )
                        continue

                    program = int(action.value) % 128
                    # devices.yaml uses 1-16 (musician convention),
                    # rtmidi uses 0-15 (MIDI protocol)
                    channel = device.midi_channel - 1
                    key = (channel, program)

                    if key in mapping:
                        logger.warning(
                            "MIDI conflict: (ch=%d, prog=%d) already mapped to '%s', "
                            "ignoring '%s'",
                            channel,
                            program,
                            mapping[key],
                            song.song.id,
                        )
                        continue

                    mapping[key] = song.song.id

        logger.info("Built MIDI index with %d entries", len(mapping))
        return cls(mapping)

    def lookup(self, channel: int, program: int) -> str | None:
        """Look up song_id by MIDI channel and program number."""
        return self._mapping.get((channel, program))
