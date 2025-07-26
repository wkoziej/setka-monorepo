"""
Test suite for the Medusa configuration system.

This module tests the ConfigLoader class and related configuration functionality,
ensuring robust handling of JSON configuration files, validation, and environment
variable overrides.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from medusa.utils.config import ConfigLoader, PlatformConfig, MedusaConfig
from medusa.exceptions import ConfigurationError


class TestPlatformConfig:
    """Test the PlatformConfig dataclass."""
    
    def test_platform_config_creation(self):
        """Test basic platform configuration creation."""
        config = PlatformConfig(
            client_secrets_file="secrets.json",
            credentials_file="creds.json"
        )
        assert config.client_secrets_file == "secrets.json"
        assert config.credentials_file == "creds.json"
        assert config.access_token is None
        assert config.api_key is None
    
    def test_platform_config_with_all_fields(self):
        """Test platform configuration with all optional fields."""
        config = PlatformConfig(
            client_secrets_file="secrets.json",
            credentials_file="creds.json",
            access_token="token123",
            api_key="key456",
            api_secret="secret789",
            page_id="page123"
        )
        assert config.access_token == "token123"
        assert config.api_key == "key456"
        assert config.api_secret == "secret789"
        assert config.page_id == "page123"
    
    def test_platform_config_validation_missing_required(self):
        """Test platform config creation with no required fields (all optional)."""
        # PlatformConfig has no required fields, all are optional
        config = PlatformConfig()
        assert config.client_secrets_file is None
        assert config.access_token is None
    
    def test_platform_config_from_dict(self):
        """Test creating platform config from dictionary."""
        data = {
            "client_secrets_file": "secrets.json",
            "credentials_file": "creds.json",
            "access_token": "token123"
        }
        config = PlatformConfig.from_dict(data)
        assert config.client_secrets_file == "secrets.json"
        assert config.access_token == "token123"
    
    def test_platform_config_from_dict_with_extra_fields(self):
        """Test creating platform config from dict with extra fields that should be filtered."""
        data = {
            "client_secrets_file": "secrets.json",
            "credentials_file": "creds.json",
            "unknown_field": "should_be_ignored",
            "another_extra": "also_ignored"
        }
        config = PlatformConfig.from_dict(data)
        assert config.client_secrets_file == "secrets.json"
        assert config.credentials_file == "creds.json"
        # Extra fields should not cause errors and should be ignored
        assert not hasattr(config, 'unknown_field')
    
    def test_platform_config_post_init(self):
        """Test __post_init__ method is called during creation."""
        # This test ensures __post_init__ is covered
        config = PlatformConfig(access_token="test_token")
        assert config.access_token == "test_token"


class TestMedusaConfig:
    """Test the MedusaConfig dataclass."""
    
    def test_medusa_config_creation(self):
        """Test basic Medusa configuration creation."""
        youtube_config = PlatformConfig(
            client_secrets_file="youtube_secrets.json",
            credentials_file="youtube_creds.json"
        )
        facebook_config = PlatformConfig(
            access_token="fb_token",
            page_id="fb_page_123"
        )
        
        config = MedusaConfig(
            youtube=youtube_config,
            facebook=facebook_config
        )
        
        assert config.youtube == youtube_config
        assert config.facebook == facebook_config
        assert config.vimeo is None
        assert config.twitter is None
    
    def test_medusa_config_with_all_platforms(self):
        """Test Medusa configuration with all supported platforms."""
        platforms = {
            "youtube": PlatformConfig(
                client_secrets_file="youtube_secrets.json",
                credentials_file="youtube_creds.json"
            ),
            "facebook": PlatformConfig(
                access_token="fb_token",
                page_id="fb_page_123"
            ),
            "vimeo": PlatformConfig(
                access_token="vimeo_token"
            ),
            "twitter": PlatformConfig(
                api_key="twitter_key",
                api_secret="twitter_secret",
                access_token="twitter_token"
            )
        }
        
        config = MedusaConfig(**platforms)
        assert config.youtube is not None
        assert config.facebook is not None
        assert config.vimeo is not None
        assert config.twitter is not None
    
    def test_get_platform_config(self):
        """Test getting platform configuration by name."""
        youtube_config = PlatformConfig(client_secrets_file="secrets.json")
        config = MedusaConfig(youtube=youtube_config)
        
        # Test existing platform
        assert config.get_platform_config("youtube") == youtube_config
        assert config.get_platform_config("YOUTUBE") == youtube_config  # Case insensitive
        
        # Test non-existing platform
        assert config.get_platform_config("facebook") is None
        assert config.get_platform_config("nonexistent") is None
    
    def test_has_platform(self):
        """Test checking if platform is configured."""
        youtube_config = PlatformConfig(client_secrets_file="secrets.json")
        config = MedusaConfig(youtube=youtube_config)
        
        assert config.has_platform("youtube") is True
        assert config.has_platform("YOUTUBE") is True  # Case insensitive
        assert config.has_platform("facebook") is False
        assert config.has_platform("nonexistent") is False
    
    def test_get_configured_platforms(self):
        """Test getting list of configured platforms."""
        youtube_config = PlatformConfig(client_secrets_file="secrets.json")
        facebook_config = PlatformConfig(access_token="token")
        
        config = MedusaConfig(youtube=youtube_config, facebook=facebook_config)
        
        platforms = config.get_configured_platforms()
        assert "youtube" in platforms
        assert "facebook" in platforms
        assert "vimeo" not in platforms
        assert "twitter" not in platforms
        assert len(platforms) == 2


class TestConfigLoader:
    """Test the ConfigLoader class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        
        # Sample valid configuration
        self.valid_config = {
            "youtube": {
                "client_secrets_file": "secrets/youtube_client_secrets.json",
                "credentials_file": "secrets/youtube_credentials.json"
            },
            "facebook": {
                "page_id": "1234567890",
                "access_token": "fb_access_token_123"
            },
            "vimeo": {
                "access_token": "vimeo_token_456"
            },
            "twitter": {
                "api_key": "twitter_api_key",
                "api_secret": "twitter_api_secret",
                "access_token": "twitter_access_token",
                "access_token_secret": "twitter_access_secret"
            }
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.config_file.exists():
            self.config_file.unlink()
        os.rmdir(self.temp_dir)
    
    def write_config_file(self, config_data):
        """Helper to write configuration to test file."""
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f)
    
    def test_load_valid_config_file(self):
        """Test loading a valid configuration file."""
        self.write_config_file(self.valid_config)
        
        loader = ConfigLoader(str(self.config_file))
        config = loader.load()
        
        assert isinstance(config, MedusaConfig)
        assert config.youtube is not None
        assert config.facebook is not None
        assert config.vimeo is not None
        assert config.twitter is not None
        
        # Verify specific values
        assert config.youtube.client_secrets_file == "secrets/youtube_client_secrets.json"
        assert config.facebook.page_id == "1234567890"
        assert config.vimeo.access_token == "vimeo_token_456"
        assert config.twitter.api_key == "twitter_api_key"
    
    def test_load_nonexistent_file(self):
        """Test loading a non-existent configuration file."""
        loader = ConfigLoader("nonexistent_config.json")
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        assert "Configuration file not found" in str(exc_info.value)
        assert "nonexistent_config.json" in str(exc_info.value)
    
    def test_load_invalid_json(self):
        """Test loading a file with invalid JSON."""
        with open(self.config_file, 'w') as f:
            f.write("{ invalid json content }")
        
        loader = ConfigLoader(str(self.config_file))
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        assert "Invalid JSON in configuration file" in str(exc_info.value)
    
    def test_load_empty_config(self):
        """Test loading an empty configuration file."""
        self.write_config_file({})
        
        loader = ConfigLoader(str(self.config_file))
        config = loader.load()
        
        # Should create empty config with all platforms as None
        assert isinstance(config, MedusaConfig)
        assert config.youtube is None
        assert config.facebook is None
        assert config.vimeo is None
        assert config.twitter is None
    
    def test_load_partial_config(self):
        """Test loading configuration with only some platforms."""
        partial_config = {
            "youtube": {
                "client_secrets_file": "youtube_secrets.json",
                "credentials_file": "youtube_creds.json"
            },
            "facebook": {
                "access_token": "fb_token",
                "page_id": "fb_page"
            }
        }
        self.write_config_file(partial_config)
        
        loader = ConfigLoader(str(self.config_file))
        config = loader.load()
        
        assert config.youtube is not None
        assert config.facebook is not None
        assert config.vimeo is None
        assert config.twitter is None
    
    def test_validate_youtube_config_missing_required(self):
        """Test validation fails for YouTube config missing required fields."""
        invalid_config = {
            "youtube": {
                "client_secrets_file": "secrets.json"
                # Missing credentials_file
            }
        }
        self.write_config_file(invalid_config)
        
        loader = ConfigLoader(str(self.config_file))
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        assert "Youtube configuration missing required field" in str(exc_info.value)
        assert "credentials_file" in str(exc_info.value)
    
    def test_validate_facebook_config_missing_required(self):
        """Test validation fails for Facebook config missing required fields."""
        invalid_config = {
            "facebook": {
                "page_id": "123456"
                # Missing access_token
            }
        }
        self.write_config_file(invalid_config)
        
        loader = ConfigLoader(str(self.config_file))
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        assert "Facebook configuration missing required field" in str(exc_info.value)
        assert "access_token" in str(exc_info.value)
    
    def test_validate_vimeo_config_missing_required(self):
        """Test validation fails for Vimeo config missing required fields."""
        invalid_config = {
            "vimeo": {
                # Missing access_token
            }
        }
        self.write_config_file(invalid_config)
        
        loader = ConfigLoader(str(self.config_file))
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        assert "Vimeo configuration missing required field" in str(exc_info.value)
        assert "access_token" in str(exc_info.value)
    
    def test_validate_twitter_config_missing_required(self):
        """Test validation fails for Twitter config missing required fields."""
        invalid_config = {
            "twitter": {
                "api_key": "key",
                "api_secret": "secret"
                # Missing access_token and access_token_secret
            }
        }
        self.write_config_file(invalid_config)
        
        loader = ConfigLoader(str(self.config_file))
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        assert "Twitter configuration missing required field" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'MEDUSA_YOUTUBE_CLIENT_SECRETS': 'env_youtube_secrets.json',
        'MEDUSA_FACEBOOK_ACCESS_TOKEN': 'env_fb_token'
    })
    def test_environment_variable_overrides(self):
        """Test that environment variables override configuration values."""
        self.write_config_file(self.valid_config)
        
        loader = ConfigLoader(str(self.config_file))
        config = loader.load()
        
        # Environment variables should override file values
        assert config.youtube.client_secrets_file == 'env_youtube_secrets.json'
        assert config.facebook.access_token == 'env_fb_token'
        
        # Non-overridden values should remain from file
        assert config.youtube.credentials_file == "secrets/youtube_credentials.json"
        assert config.facebook.page_id == "1234567890"
    
    @patch.dict(os.environ, {
        'MEDUSA_YOUTUBE_ACCESS_TOKEN': 'env_youtube_token'
    })
    def test_environment_variable_adds_missing_field(self):
        """Test that environment variables can add missing optional fields."""
        config_without_youtube_token = {
            "youtube": {
                "client_secrets_file": "secrets.json",
                "credentials_file": "creds.json"
                # No access_token in file
            }
        }
        self.write_config_file(config_without_youtube_token)
        
        loader = ConfigLoader(str(self.config_file))
        config = loader.load()
        
        # Environment variable should add the missing field
        assert config.youtube.access_token == 'env_youtube_token'
    
    def test_config_file_permissions_error(self):
        """Test handling of file permission errors."""
        self.write_config_file(self.valid_config)
        
        # Mock file opening to raise PermissionError
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            loader = ConfigLoader(str(self.config_file))
            
            with pytest.raises(ConfigurationError) as exc_info:
                loader.load()
            
            assert "Permission denied" in str(exc_info.value)
    
    def test_config_validation_with_extra_fields(self):
        """Test that extra fields in configuration are ignored."""
        config_with_extra = {
            "youtube": {
                "client_secrets_file": "secrets.json",
                "credentials_file": "creds.json",
                "extra_field": "should_be_ignored"
            },
            "unknown_platform": {
                "some_field": "value"
            }
        }
        self.write_config_file(config_with_extra)
        
        loader = ConfigLoader(str(self.config_file))
        config = loader.load()
        
        # Should load successfully, ignoring extra fields
        assert config.youtube is not None
        assert config.youtube.client_secrets_file == "secrets.json"
    
    def test_reload_configuration(self):
        """Test reloading configuration after file changes."""
        # Write initial config
        initial_config = {
            "youtube": {
                "client_secrets_file": "initial_secrets.json",
                "credentials_file": "initial_creds.json"
            }
        }
        self.write_config_file(initial_config)
        
        loader = ConfigLoader(str(self.config_file))
        config1 = loader.load()
        
        assert config1.youtube.client_secrets_file == "initial_secrets.json"
        
        # Update config file
        updated_config = {
            "youtube": {
                "client_secrets_file": "updated_secrets.json",
                "credentials_file": "updated_creds.json"
            }
        }
        self.write_config_file(updated_config)
        
        # Reload should pick up changes
        config2 = loader.load()
        assert config2.youtube.client_secrets_file == "updated_secrets.json"
    
    def test_config_loader_string_representation(self):
        """Test string representation of ConfigLoader."""
        loader = ConfigLoader(str(self.config_file))
        str_repr = str(loader)
        
        assert "ConfigLoader" in str_repr
        assert str(self.config_file) in str_repr
    
    def test_config_loader_repr(self):
        """Test detailed string representation of ConfigLoader."""
        loader = ConfigLoader(str(self.config_file))
        repr_str = repr(loader)
        
        assert "ConfigLoader" in repr_str
        assert "config_file_path" in repr_str
        assert str(self.config_file) in repr_str
    
    def test_get_environment_variable_mapping(self):
        """Test the environment variable mapping functionality."""
        loader = ConfigLoader(str(self.config_file))
        
        # Test platform field mapping
        assert loader._get_env_var_name("youtube", "client_secrets_file") == "MEDUSA_YOUTUBE_CLIENT_SECRETS"
        assert loader._get_env_var_name("facebook", "access_token") == "MEDUSA_FACEBOOK_ACCESS_TOKEN"
        assert loader._get_env_var_name("vimeo", "access_token") == "MEDUSA_VIMEO_ACCESS_TOKEN"
        assert loader._get_env_var_name("twitter", "api_key") == "MEDUSA_TWITTER_API_KEY"
    
    def test_get_env_var_name_with_unknown_field(self):
        """Test environment variable name generation for unknown fields."""
        loader = ConfigLoader(str(self.config_file))
        
        # For unknown fields, it should use the field name as uppercase
        assert loader._get_env_var_name("youtube", "unknown_field") == "MEDUSA_YOUTUBE_UNKNOWN_FIELD"
    
    def test_validate_platform_config_unknown_platform(self):
        """Test validation for unknown platform (should have no required fields)."""
        loader = ConfigLoader(str(self.config_file))
        
        # Unknown platform should not have required fields, so validation should pass
        loader._validate_platform_config("unknown_platform", {"some_field": "value"})
        # If no exception is raised, the test passes
    
    def test_validate_platform_config_empty_field_value(self):
        """Test validation fails when required field has empty value."""
        invalid_config = {
            "youtube": {
                "client_secrets_file": "",  # Empty string should fail validation
                "credentials_file": "creds.json"
            }
        }
        self.write_config_file(invalid_config)
        
        loader = ConfigLoader(str(self.config_file))
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        assert "Youtube configuration missing required field" in str(exc_info.value)
        assert "client_secrets_file" in str(exc_info.value) 