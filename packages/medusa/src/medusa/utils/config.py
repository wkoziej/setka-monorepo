"""
Configuration system for the Medusa library.

This module provides robust configuration loading and validation for the Medusa
media upload and social automation library. It supports JSON configuration files,
environment variable overrides, and comprehensive validation.
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Union

from ..exceptions import ConfigurationError
from ..models import PlatformConfig

logger = logging.getLogger(__name__)

# Flat configuration fields recognized in the JSON config file. They are mapped
# into the unified PlatformConfig.credentials dict that uploaders/publishers read.
KNOWN_PLATFORM_FIELDS = (
    "client_secrets_file",
    "credentials_file",
    "access_token",
    "api_key",
    "api_secret",
    "access_token_secret",
    "page_id",
    "app_id",
    "app_secret",
    "api_version",
)


@dataclass
class MedusaConfig:
    """
    Complete Medusa configuration containing all platform configurations.

    This dataclass holds configuration for all supported platforms and provides
    the main interface for accessing platform-specific settings.
    """

    youtube: Optional[PlatformConfig] = None
    facebook: Optional[PlatformConfig] = None
    vimeo: Optional[PlatformConfig] = None
    twitter: Optional[PlatformConfig] = None

    def get_platform_config(self, platform: str) -> Optional[PlatformConfig]:
        """
        Get configuration for a specific platform.

        Args:
            platform: Platform name (youtube, facebook, vimeo, twitter)

        Returns:
            PlatformConfig instance or None if not configured
        """
        return getattr(self, platform.lower(), None)

    def has_platform(self, platform: str) -> bool:
        """
        Check if a platform is configured.

        Args:
            platform: Platform name

        Returns:
            True if platform is configured, False otherwise
        """
        return self.get_platform_config(platform) is not None

    def get_configured_platforms(self) -> list[str]:
        """
        Get list of configured platform names.

        Returns:
            List of platform names that have configuration
        """
        platforms = []
        for platform in ["youtube", "facebook", "vimeo", "twitter"]:
            if self.has_platform(platform):
                platforms.append(platform)
        return platforms


class ConfigLoader:
    """
    Loads and validates Medusa configuration from JSON files.

    This class handles loading configuration from JSON files, applying
    environment variable overrides, and validating required fields for
    each platform.
    """

    # Platform-specific required fields
    PLATFORM_REQUIRED_FIELDS = {
        "youtube": ["client_secrets_file", "credentials_file"],
        "facebook": ["access_token", "page_id"],
        "vimeo": ["access_token"],
        "twitter": ["api_key", "api_secret", "access_token", "access_token_secret"],
    }

    # Environment variable field mappings
    ENV_FIELD_MAPPINGS = {
        "client_secrets_file": "CLIENT_SECRETS",
        "credentials_file": "CREDENTIALS",
        "access_token": "ACCESS_TOKEN",
        "api_key": "API_KEY",
        "api_secret": "API_SECRET",
        "access_token_secret": "ACCESS_TOKEN_SECRET",
        "page_id": "PAGE_ID",
    }

    def __init__(self, config_file_path: Union[str, Path]):
        """
        Initialize ConfigLoader with path to configuration file.

        Args:
            config_file_path: Path to JSON configuration file
        """
        self.config_file_path = Path(config_file_path)

    def load(self) -> MedusaConfig:
        """
        Load and validate configuration from file.

        Returns:
            MedusaConfig instance with loaded configuration

        Raises:
            ConfigurationError: If file not found, invalid JSON, or validation fails
        """
        try:
            # Load JSON configuration
            config_data = self._load_json_file()

            # Apply environment variable overrides
            config_data = self._apply_environment_overrides(config_data)

            # Validate and create platform configurations
            platform_configs = {}

            for platform in ["youtube", "facebook", "vimeo", "twitter"]:
                if platform in config_data:
                    platform_data = config_data[platform]

                    # Validate required fields
                    self._validate_platform_config(platform, platform_data)

                    # Create the unified platform config. Flat fields from the
                    # JSON file are folded into `credentials`, which is the shape
                    # every uploader/publisher reads (e.g. YouTubeAuth reads
                    # credentials["client_secrets_file"], FacebookAuth reads
                    # credentials["page_id"]). This kills the previous split where
                    # a flat config object had no `.credentials` attribute and the
                    # CLI silently produced credentials={}.
                    credentials = {
                        key: value
                        for key, value in platform_data.items()
                        if key in KNOWN_PLATFORM_FIELDS
                    }

                    # Warn about unrecognised keys so typos (e.g. 'acess_token')
                    # surface immediately instead of silently producing empty credentials.
                    unknown_keys = [
                        key for key in platform_data if key not in KNOWN_PLATFORM_FIELDS
                    ]
                    if unknown_keys:
                        logger.warning(
                            "Platform '%s': unknown config keys ignored: %s. "
                            "Check for typos; valid keys are: %s",
                            platform,
                            unknown_keys,
                            list(KNOWN_PLATFORM_FIELDS),
                        )

                    platform_configs[platform] = PlatformConfig(
                        platform_name=platform,
                        credentials=credentials,
                    )

            return MedusaConfig(**platform_configs)

        except (OSError, IOError, PermissionError) as e:
            raise ConfigurationError(
                f"Error reading configuration file '{self.config_file_path}': {e}"
            ) from e
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in configuration file '{self.config_file_path}': {e}"
            ) from e

    def _load_json_file(self) -> Dict[str, Any]:
        """
        Load JSON data from configuration file.

        Returns:
            Dictionary containing configuration data

        Raises:
            ConfigurationError: If file not found or cannot be read
        """
        if not self.config_file_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_file_path}"
            )

        try:
            with open(self.config_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in configuration file '{self.config_file_path}': {e}"
            ) from e

    def _apply_environment_overrides(
        self, config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration data.

        Args:
            config_data: Original configuration data

        Returns:
            Configuration data with environment overrides applied
        """
        # Create a deep copy to avoid modifying original
        config_copy = json.loads(json.dumps(config_data))

        for platform in ["youtube", "facebook", "vimeo", "twitter"]:
            # Initialize platform section if it doesn't exist but has env vars
            platform_data = config_copy.get(platform, {})
            has_env_overrides = False

            # Check each possible field for environment variable override
            for field_name, env_suffix in self.ENV_FIELD_MAPPINGS.items():
                env_var_name = self._get_env_var_name(platform, field_name)
                env_value = os.getenv(env_var_name)

                if env_value is not None:
                    platform_data[field_name] = env_value
                    has_env_overrides = True

            # Add platform data if we found environment overrides
            if has_env_overrides:
                config_copy[platform] = platform_data

        return config_copy

    def _get_env_var_name(self, platform: str, field_name: str) -> str:
        """
        Generate environment variable name for platform field.

        Args:
            platform: Platform name (youtube, facebook, etc.)
            field_name: Configuration field name

        Returns:
            Environment variable name (e.g., MEDUSA_YOUTUBE_ACCESS_TOKEN)
        """
        env_suffix = self.ENV_FIELD_MAPPINGS.get(field_name, field_name.upper())
        return f"MEDUSA_{platform.upper()}_{env_suffix}"

    def _validate_platform_config(self, platform: str, platform_data: Dict[str, Any]):
        """
        Validate that platform configuration has all required fields.

        Args:
            platform: Platform name
            platform_data: Platform configuration data

        Raises:
            ConfigurationError: If required fields are missing
        """
        required_fields = self.PLATFORM_REQUIRED_FIELDS.get(platform, [])

        for field in required_fields:
            if field not in platform_data or not platform_data[field]:
                raise ConfigurationError(
                    f"{platform.title()} configuration missing required field: {field}"
                )

    def __str__(self) -> str:
        """String representation of ConfigLoader."""
        return f"ConfigLoader(config_file='{self.config_file_path}')"

    def __repr__(self) -> str:
        """Detailed string representation of ConfigLoader."""
        return f"ConfigLoader(config_file_path={self.config_file_path!r})"
