"""
Tests for CLI commands (TDD Red Phase).

These tests define the expected behavior of the Click-based upload command.
"""

from unittest.mock import patch, AsyncMock

import pytest
from click.testing import CliRunner

from medusa.cli.commands import upload_command
from medusa.uploaders.base import UploadResult


class TestUploadCommand:
    """Test upload command implementation."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_upload_command_valid_args(self, temp_video_file, temp_config_file):
        """Test upload command with valid arguments."""
        with patch("medusa.cli.commands.upload_video_async") as mock_upload:
            from medusa.uploaders.base import UploadResult

            mock_upload.return_value = UploadResult(
                platform="youtube",
                success=True,
                upload_id="test_id",
                media_url="https://youtube.com/watch?v=test_id",
            )

            result = self.runner.invoke(
                upload_command, [temp_video_file, "--config", temp_config_file]
            )

            assert result.exit_code == 0
            assert "✅ Upload successful" in result.output

    def test_upload_command_missing_config(self, temp_video_file):
        """Test upload command fails when config is missing."""
        result = self.runner.invoke(upload_command, [temp_video_file])

        assert result.exit_code == 2  # Click argument error
        assert "Missing option" in result.output

    def test_upload_command_invalid_video(self, temp_config_file):
        """Test upload command fails with non-existent video file."""
        result = self.runner.invoke(
            upload_command, ["/nonexistent/video.mp4", "--config", temp_config_file]
        )

        assert result.exit_code == 2  # Click validation error
        assert "does not exist" in result.output

    def test_upload_command_invalid_config(self, temp_video_file):
        """Test upload command fails with non-existent config file."""
        result = self.runner.invoke(
            upload_command, [temp_video_file, "--config", "/nonexistent/config.json"]
        )

        assert result.exit_code == 2  # Click validation error
        assert "does not exist" in result.output

    def test_upload_command_default_options(self, temp_video_file, temp_config_file):
        """Test upload command uses default values for optional arguments."""
        with patch("medusa.cli.commands.upload_video_async") as mock_upload:
            mock_upload.return_value = UploadResult(
                platform="youtube",
                success=True,
                upload_id="test_id",
                media_url="https://youtube.com/watch?v=test_id",
            )

            result = self.runner.invoke(
                upload_command, [temp_video_file, "--config", temp_config_file]
            )

            assert result.exit_code == 0

            # Check that upload was called with default metadata
            args, kwargs = mock_upload.call_args
            metadata = args[2]  # Third argument should be metadata
            assert metadata.privacy == "private"  # Default privacy
            assert "Uploaded via Medusa" in metadata.description  # Default description

    def test_upload_command_custom_metadata(self, temp_video_file, temp_config_file):
        """Test upload command with custom metadata options."""
        with patch("medusa.cli.commands.upload_video_async") as mock_upload:
            mock_upload.return_value = UploadResult(
                platform="youtube",
                success=True,
                upload_id="test_id",
                media_url="https://youtube.com/watch?v=test_id",
            )

            result = self.runner.invoke(
                upload_command,
                [
                    temp_video_file,
                    "--config",
                    temp_config_file,
                    "--title",
                    "Custom Title",
                    "--description",
                    "Custom Description",
                    "--privacy",
                    "unlisted",
                    "--tags",
                    "tag1,tag2,tag3",
                ],
            )

            assert result.exit_code == 0

            # Check that upload was called with custom metadata
            args, kwargs = mock_upload.call_args
            metadata = args[2]  # Third argument should be metadata
            assert metadata.title == "Custom Title"
            assert metadata.description == "Custom Description"
            assert metadata.privacy == "unlisted"
            assert metadata.tags == ["tag1", "tag2", "tag3"]

    def test_upload_command_authentication_error(
        self, temp_video_file, temp_config_file
    ):
        """Test upload command handles authentication errors."""
        with patch("medusa.cli.commands.upload_video_async") as mock_upload:
            from medusa.exceptions import AuthenticationError

            mock_upload.side_effect = AuthenticationError(
                "Invalid credentials", platform="youtube"
            )

            result = self.runner.invoke(
                upload_command, [temp_video_file, "--config", temp_config_file]
            )

            assert result.exit_code == 3  # Authentication error code
            assert "Authentication failed" in result.output

    def test_upload_command_network_error(self, temp_video_file, temp_config_file):
        """Test upload command handles network errors."""
        with patch("medusa.cli.commands.upload_video_async") as mock_upload:
            from medusa.exceptions import NetworkError

            mock_upload.side_effect = NetworkError("Connection failed")

            result = self.runner.invoke(
                upload_command, [temp_video_file, "--config", temp_config_file]
            )

            assert result.exit_code == 4  # Network error code
            assert "Network error" in result.output

    def test_upload_command_general_error(self, temp_video_file, temp_config_file):
        """Test upload command handles general errors."""
        with patch("medusa.cli.commands.upload_video_async") as mock_upload:
            mock_upload.side_effect = Exception("Unexpected error")

            result = self.runner.invoke(
                upload_command, [temp_video_file, "--config", temp_config_file]
            )

            assert result.exit_code == 1  # General error code
            assert "Upload failed" in result.output

    def test_upload_command_help(self):
        """Test upload command shows helpful usage information."""
        result = self.runner.invoke(upload_command, ["--help"])

        assert result.exit_code == 0
        assert "Upload video to YouTube using Medusa" in result.output
        assert "VIDEO_PATH" in result.output
        assert "--config" in result.output
        assert "--title" in result.output
        assert "--description" in result.output
        assert "--privacy" in result.output
        assert "--tags" in result.output


class TestUploadVideoAsync:
    """Test the async upload function."""

    @pytest.mark.asyncio
    async def test_upload_video_async_success(self, temp_config_file):
        """Test successful video upload."""
        with patch("medusa.cli.commands.YouTubeUploader") as mock_uploader_class:
            mock_uploader = AsyncMock()
            mock_uploader_class.return_value = mock_uploader
            mock_uploader.authenticate.return_value = True
            mock_uploader.upload_media.return_value = UploadResult(
                platform="youtube",
                success=True,
                upload_id="test_id",
                media_url="https://youtube.com/watch?v=test_id",
            )

            from medusa.cli.commands import upload_video_async
            from medusa.models import MediaMetadata

            metadata = MediaMetadata(
                title="Test Video", description="Test Description", privacy="private"
            )

            result = await upload_video_async(
                video_path="/fake/video.mp4",
                config_path=temp_config_file,
                metadata=metadata,
            )

            assert result.success is True
            assert result.upload_id == "test_id"
            assert "youtube.com" in result.media_url

    @pytest.mark.asyncio
    async def test_upload_video_async_authentication_failure(self, temp_config_file):
        """Test upload failure due to authentication."""
        with patch("medusa.cli.commands.YouTubeUploader") as mock_uploader_class:
            mock_uploader = AsyncMock()
            mock_uploader_class.return_value = mock_uploader
            mock_uploader.authenticate.return_value = False

            from medusa.cli.commands import upload_video_async
            from medusa.models import MediaMetadata
            from medusa.exceptions import AuthenticationError

            metadata = MediaMetadata(
                title="Test Video", description="Test Description", privacy="private"
            )

            with pytest.raises(AuthenticationError):
                await upload_video_async(
                    video_path="/fake/video.mp4",
                    config_path=temp_config_file,
                    metadata=metadata,
                )
