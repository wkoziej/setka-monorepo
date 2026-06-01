# ABOUTME: Unit tests for YAML storage layer.
# ABOUTME: Tests reading/writing devices and songs to YAML files.

import tempfile
from datetime import date

import pytest

from paternologia.models import (
    Action,
    ActionType,
    Device,
    PacerButton,
    PacerConfig,
    Song,
    SongMetadata,
)
from paternologia.storage import Storage


@pytest.fixture
def temp_storage():
    """Create a Storage instance with temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Storage(data_dir=tmpdir)


@pytest.fixture
def sample_devices():
    """Sample device list for testing."""
    return [
        Device(
            id="boss",
            name="Boss RC-600",
            description="Loop Station",
            action_types=[ActionType.PRESET, ActionType.CC],
        ),
        Device(
            id="ms",
            name="Elektron Model:Samples",
            description="Sampler/Sequencer",
            action_types=[ActionType.PATTERN],
        ),
        Device(
            id="freak",
            name="Arturia MicroFreak",
            description="Synthesizer",
            action_types=[ActionType.PRESET],
        ),
    ]


@pytest.fixture
def sample_song():
    """Sample song for testing."""
    return Song(
        song=SongMetadata(
            id="w-ciszy",
            name="W ciszy",
            author="Wojtek",
            created=date(2024, 12, 14),
            notes="Ballada, tempo 72 BPM",
        ),
        pacer=[
            PacerButton(
                name="Start",
                actions=[
                    Action(
                        device="boss", type=ActionType.PRESET, value=1, label="W ciszy"
                    ),
                    Action(device="ms", type=ActionType.PATTERN, value="A0"),
                    Action(
                        device="freak",
                        type=ActionType.PRESET,
                        value=51,
                        label="W ciszy",
                    ),
                    Action(
                        device="boss",
                        type=ActionType.CC,
                        cc=1,
                        value=127,
                        label="Play/Rec",
                    ),
                ],
            ),
            PacerButton(
                name="Verse",
                actions=[
                    Action(device="ms", type=ActionType.PATTERN, value="A1"),
                    Action(
                        device="boss",
                        type=ActionType.CC,
                        cc=1,
                        value=127,
                        label="Play/Rec",
                    ),
                ],
            ),
        ],
    )


class TestDeviceStorage:
    """Tests for device YAML storage."""

    def test_get_devices_empty(self, temp_storage):
        """Returns empty list when no devices file exists."""
        devices = temp_storage.get_devices()
        assert devices == []

    def test_save_and_get_devices(self, temp_storage, sample_devices):
        """Devices can be saved and loaded."""
        temp_storage.save_devices(sample_devices)
        loaded = temp_storage.get_devices()

        assert len(loaded) == 3
        assert loaded[0].id == "boss"
        assert loaded[0].name == "Boss RC-600"
        assert ActionType.PRESET in loaded[0].action_types

    def test_get_device_by_id(self, temp_storage, sample_devices):
        """Single device can be retrieved by ID."""
        temp_storage.save_devices(sample_devices)

        boss = temp_storage.get_device("boss")
        assert boss is not None
        assert boss.name == "Boss RC-600"

        unknown = temp_storage.get_device("unknown")
        assert unknown is None

    def test_devices_file_created(self, temp_storage, sample_devices):
        """Saving devices creates the file."""
        temp_storage.save_devices(sample_devices)
        assert temp_storage.devices_file.exists()


class TestSongStorage:
    """Tests for song YAML storage."""

    def test_get_songs_empty(self, temp_storage):
        """Returns empty list when no songs exist."""
        songs = temp_storage.get_songs()
        assert songs == []

    def test_save_and_get_song(self, temp_storage, sample_song):
        """Song can be saved and loaded."""
        temp_storage.save_song(sample_song)
        loaded = temp_storage.get_song("w-ciszy")

        assert loaded is not None
        assert loaded.song.id == "w-ciszy"
        assert loaded.song.name == "W ciszy"
        assert loaded.song.author == "Wojtek"
        assert len(loaded.pacer) == 2

    def test_get_songs_multiple(self, temp_storage, sample_song):
        """Multiple songs can be loaded."""
        temp_storage.save_song(sample_song)

        song2 = Song(
            song=SongMetadata(id="another", name="Another Song"),
        )
        temp_storage.save_song(song2)

        songs = temp_storage.get_songs()
        assert len(songs) == 2

    def test_get_song_not_found(self, temp_storage):
        """Returns None when song not found."""
        song = temp_storage.get_song("nonexistent")
        assert song is None

    def test_delete_song(self, temp_storage, sample_song):
        """Song can be deleted."""
        temp_storage.save_song(sample_song)
        assert temp_storage.song_exists("w-ciszy")

        result = temp_storage.delete_song("w-ciszy")
        assert result is True
        assert not temp_storage.song_exists("w-ciszy")

    def test_delete_song_not_found(self, temp_storage):
        """Deleting nonexistent song returns False."""
        result = temp_storage.delete_song("nonexistent")
        assert result is False

    def test_song_exists(self, temp_storage, sample_song):
        """song_exists returns correct status."""
        assert not temp_storage.song_exists("w-ciszy")

        temp_storage.save_song(sample_song)
        assert temp_storage.song_exists("w-ciszy")

    def test_song_file_created(self, temp_storage, sample_song):
        """Saving song creates the file."""
        temp_storage.save_song(sample_song)
        song_file = temp_storage.songs_dir / "w-ciszy.yaml"
        assert song_file.exists()

    def test_songs_sorted_by_filename(self, temp_storage):
        """Songs are returned sorted by filename."""
        temp_storage.save_song(Song(song=SongMetadata(id="zebra", name="Zebra")))
        temp_storage.save_song(Song(song=SongMetadata(id="alpha", name="Alpha")))
        temp_storage.save_song(Song(song=SongMetadata(id="beta", name="Beta")))

        songs = temp_storage.get_songs()
        ids = [s.song.id for s in songs]
        assert ids == ["alpha", "beta", "zebra"]


class TestSongsOrder:
    """Tests for songs ordering via songs_order.yaml."""

    def test_get_songs_order_empty_when_no_file(self, temp_storage):
        """Returns empty list when songs_order.yaml doesn't exist."""
        order = temp_storage.get_songs_order()
        assert order == []

    def test_save_and_get_songs_order(self, temp_storage):
        """Songs order can be saved and loaded."""
        order = ["song-c", "song-a", "song-b"]
        temp_storage.save_songs_order(order)

        loaded = temp_storage.get_songs_order()
        assert loaded == ["song-c", "song-a", "song-b"]

    def test_songs_order_file_location(self, temp_storage):
        """Songs order is saved to data/songs_order.yaml."""
        temp_storage.save_songs_order(["test"])
        order_file = temp_storage.data_dir / "songs_order.yaml"
        assert order_file.exists()

    def test_get_songs_respects_order(self, temp_storage):
        """get_songs() returns songs in order from songs_order.yaml."""
        temp_storage.save_song(Song(song=SongMetadata(id="zebra", name="Zebra")))
        temp_storage.save_song(Song(song=SongMetadata(id="alpha", name="Alpha")))
        temp_storage.save_song(Song(song=SongMetadata(id="beta", name="Beta")))
        temp_storage.save_songs_order(["beta", "zebra", "alpha"])

        songs = temp_storage.get_songs()
        ids = [s.song.id for s in songs]
        assert ids == ["beta", "zebra", "alpha"]

    def test_get_songs_appends_unordered_songs_at_end(self, temp_storage):
        """Songs not in order file are appended at the end alphabetically."""
        temp_storage.save_song(Song(song=SongMetadata(id="zebra", name="Zebra")))
        temp_storage.save_song(Song(song=SongMetadata(id="alpha", name="Alpha")))
        temp_storage.save_song(Song(song=SongMetadata(id="beta", name="Beta")))
        temp_storage.save_songs_order(["beta"])

        songs = temp_storage.get_songs()
        ids = [s.song.id for s in songs]
        assert ids == ["beta", "alpha", "zebra"]

    def test_get_songs_ignores_missing_ids_in_order(self, temp_storage):
        """Order file can contain IDs of deleted songs - they're ignored."""
        temp_storage.save_song(Song(song=SongMetadata(id="alpha", name="Alpha")))
        temp_storage.save_songs_order(["deleted", "alpha", "also-deleted"])

        songs = temp_storage.get_songs()
        ids = [s.song.id for s in songs]
        assert ids == ["alpha"]

    def test_update_songs_order(self, temp_storage):
        """Songs order can be updated (replaced)."""
        temp_storage.save_songs_order(["a", "b", "c"])
        temp_storage.save_songs_order(["c", "b", "a"])

        loaded = temp_storage.get_songs_order()
        assert loaded == ["c", "b", "a"]


