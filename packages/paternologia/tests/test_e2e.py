# ABOUTME: End-to-end tests for Paternologia application.
# ABOUTME: Tests full user workflows from browsing to creating and managing songs.

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paternologia import dependencies
from paternologia.main import app
from paternologia.models import ActionType, Device
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
def setup_devices(test_storage):
    """Setup standard devices for testing."""
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
        Device(
            id="freak",
            name="Arturia MicroFreak",
            description="Synthesizer",
            action_types=[ActionType.PRESET, ActionType.NOTE],
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


class TestFullUserWorkflow:
    """E2E tests for complete user workflows."""

    def test_browse_empty_app(self, client, setup_devices):
        """User can browse empty app and see devices."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Brak utworów" in response.text
        assert "Nowy utwór" in response.text

        response = client.get("/devices")
        assert response.status_code == 200
        assert "Boss RC-600" in response.text
        assert "Elektron Model:Samples" in response.text
        assert "Arturia MicroFreak" in response.text

    def test_create_view_edit_delete_song(self, client, setup_devices, test_storage):
        """User can create, view, edit, and delete a song."""
        response = client.get("/songs/new")
        assert response.status_code == 200
        assert "NOWY UTWÓR" in response.text
        # Devices are loaded via HTMX partials, not on initial page
        # Verify HTMX button for adding PACER buttons is present
        assert "hx-get" in response.text
        assert "/partials/pacer-button" in response.text

        response = client.post(
            "/songs",
            data={
                "song_id": "test-song",
                "song_name": "Test Song",
                "song_author": "Test Author",
                "song_notes": "Test notes here",
                "device_boss_preset": "5",
                "device_boss_preset_name": "My Preset",
                "device_ms_pattern": "B2",
                "button_0_name": "Intro",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "preset",
                "button_0_action_0_value": "5",
                "button_0_action_0_label": "Intro preset",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/songs/test-song"

        response = client.get("/songs/test-song")
        assert response.status_code == 200
        assert "Test Song" in response.text
        assert "Test notes here" in response.text
        assert "preset 5" in response.text.lower()
        assert "Intro" in response.text

        response = client.get("/")
        assert response.status_code == 200
        assert "Test Song" in response.text

        response = client.get("/songs/test-song/edit")
        assert response.status_code == 200
        assert "EDYCJA: Test Song" in response.text

        response = client.put(
            "/songs/test-song",
            data={
                "song_name": "Updated Song Name",
                "song_author": "New Author",
                "song_notes": "Updated notes",
                "device_boss_preset": "10",
                "device_boss_preset_name": "Updated Preset",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        response = client.get("/songs/test-song")
        assert response.status_code == 200
        assert "Updated Song Name" in response.text

        response = client.delete("/songs/test-song", follow_redirects=False)
        assert response.status_code == 303

        response = client.get("/songs/test-song")
        assert response.status_code == 404

        response = client.get("/")
        assert response.status_code == 200
        assert "Updated Song Name" not in response.text

    def test_create_song_with_multiple_pacer_buttons(
        self, client, setup_devices, test_storage
    ):
        """User can create a song with multiple PACER buttons and actions."""
        response = client.post(
            "/songs",
            data={
                "song_id": "multi-button",
                "song_name": "Multi Button Song",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Verse",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "preset",
                "button_0_action_0_value": "1",
                "button_0_action_1_device": "ms",
                "button_0_action_1_type": "pattern",
                "button_0_action_1_value": "A0",
                "button_1_name": "Chorus",
                "button_1_action_0_device": "boss",
                "button_1_action_0_type": "cc",
                "button_1_action_0_cc": "2",
                "button_1_action_0_value": "127",
                "button_1_action_0_label": "Loop Start",
                "button_2_name": "Bridge",
                "button_2_action_0_device": "freak",
                "button_2_action_0_type": "preset",
                "button_2_action_0_value": "42",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("multi-button")
        assert song is not None
        assert len(song.pacer) == 3
        assert song.pacer[0].name == "Verse"
        assert len(song.pacer[0].actions) == 2
        assert song.pacer[1].name == "Chorus"
        assert song.pacer[1].actions[0].cc == 2
        assert song.pacer[2].name == "Bridge"

        response = client.get("/songs/multi-button")
        assert response.status_code == 200
        assert "3 przyciski" in response.text
        assert "Verse" in response.text
        assert "Chorus" in response.text
        assert "Bridge" in response.text

    def test_delete_first_action_keeps_second_action(
        self, client, setup_devices, test_storage
    ):
        """User can delete first action while keeping second action in same button.

        This tests the bug where deleting action[0] but keeping action[1] causes
        all actions to be lost because the form parser breaks on missing action_0.
        """
        # Create initial song with button containing 2 actions
        response = client.post(
            "/songs",
            data={
                "song_id": "action-delete-test",
                "song_name": "Action Delete Test",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Test Button",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "preset",
                "button_0_action_0_value": "1",
                "button_0_action_1_device": "ms",
                "button_0_action_1_type": "pattern",
                "button_0_action_1_value": "A0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("action-delete-test")
        assert len(song.pacer[0].actions) == 2
        assert song.pacer[0].actions[0].device == "boss"
        assert song.pacer[0].actions[1].device == "ms"

        # Now simulate deleting first action in UI by submitting form without action_0
        # but keeping action_1 (this is what happens when user clicks delete button in UI)
        response = client.put(
            "/songs/action-delete-test",
            data={
                "song_name": "Action Delete Test",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Test Button",
                # action_0 is MISSING (deleted in UI)
                "button_0_action_1_device": "ms",
                "button_0_action_1_type": "pattern",
                "button_0_action_1_value": "A0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        # Check that second action is still there (not all actions deleted)
        updated_song = test_storage.get_song("action-delete-test")
        assert len(updated_song.pacer[0].actions) == 1, (
            "Expected 1 action to remain, but got: "
            f"{[(a.device, a.type) for a in updated_song.pacer[0].actions]}"
        )
        assert updated_song.pacer[0].actions[0].device == "ms"
        assert updated_song.pacer[0].actions[0].type.value == "pattern"


class TestNoteActionType:
    """E2E tests for NOTE action type."""

    def test_create_song_with_note_action(self, client, setup_devices, test_storage):
        """User can create a song with NOTE action type."""
        response = client.post(
            "/songs",
            data={
                "song_id": "note-test",
                "song_name": "Note Test Song",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Trigger Note",
                "button_0_action_0_device": "freak",
                "button_0_action_0_type": "note",
                "button_0_action_0_note": "C4",
                "button_0_action_0_velocity": "100",
                "button_0_action_0_label": "Middle C",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("note-test")
        assert song is not None
        assert len(song.pacer) == 1
        assert song.pacer[0].actions[0].type.value == "note"
        assert song.pacer[0].actions[0].note == "C4"
        assert song.pacer[0].actions[0].velocity == 100

    def test_view_song_with_note_action(self, client, setup_devices, test_storage):
        """Song view page displays NOTE actions correctly."""
        response = client.post(
            "/songs",
            data={
                "song_id": "note-view-test",
                "song_name": "Note View Test",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Play F#3",
                "button_0_action_0_device": "freak",
                "button_0_action_0_type": "note",
                "button_0_action_0_note": "F#3",
                "button_0_action_0_velocity": "80",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        response = client.get("/songs/note-view-test")
        assert response.status_code == 200
        assert "note F#3" in response.text
        assert "vel=80" in response.text
        assert "MicroFreak" in response.text

    def test_edit_song_with_note_action_preserves_data(
        self, client, setup_devices, test_storage
    ):
        """Editing a song with NOTE action preserves note data."""
        response = client.post(
            "/songs",
            data={
                "song_id": "note-edit-test",
                "song_name": "Note Edit Test",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Original Note",
                "button_0_action_0_device": "freak",
                "button_0_action_0_type": "note",
                "button_0_action_0_note": "A4",
                "button_0_action_0_velocity": "127",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        response = client.get("/songs/note-edit-test/edit")
        assert response.status_code == 200
        assert 'value="A4"' in response.text or "A4" in response.text
        assert "127" in response.text

        response = client.put(
            "/songs/note-edit-test",
            data={
                "song_name": "Note Edit Test Updated",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Updated Note",
                "button_0_action_0_device": "freak",
                "button_0_action_0_type": "note",
                "button_0_action_0_note": "Bb5",
                "button_0_action_0_velocity": "64",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        updated_song = test_storage.get_song("note-edit-test")
        assert updated_song.pacer[0].actions[0].note == "Bb5"
        assert updated_song.pacer[0].actions[0].velocity == 64


class TestNavigationFlow:
    """E2E tests for navigation between pages."""

    def test_navigation_links(self, client, setup_devices, test_storage):
        """All navigation links work correctly."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="nav-test", name="Navigation Test"))
        test_storage.save_song(song)

        response = client.get("/")
        assert response.status_code == 200
        assert 'href="/devices"' in response.text
        assert 'href="/songs/new"' in response.text

        response = client.get("/devices")
        assert response.status_code == 200
        assert 'href="/"' in response.text

        response = client.get("/songs/nav-test")
        assert response.status_code == 200
        assert 'href="/"' in response.text
        assert 'href="/songs/nav-test/edit"' in response.text

        response = client.get("/songs/nav-test/edit")
        assert response.status_code == 200
        assert 'href="/songs/nav-test"' in response.text


class TestErrorHandling:
    """E2E tests for error scenarios."""

    def test_404_for_nonexistent_song(self, client, setup_devices):
        """App returns 404 for nonexistent songs."""
        response = client.get("/songs/does-not-exist")
        assert response.status_code == 404

        response = client.get("/songs/does-not-exist/edit")
        assert response.status_code == 404

    def test_duplicate_song_id_rejected(self, client, setup_devices, test_storage):
        """App rejects duplicate song IDs."""
        from paternologia.models import Song, SongMetadata

        song = Song(song=SongMetadata(id="existing", name="Existing Song"))
        test_storage.save_song(song)

        response = client.post(
            "/songs",
            data={"song_id": "existing", "song_name": "Duplicate Attempt"},
        )
        assert response.status_code == 400

    def test_missing_required_fields(self, client, setup_devices):
        """App rejects forms with missing required fields."""
        response = client.post(
            "/songs",
            data={"song_id": "", "song_name": ""},
        )
        assert response.status_code == 400

        response = client.post(
            "/songs",
            data={"song_id": "valid-id", "song_name": ""},
        )
        assert response.status_code == 400


class TestAPIEndpoints:
    """E2E tests for API endpoints."""

    def test_devices_json_api(self, client, setup_devices):
        """JSON API returns proper device data."""
        response = client.get("/api/devices")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3

        boss = next(d for d in data if d["id"] == "boss")
        assert boss["name"] == "Boss RC-600"
        assert "preset" in boss["action_types"]
        assert "cc" in boss["action_types"]

        ms = next(d for d in data if d["id"] == "ms")
        assert "pattern" in ms["action_types"]


class TestButtonReordering:
    """E2E tests for PACER button reordering functionality."""

    def test_reorder_buttons_preserves_data(self, client, setup_devices, test_storage):
        """When buttons are reordered in form, backend saves them in correct order.

        This tests the scenario where user moves button 3 to position 1.
        The form would then have:
        - button_0 = was button 3 (Bridge)
        - button_1 = was button 1 (Verse)
        - button_2 = was button 2 (Chorus)
        """
        # Create initial song with 3 buttons in order: Verse, Chorus, Bridge
        response = client.post(
            "/songs",
            data={
                "song_id": "reorder-test",
                "song_name": "Reorder Test",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Verse",
                "button_0_action_0_device": "boss",
                "button_0_action_0_type": "preset",
                "button_0_action_0_value": "1",
                "button_1_name": "Chorus",
                "button_1_action_0_device": "boss",
                "button_1_action_0_type": "preset",
                "button_1_action_0_value": "2",
                "button_2_name": "Bridge",
                "button_2_action_0_device": "ms",
                "button_2_action_0_type": "pattern",
                "button_2_action_0_value": "A0",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        song = test_storage.get_song("reorder-test")
        assert [b.name for b in song.pacer] == ["Verse", "Chorus", "Bridge"]

        # Now submit form with reordered buttons: Bridge, Verse, Chorus
        # This simulates what happens after JS reordering and renumbering
        response = client.put(
            "/songs/reorder-test",
            data={
                "song_name": "Reorder Test",
                "song_author": "",
                "song_notes": "",
                "button_0_name": "Bridge",
                "button_0_action_0_device": "ms",
                "button_0_action_0_type": "pattern",
                "button_0_action_0_value": "A0",
                "button_1_name": "Verse",
                "button_1_action_0_device": "boss",
                "button_1_action_0_type": "preset",
                "button_1_action_0_value": "1",
                "button_2_name": "Chorus",
                "button_2_action_0_device": "boss",
                "button_2_action_0_type": "preset",
                "button_2_action_0_value": "2",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        # Verify buttons are now in new order
        updated_song = test_storage.get_song("reorder-test")
        assert [b.name for b in updated_song.pacer] == ["Bridge", "Verse", "Chorus"]
        # Verify actions moved with buttons
        assert updated_song.pacer[0].actions[0].device == "ms"
        assert updated_song.pacer[1].actions[0].device == "boss"
        assert updated_song.pacer[1].actions[0].value == 1
