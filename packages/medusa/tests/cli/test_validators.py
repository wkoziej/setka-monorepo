"""
Tests for CLI validators (TDD Red Phase).

These tests are written first to define the expected behavior before implementation.
"""

import json
import tempfile
from pathlib import Path

import pytest

from medusa.cli.validators import (
    validate_video_file,
    validate_config_file,
    validate_privacy_option,
    CLIValidationError
)


class TestVideoFileValidation:
    """Test video file validation."""
    
    def test_validate_video_file_exists(self, temp_video_file):
        """Test that existing video file passes validation."""
        # This should pass without raising an exception
        validate_video_file(temp_video_file)
    
    def test_validate_video_file_not_exists(self):
        """Test that non-existing video file raises CLIValidationError."""
        with pytest.raises(CLIValidationError, match="Video file not found"):
            validate_video_file("/nonexistent/video.mp4")
    
    def test_validate_video_file_format_mp4(self, temp_video_file):
        """Test that .mp4 files are accepted."""
        # Rename to .mp4 extension
        mp4_path = temp_video_file.replace(".mp4", "_renamed.mp4")
        Path(temp_video_file).rename(mp4_path)
        
        validate_video_file(mp4_path)
        
        # Cleanup
        Path(mp4_path).unlink()
    
    def test_validate_video_file_format_invalid(self):
        """Test that invalid video formats raise CLIValidationError."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"not a video")
            txt_path = tmp.name
        
        try:
            with pytest.raises(CLIValidationError, match="Unsupported video format"):
                validate_video_file(txt_path)
        finally:
            Path(txt_path).unlink()
    
    def test_validate_video_file_empty_path(self):
        """Test that empty path raises CLIValidationError."""
        with pytest.raises(CLIValidationError, match="Video file path cannot be empty"):
            validate_video_file("")


class TestConfigFileValidation:
    """Test config file validation."""
    
    def test_validate_config_file_exists(self, temp_config_file):
        """Test that existing config file passes validation."""
        validate_config_file(temp_config_file)
    
    def test_validate_config_file_not_exists(self):
        """Test that non-existing config file raises CLIValidationError."""
        with pytest.raises(CLIValidationError, match="Config file not found"):
            validate_config_file("/nonexistent/config.json")
    
    def test_validate_config_file_format_valid_json(self, temp_config_file):
        """Test that valid JSON config passes validation."""
        validate_config_file(temp_config_file)
    
    def test_validate_config_file_format_invalid_json(self):
        """Test that invalid JSON raises CLIValidationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp:
            tmp.write("{ invalid json")
            invalid_json_path = tmp.name
        
        try:
            with pytest.raises(CLIValidationError, match="Invalid JSON format"):
                validate_config_file(invalid_json_path)
        finally:
            Path(invalid_json_path).unlink()
    
    def test_validate_config_file_missing_youtube_section(self):
        """Test that config without youtube section raises CLIValidationError."""
        config_content = json.dumps({"facebook": {"access_token": "test"}})
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp:
            tmp.write(config_content)
            config_path = tmp.name
        
        try:
            with pytest.raises(CLIValidationError, match="YouTube configuration not found"):
                validate_config_file(config_path)
        finally:
            Path(config_path).unlink()
    
    def test_validate_config_file_empty_path(self):
        """Test that empty path raises CLIValidationError."""
        with pytest.raises(CLIValidationError, match="Config file path cannot be empty"):
            validate_config_file("")


class TestPrivacyOptionValidation:
    """Test privacy option validation."""
    
    def test_validate_privacy_option_private(self):
        """Test that 'private' privacy option passes validation."""
        validate_privacy_option("private")
    
    def test_validate_privacy_option_unlisted(self):
        """Test that 'unlisted' privacy option passes validation."""
        validate_privacy_option("unlisted")
    
    def test_validate_privacy_option_public(self):
        """Test that 'public' privacy option passes validation."""
        validate_privacy_option("public")
    
    def test_validate_privacy_option_invalid(self):
        """Test that invalid privacy option raises CLIValidationError."""
        with pytest.raises(CLIValidationError, match="Invalid privacy option"):
            validate_privacy_option("invalid_option")
    
    def test_validate_privacy_option_empty(self):
        """Test that empty privacy option raises CLIValidationError."""
        with pytest.raises(CLIValidationError, match="Privacy option cannot be empty"):
            validate_privacy_option("")
    
    def test_validate_privacy_option_none(self):
        """Test that None privacy option raises CLIValidationError."""
        with pytest.raises(CLIValidationError, match="Privacy option cannot be empty"):
            validate_privacy_option(None) 