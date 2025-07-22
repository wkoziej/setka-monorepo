"""
Pytest fixtures for Medusa CLI tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def test_video_path() -> str:
    """Path to test video file."""
    return str(Path(__file__).parent.parent / "fixtures" / "test_video.mp4")


@pytest.fixture
def test_config_path() -> str:
    """Path to valid test config file."""
    return str(Path(__file__).parent.parent / "fixtures" / "test_config.json")


@pytest.fixture
def test_config_invalid_path() -> str:
    """Path to invalid test config file."""
    return str(Path(__file__).parent.parent / "fixtures" / "test_config_invalid.json")


@pytest.fixture
def temp_video_file() -> Generator[str, None, None]:
    """Create temporary test video file."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        # Create minimal video file content (just empty for now)
        tmp.write(b"fake video content")
        temp_path = tmp.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_config_file() -> Generator[str, None, None]:
    """Create temporary test config file."""
    config_content = '''
{
    "youtube": {
        "client_secrets_file": "path/to/client_secrets.json",
        "credentials_file": "path/to/credentials.json"
    }
}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp:
        tmp.write(config_content)
        temp_path = tmp.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path) 