"""
Tests for YouTube OAuth authentication functionality.
Tests OAuth flow management, token refresh, and credential validation.
"""

import pytest
import json
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path

from medusa.uploaders.youtube_auth import YouTubeAuth
from medusa.exceptions import (
    AuthenticationError,
    ConfigError
)
from medusa.models import PlatformConfig


class TestYouTubeAuthInitialization:
    """Test YouTube auth initialization and configuration."""
    
    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "client_secrets_file": "client_secrets.json",
                "credentials_file": "credentials.json"
            }
        )
        
        auth = YouTubeAuth(config)
        
        assert auth.platform_name == "youtube"
        assert auth.config == config
        assert auth.client_secrets_file == "client_secrets.json"
        assert auth.credentials_file == "credentials.json"
        assert auth.credentials is None
        assert not auth.is_authenticated
    
    def test_init_without_config(self):
        """Test initialization without configuration."""
        auth = YouTubeAuth()
        
        assert auth.platform_name == "youtube"
        assert auth.config.platform_name == "youtube"
        assert auth.client_secrets_file is None
        assert auth.credentials_file is None
    
    def test_init_with_missing_credentials_config(self):
        """Test initialization with missing credentials configuration."""
        config = PlatformConfig(platform_name="youtube")
        
        auth = YouTubeAuth(config)
        
        assert auth.client_secrets_file is None
        assert auth.credentials_file is None
    
    def test_init_with_partial_credentials_config(self):
        """Test initialization with partial credentials configuration."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "client_secrets_file": "client_secrets.json"
                # Missing credentials_file
            }
        )
        
        auth = YouTubeAuth(config)
        
        assert auth.client_secrets_file == "client_secrets.json"
        assert auth.credentials_file is None


class TestYouTubeAuthFileValidation:
    """Test file validation for client secrets and credentials."""
    
    def test_validate_files_with_existing_files(self):
        """Test file validation with existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            client_secrets_path = Path(temp_dir) / "client_secrets.json"
            credentials_path = Path(temp_dir) / "credentials.json"
            
            client_secrets_path.write_text('{"installed": {"client_id": "test"}}')
            credentials_path.write_text('{"token": "test_token"}')
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "client_secrets_file": str(client_secrets_path),
                    "credentials_file": str(credentials_path)
                }
            )
            
            auth = YouTubeAuth(config)
            auth.validate_files()  # Should not raise
    
    def test_validate_files_with_missing_client_secrets(self):
        """Test file validation with missing client secrets file."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "client_secrets_file": "nonexistent.json",
                "credentials_file": "credentials.json"
            }
        )
        
        auth = YouTubeAuth(config)
        
        with pytest.raises(ConfigError) as exc_info:
            auth.validate_files()
        
        assert "Client secrets file not found" in str(exc_info.value)
        assert "nonexistent.json" in str(exc_info.value)
    
    def test_validate_files_with_missing_credentials_file(self):
        """Test file validation with missing credentials file - should not raise."""
        with tempfile.TemporaryDirectory() as temp_dir:
            client_secrets_path = Path(temp_dir) / "client_secrets.json"
            client_secrets_path.write_text('{"installed": {"client_id": "test"}}')
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "client_secrets_file": str(client_secrets_path),
                    "credentials_file": "nonexistent_credentials.json"
                }
            )
            
            auth = YouTubeAuth(config)
            auth.validate_files()  # Should not raise - credentials file is optional
    
    def test_validate_files_without_configuration(self):
        """Test file validation without file configuration."""
        auth = YouTubeAuth()
        
        with pytest.raises(ConfigError) as exc_info:
            auth.validate_files()
        
        assert "Client secrets file not configured" in str(exc_info.value)
    
    def test_validate_files_with_invalid_json(self):
        """Test file validation with invalid JSON in client secrets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            client_secrets_path = Path(temp_dir) / "client_secrets.json"
            client_secrets_path.write_text('invalid json')
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "client_secrets_file": str(client_secrets_path)
                }
            )
            
            auth = YouTubeAuth(config)
            
            with pytest.raises(ConfigError) as exc_info:
                auth.validate_files()
            
            assert "Invalid JSON in client secrets file" in str(exc_info.value)


