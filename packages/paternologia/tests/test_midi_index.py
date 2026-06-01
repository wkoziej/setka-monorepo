# ABOUTME: Tests for SongMidiIndex reverse mapping.
# ABOUTME: Tests building index from songs/devices and looking up songs by MIDI channel+program.


from paternologia.midi.index import SongMidiIndex
from paternologia.models import (
    Action,
    ActionType,
    Device,
    PacerButton,
    Song,
    SongMetadata,
)


def _make_device(device_id: str, midi_channel: int, action_types=None) -> Device:
    """Create device. midi_channel uses 1-16 convention (as in devices.yaml)."""
    return Device(
        id=device_id,
        name=device_id.upper(),
        midi_channel=midi_channel,
        action_types=action_types or [ActionType.PRESET],
    )


def _make_song(song_id: str, actions: list[Action]) -> Song:
    return Song(
        song=SongMetadata(id=song_id, name=song_id.title()),
        pacer=[PacerButton(name="SW1", actions=actions)] if actions else [],
    )


class TestSongMidiIndex:
    """Tests for building and querying the reverse MIDI index.

    devices.yaml uses 1-16 (musician convention).
    rtmidi/lookup uses 0-15 (MIDI protocol).
    Index converts: key = (midi_channel - 1, program).
    """

    def test_lookup_finds_song_by_preset_action(self):
        """Should map (channel, program) to song_id. Device ch=13 → lookup ch=12."""
        devices = [_make_device("boss", midi_channel=13)]
        songs = [
            _make_song("zen", [Action(device="boss", type=ActionType.PRESET, value=2)])
        ]

        index = SongMidiIndex.build(songs, devices)
        assert index.lookup(channel=12, program=2) == "zen"

    def test_lookup_returns_none_for_unknown(self):
        """Should return None for unmapped channel/program."""
        devices = [_make_device("boss", midi_channel=13)]
        songs = [
            _make_song("zen", [Action(device="boss", type=ActionType.PRESET, value=2)])
        ]

        index = SongMidiIndex.build(songs, devices)
        assert index.lookup(channel=12, program=99) is None

    def test_ignores_non_preset_actions(self):
        """Should only index preset actions, not cc/pattern/note."""
        devices = [
            _make_device(
                "boss", midi_channel=13, action_types=[ActionType.PRESET, ActionType.CC]
            )
        ]
        songs = [
            _make_song(
                "zen", [Action(device="boss", type=ActionType.CC, value=1, cc=1)]
            )
        ]

        index = SongMidiIndex.build(songs, devices)
        assert index.lookup(channel=12, program=1) is None

    def test_handles_multiple_songs(self):
        """Should index multiple songs correctly."""
        devices = [_make_device("boss", midi_channel=13)]
        songs = [
            _make_song("zen", [Action(device="boss", type=ActionType.PRESET, value=2)]),
            _make_song(
                "rock", [Action(device="boss", type=ActionType.PRESET, value=5)]
            ),
        ]

        index = SongMidiIndex.build(songs, devices)
        assert index.lookup(channel=12, program=2) == "zen"
        assert index.lookup(channel=12, program=5) == "rock"

    def test_handles_empty_songs(self):
        """Should handle empty song list gracefully."""
        devices = [_make_device("boss", midi_channel=13)]
        index = SongMidiIndex.build([], devices)
        assert index.lookup(channel=12, program=1) is None

    def test_handles_unknown_device(self):
        """Should skip actions with unknown device IDs."""
        devices = [_make_device("boss", midi_channel=13)]
        songs = [
            _make_song(
                "zen", [Action(device="unknown", type=ActionType.PRESET, value=2)]
            )
        ]

        index = SongMidiIndex.build(songs, devices)
        assert index.lookup(channel=12, program=2) is None

    def test_conflict_first_match_wins(self):
        """When two songs map to same (channel, program), first one wins."""
        devices = [_make_device("boss", midi_channel=13)]
        songs = [
            _make_song(
                "first", [Action(device="boss", type=ActionType.PRESET, value=2)]
            ),
            _make_song(
                "second", [Action(device="boss", type=ActionType.PRESET, value=2)]
            ),
        ]

        index = SongMidiIndex.build(songs, devices)
        assert index.lookup(channel=12, program=2) == "first"

    def test_preset_value_mod_128(self):
        """Program number should be value % 128 for MIDI compatibility."""
        devices = [_make_device("boss", midi_channel=13)]
        songs = [
            _make_song(
                "zen", [Action(device="boss", type=ActionType.PRESET, value=130)]
            )
        ]

        index = SongMidiIndex.build(songs, devices)
        assert index.lookup(channel=12, program=2) == "zen"

    def test_uses_first_preset_action_per_song(self):
        """Should use the first preset action found in the song's buttons."""
        devices = [_make_device("boss", midi_channel=13)]
        songs = [
            _make_song(
                "zen",
                [
                    Action(device="boss", type=ActionType.PRESET, value=2),
                    Action(device="boss", type=ActionType.CC, value=1, cc=1),
                ],
            )
        ]

        index = SongMidiIndex.build(songs, devices)
        assert index.lookup(channel=12, program=2) == "zen"

    def test_multiple_devices_multiple_channels(self):
        """Should index presets across different devices/channels."""
        devices = [
            _make_device("boss", midi_channel=13),
            _make_device("freak", midi_channel=1),
        ]
        songs = [
            _make_song(
                "zen",
                [
                    Action(device="boss", type=ActionType.PRESET, value=2),
                    Action(device="freak", type=ActionType.PRESET, value=66),
                ],
            )
        ]

        index = SongMidiIndex.build(songs, devices)
        assert index.lookup(channel=12, program=2) == "zen"
        assert index.lookup(channel=0, program=66) == "zen"
