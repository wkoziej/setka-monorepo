"""
Integration tests for YouTube API - requires real credentials.
These tests are skipped if credentials are not available.
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from medusa.uploaders.youtube import YouTubeUploader
from medusa.models import MediaMetadata, PlatformConfig


# Skip the REAL-API classes if credentials not available. The mocked OAuth-flow
# class below always runs (it never touches the network), so the skip is applied
# per-class rather than at module scope.
CREDENTIALS_PATH = "client_secrets.json"
SKIP_REAL_API = not os.path.exists(CREDENTIALS_PATH)

requires_real_credentials = pytest.mark.skipif(
    SKIP_REAL_API, reason="YouTube credentials not available - skipping real API tests"
)


class TestYouTubeAuthenticationFlowMocked:
    """OAuth authentication flow, mocked end-to-end (no browser, always runs).

    Replaces the previous skipif(True) placeholder that never executed: it
    exercises the real YouTubeUploader.authenticate -> YouTubeAuth.authenticate
    wiring, mocking only the OAuth boundary (the browser flow + Google API
    build).
    """

    @pytest.mark.asyncio
    async def test_oauth_flow_authenticates_without_browser(self):
        """A fresh OAuth flow (no stored creds) authenticates successfully."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "client_secrets_file": "client_secrets.json",
                "credentials_file": "credentials.json",
            },
        )
        uploader = YouTubeUploader(config=config)

        fake_credentials = MagicMock()

        with (
            # No existing creds on disk -> forces the OAuth flow branch.
            patch.object(
                uploader.auth_manager, "load_existing_credentials", return_value=False
            ),
            patch(
                "medusa.uploaders.youtube_auth.InstalledAppFlow"
            ) as mock_flow_cls,
            patch.object(
                uploader.auth_manager, "validate_credentials", return_value=True
            ),
            patch.object(uploader.auth_manager, "save_credentials"),
            patch("medusa.uploaders.youtube.build", return_value=MagicMock()),
        ):
            mock_flow = MagicMock()
            mock_flow.run_local_server.return_value = fake_credentials
            mock_flow_cls.from_client_secrets_file.return_value = mock_flow

            result = await uploader.authenticate()

            assert result is True
            assert uploader.is_authenticated is True
            # The flow was built from the configured client secrets and saved.
            mock_flow_cls.from_client_secrets_file.assert_called_once()
            uploader.auth_manager.save_credentials.assert_called_once()

    @pytest.mark.asyncio
    async def test_oauth_flow_uses_existing_valid_credentials(self):
        """When valid credentials already exist, no OAuth flow is started."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "client_secrets_file": "client_secrets.json",
                "credentials_file": "credentials.json",
            },
        )
        uploader = YouTubeUploader(config=config)

        with (
            patch.object(
                uploader.auth_manager, "load_existing_credentials", return_value=True
            ),
            patch.object(
                uploader.auth_manager, "validate_credentials", return_value=True
            ),
            patch.object(
                uploader.auth_manager, "start_oauth_flow"
            ) as mock_oauth,
            patch("medusa.uploaders.youtube.build", return_value=MagicMock()),
        ):
            uploader.auth_manager.credentials = MagicMock()
            result = await uploader.authenticate()

            assert result is True
            mock_oauth.assert_not_called()


@requires_real_credentials
class TestYouTubeRealAPI:
    """Integration tests with real YouTube API."""

    @pytest.fixture
    def uploader(self):
        """Create YouTube uploader with real credentials."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={"client_secrets_file": CREDENTIALS_PATH},
        )
        return YouTubeUploader(config=config)

    @pytest.mark.asyncio
    async def test_metadata_validation_real(self, uploader):
        """Test metadata validation with real constraints."""
        # Test with valid metadata
        metadata = MediaMetadata(
            title="Test Video - Medusa Library",
            description="This is a test video uploaded by Medusa library for testing purposes.",
            tags=["test", "medusa", "automation"],
            privacy="private",  # Always use private for tests
        )

        # Should not raise any exception
        uploader._validate_metadata(metadata)
        print("✅ Metadata validation passed!")

    @pytest.mark.asyncio
    async def test_video_upload_simulation(self, uploader):
        """Test video upload simulation (without actual file)."""
        print("\n" + "=" * 50)
        print("SIMULATION TEST: Video Upload")
        print("=" * 50)
        print("This test simulates video upload process without actual file.")

        # Create test metadata
        metadata = MediaMetadata(
            title=f"Test Upload - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="Automated test upload from Medusa library.\nThis video will be deleted after testing.",
            tags=["test", "automation", "medusa", "api_test"],
            privacy="private",  # Always private for tests
            category="science",
        )

        # Validate metadata
        uploader._validate_metadata(metadata)

        # Convert to YouTube format
        youtube_metadata = uploader._convert_metadata_to_youtube_format(metadata)

        # Verify conversion
        assert youtube_metadata["snippet"]["title"] == metadata.title
        assert youtube_metadata["snippet"]["description"] == metadata.description
        assert youtube_metadata["status"]["privacyStatus"] == "private"

        print("✅ Upload simulation successful!")
        print(f"📝 Metadata: {youtube_metadata}")