class TestYouTubeAuthCredentialsLoading:
    """Test credentials loading and validation."""
    
    def test_load_existing_credentials(self):
        """Test loading existing valid credentials."""
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = Path(temp_dir) / "credentials.json"
            test_credentials = {
                "token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
                "expiry": "2024-12-31T23:59:59.000000Z"
            }
            credentials_path.write_text(json.dumps(test_credentials))
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "credentials_file": str(credentials_path)
                }
            )
            
            auth = YouTubeAuth(config)
            result = auth.load_existing_credentials()
            
            assert result is True
            assert auth.credentials is not None
            assert auth.credentials.token == "test_access_token"
    
    def test_load_nonexistent_credentials(self):
        """Test loading credentials from nonexistent file."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "credentials_file": "nonexistent.json"
            }
        )
        
        auth = YouTubeAuth(config)
        result = auth.load_existing_credentials()
        
        assert result is False
        assert auth.credentials is None
    
    def test_load_invalid_credentials_json(self):
        """Test loading credentials with invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = Path(temp_dir) / "credentials.json"
            credentials_path.write_text('invalid json')
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "credentials_file": str(credentials_path)
                }
            )
            
            auth = YouTubeAuth(config)
            
            with pytest.raises(ConfigError) as exc_info:
                auth.load_existing_credentials()
            
            assert "Invalid JSON in credentials file" in str(exc_info.value)
    
    def test_load_credentials_without_file_config(self):
        """Test loading credentials without file configuration."""
        auth = YouTubeAuth()
        result = auth.load_existing_credentials()
        
        assert result is False
        assert auth.credentials is None


class TestYouTubeAuthTokenValidation:
    """Test token validation and expiry checking."""
    
    @patch('medusa.uploaders.youtube_auth.build')
    def test_validate_credentials_valid_token(self, mock_build):
        """Test credentials validation with valid token."""
        # Mock the YouTube API service
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Mock successful API call
        mock_service.channels.return_value.list.return_value.execute.return_value = {
            'items': [{'id': 'test_channel_id'}]
        }
        
        # Create mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.expired = False
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        
        result = auth.validate_credentials()
        
        assert result is True
        mock_build.assert_called_once_with('youtube', 'v3', credentials=mock_credentials)
    
    @patch('medusa.uploaders.youtube_auth.build')
    def test_validate_credentials_expired_token(self, mock_build):
        """Test credentials validation with expired token."""
        # Create mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = False
        mock_credentials.expired = True
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        
        result = auth.validate_credentials()
        
        assert result is False
        mock_build.assert_not_called()
    
    @patch('medusa.uploaders.youtube_auth.build')
    def test_validate_credentials_api_error(self, mock_build):
        """Test credentials validation with API error."""
        # Mock the YouTube API service to raise exception
        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_service.channels.return_value.list.return_value.execute.side_effect = Exception("API Error")
        
        # Create mock credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.expired = False
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        
        with pytest.raises(AuthenticationError) as exc_info:
            auth.validate_credentials()
        
        assert "Failed to validate YouTube credentials" in str(exc_info.value)
        assert "API Error" in str(exc_info.value)
    
    def test_validate_credentials_without_credentials(self):
        """Test credentials validation without loaded credentials."""
        auth = YouTubeAuth()
        
        result = auth.validate_credentials()
        
        assert result is False


class TestYouTubeAuthTokenRefresh:
    """Test token refresh functionality."""
    
    @patch('medusa.uploaders.youtube_auth.Request')
    def test_refresh_token_success(self, mock_request):
        """Test successful token refresh."""
        # Create mock credentials with refresh capability
        mock_credentials = Mock()
        mock_credentials.expired = True
        mock_credentials.refresh_token = "test_refresh_token"
        mock_credentials.refresh = Mock()
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        
        result = auth.refresh_token()
        
        assert result is True
        mock_credentials.refresh.assert_called_once()
    
    @patch('medusa.uploaders.youtube_auth.Request')
    def test_refresh_token_failure(self, mock_request):
        """Test token refresh failure."""
        # Create mock credentials that fail to refresh
        mock_credentials = Mock()
        mock_credentials.expired = True
        mock_credentials.refresh_token = "test_refresh_token"
        mock_credentials.refresh = Mock(side_effect=Exception("Refresh failed"))
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        
        with pytest.raises(AuthenticationError) as exc_info:
            auth.refresh_token()
        
        assert "Failed to refresh YouTube token" in str(exc_info.value)
        assert "Refresh failed" in str(exc_info.value)
    
    def test_refresh_token_without_credentials(self):
        """Test token refresh without loaded credentials."""
        auth = YouTubeAuth()
        
        result = auth.refresh_token()
        
        assert result is False
    
    def test_refresh_token_without_refresh_token(self):
        """Test token refresh without refresh token."""
        mock_credentials = Mock()
        mock_credentials.expired = True
        mock_credentials.refresh_token = None
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        
        result = auth.refresh_token()
        
        assert result is False


