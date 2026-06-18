# ABOUTME: Integration tests for Paternologia API endpoints.
# ABOUTME: Tests songs CRUD and devices endpoints using FastAPI TestClient.

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from unittest.mock import patch, MagicMock

from paternologia import dependencies
from paternologia.main import app
from paternologia.models import ActionType, Device, PacerConfig, PacerExportSettings
from paternologia.storage import Storage


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_storage(temp_data_dir):
    """Create storage with temporary directory."""
    storage = Storage(data_dir=temp_data_dir)
    storage._ensure_dirs()
    return storage


@pytest.fixture
def sample_devices(test_storage):
    """Create sample devices in storage."""
    devices = [
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
    ]
    test_storage.save_devices(devices)
    return devices


@pytest.fixture
def client(test_storage, temp_data_dir):
    """Create test client with mocked storage."""
    original_templates = dependencies._templates
    original_templates_dir = dependencies.TEMPLATES_DIR
    original_data_dir = dependencies.DATA_DIR

    dependencies._storage = test_storage
    dependencies._templates = None
    dependencies.TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
    dependencies.DATA_DIR = temp_data_dir

    with TestClient(app) as client:
        yield client

    dependencies._storage = None
    dependencies._templates = original_templates
    dependencies.TEMPLATES_DIR = original_templates_dir
    dependencies.DATA_DIR = original_data_dir


class TestIndexPage:
    """Tests for main index page."""

    def test_index_empty(self, client, sample_devices):
        """Index page shows empty message when no songs."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Brak utworów" in response.text

    def test_index_with_songs(self, client, sample_devices, test_storage):
        """Index page lists songs."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        response = client.get("/")
        assert response.status_code == 200
        assert "Test Song" in response.text


class TestDevicesEndpoints:
    """Tests for devices API endpoints."""

    def test_devices_page(self, client, sample_devices):
        """Devices page lists all devices."""
        response = client.get("/devices")
        assert response.status_code == 200
        assert "Boss RC-600" in response.text
        assert "Elektron Model:Samples" in response.text

    def test_devices_json(self, client, sample_devices):
        """API returns devices as JSON."""
        response = client.get("/api/devices")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "boss"
        assert data[1]["id"] == "ms"


class TestSongView:
    """Tests for song view page."""

    def test_view_song_not_found(self, client, sample_devices):
        """Returns 404 for nonexistent song."""
        response = client.get("/songs/nonexistent")
        assert response.status_code == 404

    def test_view_song(self, client, sample_devices, test_storage):
        """View page shows song details."""
        from paternologia.models import Song, SongMetadata

        song = Song(
            song=SongMetadata(id="test", name="Test Song", notes="Test notes"),
        )
        test_storage.save_song(song)

        response = client.get("/songs/test")
        assert response.status_code == 200
        assert "Test Song" in response.text
        assert "Test notes" in response.text


class TestSongEdit:
    """Tests for song edit page."""

    def test_new_song_form(self, client, sample_devices):
        """New song form loads correctly."""
        response = client.get("/songs/new")
        assert response.status_code == 200
        assert "NOWY UTWÓR" in response.text

    def test_edit_song_form(self, client, sample_devices, test_storage):
        """Edit form loads with song data."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        response = client.get("/songs/test/edit")
        assert response.status_code == 200
        assert "Test Song" in response.text

    def test_edit_song_not_found(self, client, sample_devices):
        """Returns 404 for nonexistent song."""
        response = client.get("/songs/nonexistent/edit")
        assert response.status_code == 404


class TestSongCRUD:
    """Tests for song create/update/delete operations."""

    def test_create_song(self, client, sample_devices, test_storage):
        """Create a new song via POST."""
        response = client.post(
            "/songs",
            data={
                "song_id": "new-song",
                "song_name": "New Song",
                "song_author": "Test Author",
                "song_notes": "Test notes",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/songs/new-song"

        song = test_storage.get_song("new-song")
        assert song is not None
        assert song.song.name == "New Song"

    def test_create_song_missing_fields(self, client, sample_devices):
        """Create fails without required fields."""
        response = client.post(
            "/songs",
            data={"song_id": "", "song_name": ""},
        )
        assert response.status_code == 400

    def test_create_duplicate_song(self, client, sample_devices, test_storage):
        """Create fails for duplicate ID."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="existing", name="Existing"))
        test_storage.save_song(song)

        response = client.post(
            "/songs",
            data={"song_id": "existing", "song_name": "Duplicate"},
        )
        assert response.status_code == 400

    def test_create_song_invalid_id(self, client, sample_devices):
        """Create fails for invalid song_id format."""
        response = client.post(
            "/songs",
            data={"song_id": "Bad Id", "song_name": "Test"},
        )
        assert response.status_code == 400

    def test_update_song(self, client, sample_devices, test_storage):
        """Update an existing song via PUT."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Original"))
        test_storage.save_song(song)

        response = client.put(
            "/songs/test",
            data={
                "song_name": "Updated Name",
                "song_author": "New Author",
                "song_notes": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        updated = test_storage.get_song("test")
        assert updated.song.name == "Updated Name"

    def test_update_song_not_found(self, client, sample_devices):
        """Update fails for nonexistent song."""
        response = client.put(
            "/songs/nonexistent",
            data={"song_name": "Test"},
        )
        assert response.status_code == 404

    def test_delete_song(self, client, sample_devices, test_storage):
        """Delete a song via DELETE."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="to-delete", name="Delete Me"))
        test_storage.save_song(song)

        response = client.delete("/songs/to-delete", follow_redirects=False)
        assert response.status_code == 303

        assert not test_storage.song_exists("to-delete")

    def test_delete_song_not_found(self, client, sample_devices):
        """Delete fails for nonexistent song."""
        response = client.delete("/songs/nonexistent")
        assert response.status_code == 404


