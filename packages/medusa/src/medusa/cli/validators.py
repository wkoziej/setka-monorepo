"""
CLI validators for Medusa command-line interface.

Provides validation functions for video files, config files, and options
following DRY principle by reusing existing validation logic where possible.
"""

import json
from pathlib import Path
from typing import Optional, Union

from ..exceptions import MedusaError


class CLIValidationError(MedusaError):
    """Exception raised for CLI validation errors."""
    pass


def validate_video_file(file_path: Union[str, Path]) -> None:
    """
    Validate video file exists and has supported format.
    
    Args:
        file_path: Path to the video file
        
    Raises:
        CLIValidationError: If file doesn't exist or has unsupported format
    """
    if not file_path:
        raise CLIValidationError("Video file path cannot be empty")
    
    path = Path(file_path)
    
    if not path.exists():
        raise CLIValidationError(f"Video file not found: {file_path}")
    
    if not path.is_file():
        raise CLIValidationError(f"Path is not a file: {file_path}")
    
    # Check supported video formats
    supported_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
    if path.suffix.lower() not in supported_extensions:
        raise CLIValidationError(
            f"Unsupported video format: {path.suffix}. "
            f"Supported formats: {', '.join(sorted(supported_extensions))}"
        )


def validate_config_file(file_path: Union[str, Path]) -> None:
    """
    Validate config file exists, is valid JSON, and contains YouTube config.
    
    Args:
        file_path: Path to the config file
        
    Raises:
        CLIValidationError: If file doesn't exist, invalid JSON, or missing YouTube config
    """
    if not file_path:
        raise CLIValidationError("Config file path cannot be empty")
    
    path = Path(file_path)
    
    if not path.exists():
        raise CLIValidationError(f"Config file not found: {file_path}")
    
    if not path.is_file():
        raise CLIValidationError(f"Path is not a file: {file_path}")
    
    # Validate JSON format
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        raise CLIValidationError(f"Invalid JSON format in config file: {e}")
    except Exception as e:
        raise CLIValidationError(f"Error reading config file: {e}")
    
    # Validate YouTube configuration exists
    if not isinstance(config_data, dict):
        raise CLIValidationError("Config file must contain a JSON object")
    
    if 'youtube' not in config_data:
        raise CLIValidationError(
            "YouTube configuration not found in config file. "
            "Config must contain 'youtube' section with API credentials."
        )
    
    youtube_config = config_data['youtube']
    if not isinstance(youtube_config, dict):
        raise CLIValidationError("YouTube configuration must be an object")


def validate_privacy_option(privacy: Optional[str]) -> None:
    """
    Validate privacy option value.
    
    Args:
        privacy: Privacy setting value
        
    Raises:
        CLIValidationError: If privacy option is invalid
    """
    if not privacy:
        raise CLIValidationError("Privacy option cannot be empty")
    
    valid_options = {'private', 'unlisted', 'public'}
    if privacy not in valid_options:
        raise CLIValidationError(
            f"Invalid privacy option: {privacy}. "
            f"Valid options: {', '.join(sorted(valid_options))}"
        ) 