class TestYouTubeAuthOAuthFlow:
    """Test OAuth flow initiation and completion."""
    
    @patch('medusa.uploaders.youtube_auth.InstalledAppFlow')
    def test_start_oauth_flow_success(self, mock_flow_class):
        """Test successful OAuth flow initiation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            client_secrets_path = Path(temp_dir) / "client_secrets.json"
            client_secrets_path.write_text('{"installed": {"client_id": "test"}}')
            
            # Mock the OAuth flow
            mock_flow = Mock()
            mock_flow_class.from_client_secrets_file.return_value = mock_flow
            
            mock_credentials = Mock()
            mock_flow.run_local_server.return_value = mock_credentials
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "client_secrets_file": str(client_secrets_path)
                }
            )
            
            auth = YouTubeAuth(config)
            result = auth.start_oauth_flow()
            
            assert result is True
            assert auth.credentials == mock_credentials
            mock_flow_class.from_client_secrets_file.assert_called_once()
            mock_flow.run_local_server.assert_called_once()
    
    @patch('medusa.uploaders.youtube_auth.InstalledAppFlow')
    def test_start_oauth_flow_failure(self, mock_flow_class):
        """Test OAuth flow failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            client_secrets_path = Path(temp_dir) / "client_secrets.json"
            client_secrets_path.write_text('{"installed": {"client_id": "test"}}')
            
            # Mock the OAuth flow to fail
            mock_flow = Mock()
            mock_flow_class.from_client_secrets_file.return_value = mock_flow
            mock_flow.run_local_server.side_effect = Exception("OAuth failed")
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "client_secrets_file": str(client_secrets_path)
                }
            )
            
            auth = YouTubeAuth(config)
            
            with pytest.raises(AuthenticationError) as exc_info:
                auth.start_oauth_flow()
            
            assert "OAuth flow failed" in str(exc_info.value)
            assert "OAuth failed" in str(exc_info.value)
    
    def test_start_oauth_flow_without_client_secrets(self):
        """Test OAuth flow without client secrets file."""
        auth = YouTubeAuth()
        
        with pytest.raises(ConfigError) as exc_info:
            auth.start_oauth_flow()
        
        assert "Client secrets file not configured" in str(exc_info.value)