class TestStorageDirectoryCreation:
    """Tests for automatic directory creation."""

    def test_ensure_dirs_creates_structure(self, temp_storage):
        """_ensure_dirs creates necessary directories."""
        temp_storage._ensure_dirs()
        assert temp_storage.data_dir.exists()
        assert temp_storage.songs_dir.exists()

    def test_save_creates_directories(self, temp_storage, sample_song):
        """Saving automatically creates directories."""
        temp_storage.save_song(sample_song)
        assert temp_storage.songs_dir.exists()


class TestPacerConfigStorage:
    """Tests for PacerConfig YAML storage."""

    def test_get_pacer_config_returns_none_when_missing(self, temp_storage):
        """Returns None when pacer.yaml doesn't exist."""
        config = temp_storage.get_pacer_config()
        assert config is None

    def test_save_and_get_pacer_config(self, temp_storage):
        """PacerConfig can be saved and loaded."""
        config = PacerConfig(device_name="PACER", amidi_timeout_seconds=10)
        temp_storage.save_pacer_config(config)

        loaded = temp_storage.get_pacer_config()
        assert loaded is not None
        assert loaded.device_name == "PACER"
        assert loaded.amidi_timeout_seconds == 10

    def test_pacer_config_file_location(self, temp_storage):
        """PacerConfig is saved to data/pacer.yaml."""
        config = PacerConfig(device_name="RC-600")
        temp_storage.save_pacer_config(config)

        pacer_file = temp_storage.data_dir / "pacer.yaml"
        assert pacer_file.exists()

    def test_get_pacer_config_with_default_timeout(self, temp_storage):
        """PacerConfig uses default timeout when not specified."""
        config = PacerConfig()
        temp_storage.save_pacer_config(config)

        loaded = temp_storage.get_pacer_config()
        assert loaded.amidi_timeout_seconds == 5
