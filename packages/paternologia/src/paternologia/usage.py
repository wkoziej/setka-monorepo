# ABOUTME: Reverse index from a preset/pattern slot to the songs that occupy it.
# ABOUTME: Keys on the raw stored value so display offset never affects matching.

import logging
from typing import NamedTuple

from paternologia.models import ActionType, Song
from paternologia.pacer.mappings import pattern_to_program

logger = logging.getLogger(__name__)

_TRACKED_TYPES = (ActionType.PRESET, ActionType.PATTERN)


class UsageEntry(NamedTuple):
    """A song that uses a particular slot."""

    song_id: str
    song_name: str


def _normalize_value(action_type: ActionType, value: int | str | None):
    """Build a stable slot key part from a raw action value.

    Presets compare as integers; patterns compare case/whitespace-insensitively.
    Returns ``None`` for values that should not be indexed.
    """
    if value is None:
        return None
    if action_type == ActionType.PRESET:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    if action_type == ActionType.PATTERN:
        text = str(value).strip()
        if not text:
            return None
        # Identify a pattern by its physical slot (program number), so equivalent
        # spellings collapse to one slot: "A9" == "A09", "a01" == "A01". This is
        # the same slot identity the hardware/export uses (pattern_to_program).
        return pattern_to_program(text)
    return None


def _coerce_action_type(action_type: ActionType | str) -> ActionType | None:
    if isinstance(action_type, ActionType):
        return action_type
    try:
        return ActionType(action_type)
    except ValueError:
        return None


class PresetUsageIndex:
    """Maps (device_id, action_type, raw value) → ordered list of songs using it."""

    def __init__(self, mapping: dict[tuple[str, str, object], list[UsageEntry]]):
        self._mapping = mapping

    @classmethod
    def build(cls, songs: list[Song]) -> "PresetUsageIndex":
        """Build the index by scanning every preset/pattern action in all songs.

        Mirrors ``SongMidiIndex.build`` in shape. A slot used multiple times
        within one song lists that song once; order follows ``songs``.
        """
        mapping: dict[tuple[str, str, object], list[UsageEntry]] = {}

        for song in songs:
            for button in song.pacer:
                for action in button.actions:
                    if action.type not in _TRACKED_TYPES:
                        continue
                    normalized = _normalize_value(action.type, action.value)
                    if normalized is None:
                        logger.debug(
                            "Song '%s': skipping %s action with empty value",
                            song.song.id,
                            action.type.value,
                        )
                        continue

                    key = (action.device, action.type.value, normalized)
                    entries = mapping.setdefault(key, [])
                    if not any(e.song_id == song.song.id for e in entries):
                        entries.append(UsageEntry(song.song.id, song.song.name))

        logger.info("Built preset usage index with %d slots", len(mapping))
        return cls(mapping)

    def lookup(
        self,
        device_id: str,
        action_type: ActionType | str,
        value: int | str | None,
        exclude_song_id: str | None = None,
    ) -> list[UsageEntry]:
        """Return songs occupying the slot, excluding ``exclude_song_id``."""
        coerced = _coerce_action_type(action_type)
        if coerced is None:
            return []
        normalized = _normalize_value(coerced, value)
        if normalized is None:
            return []

        key = (device_id, coerced.value, normalized)
        entries = self._mapping.get(key, [])
        return [e for e in entries if e.song_id != exclude_song_id]