class TestYouTubeAuthCredentialsSaving:
    """Test credentials saving functionality."""
    
    def test_save_credentials_success(self):
        """Test successful credentials saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = Path(temp_dir) / "credentials.json"
            
            # Mock credentials
            mock_credentials = Mock()
            mock_credentials.to_json.return_value = '{"token": "test_token"}'
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "credentials_file": str(credentials_path)
                }
            )
            
            auth = YouTubeAuth(config)
            auth.credentials = mock_credentials
            
            auth.save_credentials()
            
            # Verify file was created and contains expected content
            assert credentials_path.exists()
            saved_data = json.loads(credentials_path.read_text())
            assert saved_data["token"] == "test_token"
    
    def test_save_credentials_without_config(self):
        """Test saving credentials without file configuration."""
        mock_credentials = Mock()
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        
        with pytest.raises(ConfigError) as exc_info:
            auth.save_credentials()
        
        assert "Credentials file not configured" in str(exc_info.value)
    
    def test_save_credentials_without_credentials(self):
        """Test saving credentials without loaded credentials."""
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "credentials_file": "credentials.json"
            }
        )
        
        auth = YouTubeAuth(config)
        
        with pytest.raises(AuthenticationError) as exc_info:
            auth.save_credentials()
        
        assert "No credentials to save" in str(exc_info.value)
    
    def test_save_credentials_permission_error(self):
        """Test saving credentials with permission error."""
        # Mock credentials
        mock_credentials = Mock()
        mock_credentials.to_json.return_value = '{"token": "test_token"}'
        
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "credentials_file": "/root/credentials.json"  # Permission denied path
            }
        )
        
        auth = YouTubeAuth(config)
        auth.credentials = mock_credentials
        
        with pytest.raises(ConfigError) as exc_info:
            auth.save_credentials()
        
        assert "Failed to save credentials" in str(exc_info.value)


class TestYouTubeAuthMainFlow:
    """Test main authentication flow."""
    
    @pytest.mark.asyncio
    @patch.object(YouTubeAuth, 'load_existing_credentials')
    @patch.object(YouTubeAuth, 'validate_credentials')
    @patch.object(YouTubeAuth, 'refresh_token')
    async def test_authenticate_with_valid_existing_credentials(
        self, mock_refresh, mock_validate, mock_load
    ):
        """Test authentication with valid existing credentials."""
        # Setup mocks
        mock_load.return_value = True
        mock_validate.return_value = True
        mock_refresh.return_value = True
        
        auth = YouTubeAuth()
        result = await auth.authenticate()
        
        assert result is True
        assert auth.is_authenticated is True
        mock_load.assert_called_once()
        mock_validate.assert_called_once()
        mock_refresh.assert_not_called()
    
    @pytest.mark.asyncio
    @patch.object(YouTubeAuth, 'load_existing_credentials')
    @patch.object(YouTubeAuth, 'validate_credentials')
    @patch.object(YouTubeAuth, 'refresh_token')
    @patch.object(YouTubeAuth, 'save_credentials')
    async def test_authenticate_with_expired_credentials_refresh_success(
        self, mock_save, mock_refresh, mock_validate, mock_load
    ):
        """Test authentication with expired credentials that refresh successfully."""
        # Setup mocks
        mock_load.return_value = True
        mock_validate.side_effect = [False, True]  # First invalid, then valid after refresh
        mock_refresh.return_value = True
        
        auth = YouTubeAuth()
        result = await auth.authenticate()
        
        assert result is True
        assert auth.is_authenticated is True
        mock_load.assert_called_once()
        assert mock_validate.call_count == 2
        mock_refresh.assert_called_once()
        mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(YouTubeAuth, 'load_existing_credentials')
    @patch.object(YouTubeAuth, 'validate_credentials')
    @patch.object(YouTubeAuth, 'refresh_token')
    @patch.object(YouTubeAuth, 'start_oauth_flow')
    @patch.object(YouTubeAuth, 'save_credentials')
    async def test_authenticate_with_expired_credentials_refresh_failure(
        self, mock_save, mock_oauth, mock_refresh, mock_validate, mock_load
    ):
        """Test authentication with expired credentials that fail to refresh."""
        # Setup mocks
        mock_load.return_value = True
        mock_validate.side_effect = [False, True]  # Invalid, then valid after OAuth
        mock_refresh.return_value = False
        mock_oauth.return_value = True
        
        auth = YouTubeAuth()
        result = await auth.authenticate()
        
        assert result is True
        assert auth.is_authenticated is True
        mock_load.assert_called_once()
        assert mock_validate.call_count == 2
        mock_refresh.assert_called_once()
        mock_oauth.assert_called_once()
        mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(YouTubeAuth, 'load_existing_credentials')
    @patch.object(YouTubeAuth, 'start_oauth_flow')
    @patch.object(YouTubeAuth, 'validate_credentials')
    @patch.object(YouTubeAuth, 'save_credentials')
    async def test_authenticate_without_existing_credentials(
        self, mock_save, mock_validate, mock_oauth, mock_load
    ):
        """Test authentication without existing credentials."""
        # Setup mocks
        mock_load.return_value = False
        mock_oauth.return_value = True
        mock_validate.return_value = True
        
        auth = YouTubeAuth()
        result = await auth.authenticate()
        
        assert result is True
        assert auth.is_authenticated is True
        mock_load.assert_called_once()
        mock_oauth.assert_called_once()
        mock_validate.assert_called_once()
        mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.object(YouTubeAuth, 'load_existing_credentials')
    @patch.object(YouTubeAuth, 'start_oauth_flow')
    async def test_authenticate_oauth_failure(self, mock_oauth, mock_load):
        """Test authentication with OAuth flow failure."""
        # Setup mocks
        mock_load.return_value = False
        mock_oauth.side_effect = AuthenticationError("OAuth failed", platform="youtube")
        
        auth = YouTubeAuth()
        
        with pytest.raises(AuthenticationError) as exc_info:
            await auth.authenticate()
        
        assert "OAuth failed" in str(exc_info.value)
        assert auth.is_authenticated is False


class TestYouTubeAuthUtilityMethods:
    """Test utility methods and edge cases."""
    
    def test_get_required_scopes(self):
        """Test getting required OAuth scopes."""
        auth = YouTubeAuth()
        scopes = auth.get_required_scopes()
        
        assert isinstance(scopes, list)
        assert len(scopes) > 0
        assert "https://www.googleapis.com/auth/youtube.upload" in scopes
    
    def test_is_token_expired_with_expired_credentials(self):
        """Test token expiry check with expired credentials."""
        mock_credentials = Mock()
        mock_credentials.expired = True
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        
        assert auth.is_token_expired() is True
    
    def test_is_token_expired_with_valid_credentials(self):
        """Test token expiry check with valid credentials."""
        mock_credentials = Mock()
        mock_credentials.expired = False
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        
        assert auth.is_token_expired() is False
    
    def test_is_token_expired_without_credentials(self):
        """Test token expiry check without credentials."""
        auth = YouTubeAuth()
        
        assert auth.is_token_expired() is True
    
    def test_get_auth_status(self):
        """Test getting authentication status information."""
        mock_credentials = Mock()
        mock_credentials.token = "test_token"
        mock_credentials.expired = False
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        auth.is_authenticated = True
        
        status = auth.get_auth_status()
        
        assert isinstance(status, dict)
        assert status["authenticated"] is True
        assert status["has_credentials"] is True
        assert status["token_expired"] is False
    
    def test_get_auth_status_unauthenticated(self):
        """Test getting authentication status when unauthenticated."""
        auth = YouTubeAuth()
        
        status = auth.get_auth_status()
        
        assert isinstance(status, dict)
        assert status["authenticated"] is False
        assert status["has_credentials"] is False
        assert status["token_expired"] is True
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup method."""
        mock_credentials = Mock()
        
        auth = YouTubeAuth()
        auth.credentials = mock_credentials
        auth.is_authenticated = True
        
        await auth.cleanup()
        
        # Cleanup should not reset authentication state
        assert auth.is_authenticated is True
        assert auth.credentials is not None


class TestYouTubeAuthErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    def test_authentication_error_with_context(self):
        """Test authentication error includes proper context."""
        auth = YouTubeAuth()
        
        try:
            raise AuthenticationError(
                "Test error",
                platform="youtube",
                auth_type="oauth",
                token_expired=True
            )
        except AuthenticationError as e:
            assert e.platform == "youtube"
            assert e.context.get("auth_type") == "oauth"
            assert e.context.get("token_expired") is True
    
    @patch('medusa.uploaders.youtube_auth.Path.exists')
    def test_file_validation_with_io_error(self, mock_exists):
        """Test file validation with I/O error."""
        mock_exists.side_effect = OSError("Permission denied")
        
        config = PlatformConfig(
            platform_name="youtube",
            credentials={
                "client_secrets_file": "test.json"
            }
        )
        
        auth = YouTubeAuth(config)
        
        with pytest.raises(ConfigError) as exc_info:
            auth.validate_files()
        
        assert "Error checking file existence" in str(exc_info.value)
    
    def test_multiple_authentication_attempts(self):
        """Test multiple authentication attempts behavior."""
        auth = YouTubeAuth()
        
        # First attempt should set up state
        assert auth.is_authenticated is False
        
        # Multiple calls should be idempotent
        auth.is_authenticated = True
        assert auth.is_authenticated is True


# Integration test scenarios
class TestYouTubeAuthIntegration:
    """Integration tests for complete authentication workflows."""
    
    def test_full_oauth_workflow_simulation(self):
        """Test complete OAuth workflow with mocked components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            client_secrets_path = Path(temp_dir) / "client_secrets.json"
            credentials_path = Path(temp_dir) / "credentials.json"
            
            # Create client secrets file
            client_secrets_data = {
                "installed": {
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
            client_secrets_path.write_text(json.dumps(client_secrets_data))
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "client_secrets_file": str(client_secrets_path),
                    "credentials_file": str(credentials_path)
                }
            )
            
            auth = YouTubeAuth(config)
            
            # Validate configuration
            auth.validate_files()
            
            # Check initial state
            assert not auth.load_existing_credentials()
            assert not auth.validate_credentials()
            assert auth.is_token_expired()
            
            # Verify file paths are set correctly
            assert auth.client_secrets_file == str(client_secrets_path)
            assert auth.credentials_file == str(credentials_path)
    
    def test_credentials_persistence_workflow(self):
        """Test credentials loading and saving workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_path = Path(temp_dir) / "credentials.json"
            
            # Create initial credentials
            test_credentials = {
                "token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
                "expiry": "2024-12-31T23:59:59.000000Z"
            }
            credentials_path.write_text(json.dumps(test_credentials))
            
            config = PlatformConfig(
                platform_name="youtube",
                credentials={
                    "credentials_file": str(credentials_path)
                }
            )
            
            # Load credentials
            auth = YouTubeAuth(config)
            assert auth.load_existing_credentials() is True
            assert auth.credentials is not None
            
            # Verify loaded credentials
            assert auth.credentials.token == "test_access_token"
            
            # Test status reporting
            status = auth.get_auth_status()
            assert status["has_credentials"] is True 