class TestYouTubeCredentialsSetup:
    """Tests for credential setup and validation."""

    def test_credentials_file_format(self):
        """Test if credentials file has correct format."""
        if not os.path.exists(CREDENTIALS_PATH):
            pytest.skip("Credentials file not available")

        import json

        with open(CREDENTIALS_PATH, "r") as f:
            credentials = json.load(f)

        # Check required fields
        assert "installed" in credentials or "web" in credentials

        client_config = credentials.get("installed") or credentials.get("web")
        assert "client_id" in client_config
        assert "client_secret" in client_config
        assert "auth_uri" in client_config
        assert "token_uri" in client_config

        print("✅ Credentials file format is valid!")


@pytest.mark.manual
class TestYouTubeManualTests:
    """
    Manual tests that require human interaction.
    Run with: pytest -m manual
    """

    @pytest.mark.asyncio
    async def test_full_upload_workflow(self):
        """
        MANUAL TEST: Complete upload workflow with real file.

        Prerequisites:
        1. Valid credentials in client_secrets.json
        2. Test video file (small, < 50MB recommended)
        3. Manual browser interaction for OAuth
        """
        print("\n" + "=" * 60)
        print("MANUAL TEST: Full YouTube Upload Workflow")
        print("=" * 60)
        print("⚠️  This test requires manual interaction!")
        print("📁 Place a test video file as 'test_video.mp4'")
        print("🌐 Browser will open for OAuth authentication")
        print("🔒 Video will be uploaded as PRIVATE")
        print("=" * 60)

        # Check for test video
        test_video = "test_video.mp4"
        if not os.path.exists(test_video):
            pytest.skip(f"Test video file '{test_video}' not found")

        # Setup uploader
        config = PlatformConfig(
            platform_name="youtube",
            credentials={"client_secrets_file": CREDENTIALS_PATH},
        )
        uploader = YouTubeUploader(config=config)

        # Create metadata
        metadata = MediaMetadata(
            title=f"Medusa Test Upload - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            description=(
                "🤖 Automated test upload from Medusa library\n\n"
                "This is a test video uploaded automatically by the Medusa media automation library. "
                "This video is uploaded as PRIVATE and will be deleted after testing.\n\n"
                f"Upload time: {datetime.now(timezone.utc).isoformat()}\n"
                "Repository: https://github.com/your-repo/medusa"
            ),
            tags=["medusa", "automation", "test", "api", "youtube", "upload"],
            privacy="private",  # ALWAYS private for tests
            category="science",
        )

        try:
            print("🔐 Starting authentication...")
            auth_result = await uploader.authenticate()
            assert auth_result, "Authentication failed"

            print("📤 Starting video upload...")
            result = await uploader.upload_media(test_video, metadata)

            assert result.success, f"Upload failed: {result}"

            print("✅ Upload successful!")
            print(f"📺 Video ID: {result.upload_id}")
            print(f"🔗 Video URL: {result.media_url}")
            print(f"📊 Metadata: {result.metadata}")

            # Store result for manual verification
            result_dict = {
                "platform": result.platform,
                "upload_id": result.upload_id,
                "success": result.success,
                "media_url": result.media_url,
                "metadata": result.metadata,
                "error": result.error,
                "timestamp": result.timestamp.isoformat(),
            }

            with open("last_upload_result.json", "w") as f:
                import json

                json.dump(result_dict, f, indent=2, default=str)

            print("💾 Upload result saved to 'last_upload_result.json'")
            print("🗑️  Remember to delete the test video from YouTube Studio!")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise


if __name__ == "__main__":
    print("YouTube Real API Integration Tests")
    print("=" * 40)

    if SKIP_REAL_API:
        print("❌ No credentials found!")
        print("📋 To run real API tests:")
        print("   1. Get YouTube API credentials from Google Cloud Console")
        print("   2. Save as 'client_secrets.json' in project root")
        print("   3. Run: pytest tests/integration/test_youtube_real_api.py -v")
    else:
        print("✅ Credentials found!")
        print("🚀 Run tests with: pytest tests/integration/test_youtube_real_api.py -v")
        print(
            "🔧 Manual tests: pytest tests/integration/test_youtube_real_api.py -m manual -v"
        )