class TestSongWithPacerButtons:
    """Tests for creating songs with PACER button configurations."""

    def test_create_song_with_buttons(self, client, sample_devices, test_storage):
        """Create song with PACER buttons and actions."""
        response = client.post(
            "/songs",
            data={
                "song_id": "with-buttons",
                "song_name": "Song With Buttons",
                "song_author": "",
                "song_notes": "",
                "device_boss_preset": "5",
                "device_boss_preset_name": "Test Preset",
                "button_0_name": "Start",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "preset",
                "button_0_action_0_value": "5",
                "button_0_action_0_label": "Start preset",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("with-buttons")
        assert song is not None
        assert len(song.pacer) == 1
        assert song.pacer[0].name == "Start"
        assert len(song.pacer[0].actions) == 1
        assert song.pacer[0].actions[0].value == 5


class TestSongPacerExport:
    """Tests for pacer_export field in song creation/update."""

    def test_create_song_with_pacer_export(self, client, sample_devices, test_storage):
        """Create song with custom pacer export settings."""
        response = client.post(
            "/songs",
            data={
                "song_id": "with-export",
                "song_name": "Song With Export",
                "song_author": "",
                "song_notes": "",
                "pacer_export_target_preset": "C4",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("with-export")
        assert song is not None
        assert song.song.pacer_export.target_preset == "C4"

    def test_create_song_default_pacer_export(
        self, client, sample_devices, test_storage
    ):
        """Create song without explicit pacer export gets default."""
        response = client.post(
            "/songs",
            data={
                "song_id": "no-export",
                "song_name": "Song Without Export",
                "song_author": "",
                "song_notes": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("no-export")
        assert song is not None
        assert song.song.pacer_export.target_preset == "A1"


class TestPacerSendEndpoint:
    """Tests for POST /pacer/send/{song_id} endpoint."""

    def test_send_to_pacer_success(self, client, sample_devices, test_storage):
        """Successfully sends .syx to Pacer via amidi."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        config = PacerConfig(device_name="PACER")
        test_storage.save_pacer_config(config)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch(
            "paternologia.routers.pacer.find_amidi_port", return_value="hw:8,0,0"
        ):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                response = client.post("/pacer/send/test")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
                assert data["preset"] == "A1"
                assert data["port"] == "hw:8,0,0"

                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert call_args[0] == "amidi"
                assert "-p" in call_args
                assert "hw:8,0,0" in call_args
                assert "-s" in call_args

    def test_send_to_pacer_custom_preset(self, client, sample_devices, test_storage):
        """Sends .syx with custom preset override."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        config = PacerConfig(device_name="PACER")
        test_storage.save_pacer_config(config)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch(
            "paternologia.routers.pacer.find_amidi_port", return_value="hw:8,0,0"
        ):
            with patch("subprocess.run", return_value=mock_result):
                response = client.post("/pacer/send/test", data={"preset": "B3"})

                assert response.status_code == 200
                data = response.json()
                assert data["preset"] == "B3"

    def test_send_to_pacer_uses_song_default_preset(
        self, client, sample_devices, test_storage
    ):
        """Uses song's default preset when not specified in query."""
        from paternologia.models import Song, SongMetadata

        song = Song(
            song=SongMetadata(
                id="test",
                name="Test Song",
                pacer_export=PacerExportSettings(target_preset="C4"),
            )
        )
        test_storage.save_song(song)

        config = PacerConfig(device_name="PACER")
        test_storage.save_pacer_config(config)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch(
            "paternologia.routers.pacer.find_amidi_port", return_value="hw:8,0,0"
        ):
            with patch("subprocess.run", return_value=mock_result):
                response = client.post("/pacer/send/test")

                assert response.status_code == 200
                data = response.json()
                assert data["preset"] == "C4"

    def test_send_to_pacer_song_not_found(self, client, sample_devices, test_storage):
        """Returns 404 when song doesn't exist."""
        config = PacerConfig(device_name="PACER")
        test_storage.save_pacer_config(config)

        response = client.post("/pacer/send/nonexistent")
        assert response.status_code == 404

    def test_send_to_pacer_missing_config(self, client, sample_devices, test_storage):
        """Returns 400 when pacer.yaml is missing."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        response = client.post("/pacer/send/test")
        assert response.status_code == 400
        assert "pacer.yaml" in response.json()["detail"]

    def test_send_to_pacer_invalid_preset(self, client, sample_devices, test_storage):
        """Returns 400 for invalid preset."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        config = PacerConfig(device_name="PACER")
        test_storage.save_pacer_config(config)

        with patch(
            "paternologia.routers.pacer.find_amidi_port", return_value="hw:8,0,0"
        ):
            response = client.post("/pacer/send/test", data={"preset": "E1"})
            assert response.status_code == 400
            assert "Invalid preset" in response.json()["detail"]

    def test_send_to_pacer_device_not_found(self, client, sample_devices, test_storage):
        """Returns 400 when device is not connected."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        config = PacerConfig(device_name="PACER")
        test_storage.save_pacer_config(config)

        with patch("paternologia.routers.pacer.find_amidi_port", return_value=None):
            response = client.post("/pacer/send/test")

            assert response.status_code == 400
            assert "Nie znaleziono" in response.json()["detail"]

    def test_send_to_pacer_amidi_not_found(self, client, sample_devices, test_storage):
        """Returns 500 when amidi is not installed."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        config = PacerConfig(device_name="PACER")
        test_storage.save_pacer_config(config)

        with patch(
            "paternologia.routers.pacer.find_amidi_port", return_value="hw:8,0,0"
        ):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                response = client.post("/pacer/send/test")

                assert response.status_code == 500
                assert "amidi not found" in response.json()["detail"]

    def test_send_to_pacer_amidi_failure(self, client, sample_devices, test_storage):
        """Returns 500 when amidi command fails."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="test", name="Test Song"))
        test_storage.save_song(song)

        config = PacerConfig(device_name="PACER")
        test_storage.save_pacer_config(config)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Device not found"

        with patch(
            "paternologia.routers.pacer.find_amidi_port", return_value="hw:8,0,0"
        ):
            with patch("subprocess.run", return_value=mock_result):
                response = client.post("/pacer/send/test")

                assert response.status_code == 500
                assert "amidi failed" in response.json()["detail"]


class TestSongsOrderEndpoint:
    """Tests for PUT /api/songs/order endpoint."""

    def test_update_songs_order(self, client, sample_devices, test_storage):
        """Update songs order via PUT."""
        from paternologia.models import Song, SongMetadata

        test_storage.save_song(Song(song=SongMetadata(id="alpha", name="Alpha")))
        test_storage.save_song(Song(song=SongMetadata(id="beta", name="Beta")))
        test_storage.save_song(Song(song=SongMetadata(id="gamma", name="Gamma")))

        response = client.put(
            "/api/songs/order",
            json=["gamma", "alpha", "beta"],
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        order = test_storage.get_songs_order()
        assert order == ["gamma", "alpha", "beta"]

    def test_update_songs_order_empty(self, client, sample_devices, test_storage):
        """Clear songs order via PUT with empty list."""
        test_storage.save_songs_order(["a", "b", "c"])

        response = client.put("/api/songs/order", json=[])
        assert response.status_code == 200

        order = test_storage.get_songs_order()
        assert order == []

    def test_get_songs_order(self, client, sample_devices, test_storage):
        """GET /api/songs/order returns current order."""
        test_storage.save_songs_order(["c", "a", "b"])

        response = client.get("/api/songs/order")
        assert response.status_code == 200
        assert response.json() == ["c", "a", "b"]

    def test_get_songs_order_empty(self, client, sample_devices, test_storage):
        """GET /api/songs/order returns empty list when no order set."""
        response = client.get("/api/songs/order")
        assert response.status_code == 200
        assert response.json() == []


class TestHTMXPartials:
    """Tests for HTMX partial endpoints."""

    def test_get_pacer_button_partial(self, client, sample_devices):
        """GET /partials/pacer-button returns valid HTML partial."""
        response = client.get("/partials/pacer-button?button_idx=0")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert 'name="button_0_name"' in response.text
        assert "pacer-button-card" in response.text

    def test_get_pacer_button_partial_with_index(self, client, sample_devices):
        """Button index is reflected in input names."""
        response = client.get("/partials/pacer-button?button_idx=3")

        assert response.status_code == 200
        assert 'name="button_3_name"' in response.text
        assert "#4" in response.text  # button_idx + 1

    def test_get_action_row_partial(self, client, sample_devices):
        """GET /partials/action-row returns valid HTML partial."""
        response = client.get("/partials/action-row?button_idx=0&action_idx=0")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert 'name="button_0_action_0_device"' in response.text
        assert "action-row" in response.text

    def test_get_action_row_partial_with_indices(self, client, sample_devices):
        """Action indices are reflected in input names."""
        response = client.get("/partials/action-row?button_idx=2&action_idx=4")

        assert response.status_code == 200
        assert 'name="button_2_action_4_device"' in response.text
        assert 'name="button_2_action_4_type"' in response.text

    def test_get_action_types_partial(self, client, sample_devices):
        """GET /partials/action-types returns options for device."""
        response = client.get(
            "/partials/action-types?device_id=boss&button_idx=0&action_idx=0"
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # boss supports preset and cc
        assert "preset" in response.text.lower()
        assert "cc" in response.text.lower()
        # boss does NOT support pattern
        assert "pattern" not in response.text.lower()

    def test_get_action_types_partial_pattern_device(self, client, sample_devices):
        """Action types for pattern-only device."""
        response = client.get(
            "/partials/action-types?device_id=ms&button_idx=0&action_idx=0"
        )

        assert response.status_code == 200
        # ms (Model:Samples) only supports pattern
        assert "pattern" in response.text.lower()
        assert "preset" not in response.text.lower()

    def test_get_action_types_partial_unknown_device(self, client, sample_devices):
        """Action types for unknown device returns empty."""
        response = client.get(
            "/partials/action-types?device_id=unknown&button_idx=0&action_idx=0"
        )

        assert response.status_code == 200
        # Should return empty or just placeholder option
        assert "preset" not in response.text.lower()

    def test_get_action_fields_partial_preset(self, client, sample_devices):
        """GET /partials/action-fields for preset type."""
        response = client.get(
            "/partials/action-fields?action_type=preset&button_idx=0&action_idx=0"
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Preset needs value and optional label
        assert 'name="button_0_action_0_value"' in response.text
        assert 'name="button_0_action_0_label"' in response.text
        # Preset does NOT need cc
        assert 'name="button_0_action_0_cc"' not in response.text

    def test_get_action_fields_partial_cc(self, client, sample_devices):
        """GET /partials/action-fields for cc type."""
        response = client.get(
            "/partials/action-fields?action_type=cc&button_idx=1&action_idx=2"
        )

        assert response.status_code == 200
        # CC needs cc number, value, and optional label
        assert 'name="button_1_action_2_cc"' in response.text
        assert 'name="button_1_action_2_value"' in response.text
        assert 'name="button_1_action_2_label"' in response.text

    def test_get_action_fields_partial_pattern(self, client, sample_devices):
        """GET /partials/action-fields for pattern type."""
        response = client.get(
            "/partials/action-fields?action_type=pattern&button_idx=0&action_idx=0"
        )

        assert response.status_code == 200
        # Pattern needs value (text) and optional label
        assert 'name="button_0_action_0_value"' in response.text
        assert 'name="button_0_action_0_label"' in response.text
        # Pattern does NOT need cc
        assert 'name="button_0_action_0_cc"' not in response.text


class TestPresetUsagePartial:
    """Tests for GET /partials/preset-usage (slot occupancy hint)."""

    @staticmethod
    def _devices_with_offset(test_storage):
        """Boss with hidden display offset 1; ms pattern device (offset 0)."""
        devices = [
            Device(
                id="boss",
                name="Boss RC-600",
                midi_channel=13,
                preset_display_offset=1,
                action_types=[ActionType.PRESET, ActionType.CC],
            ),
            Device(
                id="ms",
                name="Elektron M:S",
                midi_channel=14,
                action_types=[ActionType.PATTERN],
            ),
        ]
        test_storage.save_devices(devices)
        return devices

    @staticmethod
    def _song_with_preset(test_storage, song_id, name, value):
        from paternologia.models import (
            Action,
            ActionType as AT,
            PacerButton,
            Song,
            SongMetadata,
        )

        song = Song(
            song=SongMetadata(id=song_id, name=name),
            pacer=[
                PacerButton(
                    name="SW1",
                    actions=[Action(device="boss", type=AT.PRESET, value=value)],
                )
            ],
        )
        test_storage.save_song(song)
        return song

    def test_used_in_other_song_lists_name(self, client, test_storage):
        """UI number 5 (offset 1 → stored 4) shared by two songs; excludes self."""
        self._devices_with_offset(test_storage)
        self._song_with_preset(test_storage, "zen", "Zen", 4)
        self._song_with_preset(test_storage, "rock", "Rock Song", 4)

        response = client.get(
            "/partials/preset-usage",
            params={
                "device_id": "boss",
                "action_type": "preset",
                "value": "5",
                "song_id": "zen",
            },
        )
        assert response.status_code == 200
        assert "Rock Song" in response.text
        assert "Zen" not in response.text

    def test_free_slot(self, client, test_storage):
        """A slot used only by the current song reports as free."""
        self._devices_with_offset(test_storage)
        self._song_with_preset(test_storage, "zen", "Zen", 4)

        response = client.get(
            "/partials/preset-usage",
            params={
                "device_id": "boss",
                "action_type": "preset",
                "value": "5",
                "song_id": "zen",
            },
        )
        assert response.status_code == 200
        assert "wolny" in response.text.lower()

    def test_empty_value_returns_blank(self, client, test_storage):
        """No value entered → minimal/blank fragment, never an error."""
        self._devices_with_offset(test_storage)
        response = client.get(
            "/partials/preset-usage",
            params={"device_id": "boss", "action_type": "preset", "value": ""},
        )
        assert response.status_code == 200
        assert response.text.strip() == ""

    def test_cc_type_returns_blank(self, client, test_storage):
        """cc actions are not slots → blank fragment."""
        self._devices_with_offset(test_storage)
        response = client.get(
            "/partials/preset-usage",
            params={"device_id": "boss", "action_type": "cc", "value": "5"},
        )
        assert response.status_code == 200
        assert response.text.strip() == ""

    def test_new_song_excludes_nothing(self, client, test_storage):
        """Empty song_id (new song) → existing user of the slot is still listed."""
        self._devices_with_offset(test_storage)
        self._song_with_preset(test_storage, "zen", "Zen", 4)

        response = client.get(
            "/partials/preset-usage",
            params={
                "device_id": "boss",
                "action_type": "preset",
                "value": "5",
                "song_id": "",
            },
        )
        assert response.status_code == 200
        assert "Zen" in response.text

    def test_offset_applied_before_lookup(self, client, test_storage):
        """UI number 5 maps to stored 4; UI number 4 must NOT match stored 4."""
        self._devices_with_offset(test_storage)
        self._song_with_preset(test_storage, "zen", "Zen", 4)

        # UI 4 → stored 3 → no song uses stored 3 → free
        response = client.get(
            "/partials/preset-usage",
            params={
                "device_id": "boss",
                "action_type": "preset",
                "value": "4",
                "song_id": "",
            },
        )
        assert response.status_code == 200
        assert "Zen" not in response.text
        assert "wolny" in response.text.lower()

    def test_reflects_fresh_state_after_save(self, client, test_storage):
        """Index is built on demand → a newly saved song appears immediately."""
        self._devices_with_offset(test_storage)
        self._song_with_preset(test_storage, "zen", "Zen", 4)

        # Initially UI 5 (stored 4) is used only by zen → free for others (exclude zen)
        first = client.get(
            "/partials/preset-usage",
            params={
                "device_id": "boss",
                "action_type": "preset",
                "value": "5",
                "song_id": "zen",
            },
        )
        assert "wolny" in first.text.lower()

        # A new song lands on the same raw slot (stored 4)
        self._song_with_preset(test_storage, "rock", "Rock", 4)

        second = client.get(
            "/partials/preset-usage",
            params={
                "device_id": "boss",
                "action_type": "preset",
                "value": "5",
                "song_id": "zen",
            },
        )
        assert "Rock" in second.text


class TestPresetEditorWiring:
    """Tests for the editor: transparent display number + usage-hint wiring."""

    @staticmethod
    def _devices_with_offset(test_storage):
        devices = [
            Device(
                id="boss",
                name="Boss RC-600",
                midi_channel=13,
                preset_display_offset=1,
                action_types=[ActionType.PRESET, ActionType.CC],
            ),
            Device(
                id="ms",
                name="Elektron M:S",
                midi_channel=14,
                action_types=[ActionType.PATTERN],
            ),
        ]
        test_storage.save_devices(devices)
        return devices

    def test_edit_renders_display_number_and_hint(self, client, test_storage):
        """Boss preset stored raw 4 renders as 5 (offset 1) with usage wiring."""
        from paternologia.models import (
            Action,
            ActionType as AT,
            PacerButton,
            Song,
            SongMetadata,
        )

        self._devices_with_offset(test_storage)
        test_storage.save_song(
            Song(
                song=SongMetadata(id="zen", name="Zen"),
                pacer=[
                    PacerButton(
                        name="SW1",
                        actions=[Action(device="boss", type=AT.PRESET, value=4)],
                    )
                ],
            )
        )

        response = client.get("/songs/zen/edit")
        assert response.status_code == 200
        assert "/partials/preset-usage" in response.text
        assert "preset-usage" in response.text
        assert 'value="5"' in response.text  # raw 4 + offset 1

    def test_save_converts_display_to_stored(self, client, test_storage):
        """UI number 5 is persisted as raw 4 (offset removed on save)."""
        self._devices_with_offset(test_storage)
        response = client.post(
            "/songs",
            data={
                "song_id": "round-trip",
                "song_name": "Round Trip",
                "button_0_name": "SW1",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "preset",
                "button_0_action_0_value": "5",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("round-trip")
        assert song.pacer[0].actions[0].value == 4

    def test_cc_value_not_offset_on_save(self, client, test_storage):
        """CC value carries no display offset; stored exactly as entered."""
        self._devices_with_offset(test_storage)
        client.post(
            "/songs",
            data={
                "song_id": "cc-song",
                "song_name": "CC Song",
                "button_0_name": "SW1",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "cc",
                "button_0_action_0_cc": "10",
                "button_0_action_0_value": "5",
            },
            follow_redirects=False,
        )
        song = test_storage.get_song("cc-song")
        assert song.pacer[0].actions[0].value == 5

    def test_new_song_form_has_empty_song_id(self, client, test_storage):
        """New song form carries data-song-id="" so nothing is excluded."""
        self._devices_with_offset(test_storage)
        response = client.get("/songs/new")
        assert response.status_code == 200
        assert 'data-song-id=""' in response.text

    def test_pattern_rendered_without_offset(self, client, test_storage):
        """M:S pattern is consistent already → rendered verbatim, no offset."""
        from paternologia.models import (
            Action,
            ActionType as AT,
            PacerButton,
            Song,
            SongMetadata,
        )

        self._devices_with_offset(test_storage)
        test_storage.save_song(
            Song(
                song=SongMetadata(id="patt", name="Patt"),
                pacer=[
                    PacerButton(
                        name="SW1",
                        actions=[Action(device="ms", type=AT.PATTERN, value="F03")],
                    )
                ],
            )
        )

        response = client.get("/songs/patt/edit")
        assert response.status_code == 200
        assert 'value="F03"' in response.text

    def test_cc_fields_have_no_usage_hint(self, client, sample_devices):
        """cc action fields do not wire the preset-usage hint; preset fields do."""
        cc = client.get(
            "/partials/action-fields?action_type=cc&button_idx=0&action_idx=0"
        )
        assert "/partials/preset-usage" not in cc.text

        preset = client.get(
            "/partials/action-fields?action_type=preset&button_idx=0&action_idx=0"
        )
        assert "/partials/preset-usage" in preset.text
