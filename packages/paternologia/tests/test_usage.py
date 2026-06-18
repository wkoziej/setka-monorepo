# ABOUTME: Tests for PresetUsageIndex (which songs occupy a given preset/pattern slot).
# ABOUTME: Keys on the raw stored value; offset is purely a presentation concern.

from paternologia.models import (
    Action,
    ActionType,
    PacerButton,
    Song,
    SongMetadata,
)
from paternologia.usage import PresetUsageIndex


def _song(song_id: str, buttons: list[PacerButton], name: str | None = None) -> Song:
    return Song(
        song=SongMetadata(id=song_id, name=name or song_id.title()),
        pacer=buttons,
    )


def _btn(*actions: Action) -> PacerButton:
    return PacerButton(name="SW1", actions=list(actions))


class TestPresetUsageIndex:
    def test_two_songs_share_preset_slot(self):
        """Both songs using boss/preset/4 are returned with their names."""
        songs = [
            _song(
                "zen", [_btn(Action(device="boss", type=ActionType.PRESET, value=4))]
            ),
            _song(
                "rock",
                [_btn(Action(device="boss", type=ActionType.PRESET, value=4))],
                name="Rock Song",
            ),
        ]
        index = PresetUsageIndex.build(songs)
        result = index.lookup("boss", ActionType.PRESET, 4)
        assert [e.song_id for e in result] == ["zen", "rock"]
        assert {e.song_name for e in result} == {"Zen", "Rock Song"}

    def test_pattern_key_normalized_case_and_whitespace(self):
        """Pattern slot key is robust to case/whitespace differences."""
        songs = [
            _song(
                "a", [_btn(Action(device="ms", type=ActionType.PATTERN, value="F03"))]
            ),
            _song(
                "b", [_btn(Action(device="ms", type=ActionType.PATTERN, value=" f03 "))]
            ),
        ]
        index = PresetUsageIndex.build(songs)
        result = index.lookup("ms", ActionType.PATTERN, "f03")
        assert {e.song_id for e in result} == {"a", "b"}

    def test_exclude_song_id_removes_current_song(self):
        """A slot used only by the excluded song yields an empty list."""
        songs = [
            _song(
                "only", [_btn(Action(device="boss", type=ActionType.PRESET, value=7))]
            )
        ]
        index = PresetUsageIndex.build(songs)
        assert index.lookup("boss", ActionType.PRESET, 7, exclude_song_id="only") == []

    def test_same_slot_twice_in_one_song_dedups(self):
        """A slot used in two buttons of one song lists that song once."""
        songs = [
            _song(
                "dup",
                [
                    _btn(Action(device="boss", type=ActionType.PRESET, value=2)),
                    _btn(Action(device="boss", type=ActionType.PRESET, value=2)),
                ],
            )
        ]
        index = PresetUsageIndex.build(songs)
        result = index.lookup("boss", ActionType.PRESET, 2)
        assert [e.song_id for e in result] == ["dup"]

    def test_none_value_skipped(self):
        """Actions with no value never enter the index."""
        songs = [
            _song(
                "x", [_btn(Action(device="boss", type=ActionType.PRESET, value=None))]
            )
        ]
        index = PresetUsageIndex.build(songs)
        assert index.lookup("boss", ActionType.PRESET, 0) == []

    def test_cc_and_note_ignored(self):
        """Only preset/pattern slots are tracked; cc/note are transient."""
        songs = [
            _song(
                "x",
                [
                    _btn(Action(device="boss", type=ActionType.CC, value=5, cc=1)),
                    _btn(Action(device="freak", type=ActionType.NOTE, note="C4")),
                ],
            )
        ]
        index = PresetUsageIndex.build(songs)
        assert index.lookup("boss", ActionType.CC, 5) == []
        assert index.lookup("freak", ActionType.NOTE, "C4") == []

    def test_preset_int_and_pattern_str_do_not_collide(self):
        """Same device + same numeric look but different action_type stay separate."""
        songs = [
            _song(
                "p",
                [_btn(Action(device="ms", type=ActionType.PATTERN, value="3"))],
            ),
        ]
        index = PresetUsageIndex.build(songs)
        assert index.lookup("ms", ActionType.PATTERN, "3")
        assert index.lookup("ms", ActionType.PRESET, 3) == []

    def test_lookup_accepts_action_type_string(self):
        """Endpoint passes action_type as a query string; lookup coerces it."""
        songs = [
            _song("z", [_btn(Action(device="boss", type=ActionType.PRESET, value=9))])
        ]
        index = PresetUsageIndex.build(songs)
        assert [e.song_id for e in index.lookup("boss", "preset", 9)] == ["z"]

    def test_order_follows_song_order(self):
        """Entries keep the order songs were supplied in."""
        songs = [
            _song(
                "first", [_btn(Action(device="boss", type=ActionType.PRESET, value=1))]
            ),
            _song(
                "second", [_btn(Action(device="boss", type=ActionType.PRESET, value=1))]
            ),
            _song(
                "third", [_btn(Action(device="boss", type=ActionType.PRESET, value=1))]
            ),
        ]
        index = PresetUsageIndex.build(songs)
        result = index.lookup("boss", ActionType.PRESET, 1)
        assert [e.song_id for e in result] == ["first", "second", "third"]

    def test_empty_songs(self):
        index = PresetUsageIndex.build([])
        assert index.lookup("boss", ActionType.PRESET, 1) == []
