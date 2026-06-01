# ABOUTME: API tests for Pacer export endpoint.
# ABOUTME: Tests /pacer/export/{song_id}.syx endpoint with various scenarios.

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paternologia import dependencies
from paternologia.main import app
from paternologia.models import (
    Action,
    ActionType,
    Device,
    PacerButton,
    Song,
    SongMetadata,
)
from paternologia.pacer import constants as c
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
            midi_channel=0,
            action_types=[ActionType.PRESET, ActionType.CC],
        ),
        Device(
            id="ms",
            name="Elektron M:S",
            midi_channel=1,
            action_types=[ActionType.PATTERN],
        ),
        Device(
            id="freak",
            name="MicroFreak",
            midi_channel=2,
            action_types=[ActionType.PRESET],
        ),
    ]
    test_storage.save_devices(devices)
    return devices


@pytest.fixture
def sample_song(test_storage):
    """Create a sample song."""
    song = Song(
        song=SongMetadata(id="test-song", name="Test Song"),
        pacer=[
            PacerButton(
                name="Start",
                actions=[
                    Action(device="boss", type=ActionType.PRESET, value=1),
                    Action(device="ms", type=ActionType.PATTERN, value="A01"),
                ],
            )
        ],
    )
    test_storage.save_song(song)
    return song


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


class TestExportEndpointHappyPath:
    """Tests for successful export scenarios."""

    def test_export_song(self, client, sample_devices, sample_song):
        """Export existing song returns .syx data."""
        response = client.get("/pacer/export/test-song.syx")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert "attachment" in response.headers["content-disposition"]
        assert "test-song" in response.headers["content-disposition"]

    def test_export_syx_format(self, client, sample_devices, sample_song):
        """Exported data is valid SysEx."""
        response = client.get("/pacer/export/test-song.syx")

        assert response.content[0] == c.SYSEX_START
        assert response.content[-1] == c.SYSEX_END

    def test_export_with_preset(self, client, sample_devices, sample_song):
        """Export with specific preset parameter."""
        response = client.get("/pacer/export/test-song.syx?preset=B3")

        assert response.status_code == 200
        assert "B3" in response.headers["content-disposition"]

    def test_export_contains_song_name(self, client, sample_devices, sample_song):
        """Exported data contains song name."""
        response = client.get("/pacer/export/test-song.syx")

        # "Test Song" truncated to 8 chars = "Test Son"
        assert b"Test Son" in response.content


class TestExportEndpointErrors:
    """Tests for error scenarios."""

    def test_export_song_not_found(self, client, sample_devices):
        """Export nonexistent song returns 404."""
        response = client.get("/pacer/export/nonexistent.syx")
        assert response.status_code == 404

    def test_export_invalid_preset(self, client, sample_devices, sample_song):
        """Export with invalid preset returns 400."""
        response = client.get("/pacer/export/test-song.syx?preset=Z9")

        assert response.status_code == 400
        assert "Invalid preset" in response.json()["detail"]

    def test_export_invalid_preset_format(self, client, sample_devices, sample_song):
        """Export with malformed preset returns 400."""
        response = client.get("/pacer/export/test-song.syx?preset=invalid")

        assert response.status_code == 400


class TestExportEdgeCases:
    """Tests for edge cases."""

    def test_export_empty_song(self, client, sample_devices, test_storage):
        """Export song without PACER buttons."""
        song = Song(song=SongMetadata(id="empty", name="Empty"), pacer=[])
        test_storage.save_song(song)

        response = client.get("/pacer/export/empty.syx")

        assert response.status_code == 200
        # All steps have MSG_CTRL_OFF (0x61)
        assert bytes([c.MSG_CTRL_OFF]) in response.content

    def test_export_unknown_device(self, client, sample_devices, test_storage):
        """Export song with unknown device uses channel 0."""
        song = Song(
            song=SongMetadata(id="unknown-dev", name="Unknown"),
            pacer=[
                PacerButton(
                    name="Btn",
                    actions=[
                        Action(device="unknown_device", type=ActionType.PRESET, value=1)
                    ],
                )
            ],
        )
        test_storage.save_song(song)

        response = client.get("/pacer/export/unknown-dev.syx")

        # Should not fail - uses channel 0 as fallback
        assert response.status_code == 200

    def test_export_full_buttons(self, client, sample_devices, test_storage):
        """Export song with 6 buttons, 6 actions each."""
        buttons = []
        for i in range(6):
            actions = [
                Action(device="boss", type=ActionType.PRESET, value=j) for j in range(6)
            ]
            buttons.append(PacerButton(name=f"Btn{i}", actions=actions))

        song = Song(song=SongMetadata(id="full", name="Full"), pacer=buttons)
        test_storage.save_song(song)

        response = client.get("/pacer/export/full.syx")

        assert response.status_code == 200
        # 36 PRESET steps should use MSG_SW_PRG_BANK (0x45)
        # Note: 'E' in some strings is also 0x45, so check >= 36
        assert response.content.count(bytes([c.MSG_SW_PRG_BANK])) >= 36

    def test_export_special_characters_in_name(
        self, client, sample_devices, test_storage
    ):
        """Export song with special characters in name."""
        song = Song(song=SongMetadata(id="special", name="Zażółć"), pacer=[])
        test_storage.save_song(song)

        response = client.get("/pacer/export/special.syx")

        # Non-ASCII replaced with ?
        assert response.status_code == 200


class TestExportPresetRange:
    """Tests for all valid preset values."""

    @pytest.mark.parametrize("row", "ABCD")
    @pytest.mark.parametrize("col", range(1, 7))
    def test_all_presets_valid(self, client, sample_devices, sample_song, row, col):
        """All A1-D6 presets are valid (Pacer has 4 banks x 6 presets)."""
        preset = f"{row}{col}"
        response = client.get(f"/pacer/export/test-song.syx?preset={preset}")

        assert response.status_code == 200
