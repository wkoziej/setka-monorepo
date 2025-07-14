"""
YouTube OAuth authentication management.
Handles OAuth flow, token refresh, and credential validation for YouTube API.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..models import PlatformConfig
from ..exceptions import (
    AuthenticationError,
    ConfigError,
    ValidationError,
    MedusaError
)


class YouTubeAuth:
    """
    YouTube OAuth authentication manager.
    
    Handles the complete OAuth flow for YouTube API access including:
    - Initial OAuth authorization
    - Token refresh
    - Credential validation
    - Credential persistence
    """
    
    # Required OAuth scopes for YouTube operations
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube'
    ]
    
    def __init__(self, config: Optional[PlatformConfig] = None):
        """
        Initialize YouTube authentication manager.
        
        Args:
            config: Platform configuration with credential file paths
        """
        self.platform_name = "youtube"
        self.config = config or PlatformConfig(platform_name=self.platform_name)
        self.logger = logging.getLogger(f"medusa.auth.{self.platform_name}")
        
        # Extract file paths from config
        credentials_dict = self.config.credentials or {}
        self.client_secrets_file = credentials_dict.get("client_secrets_file")
        self.credentials_file = credentials_dict.get("credentials_file")
        
        # Authentication state
        self.credentials: Optional[Credentials] = None
        self.is_authenticated = False
    
    def validate_files(self) -> None:
        """
        Validate that required configuration files exist and are valid.
        
        Raises:
            ConfigError: If files are missing or invalid
        """
        if not self.client_secrets_file:
            raise ConfigError(
                "Client secrets file not configured",
                missing_fields=["client_secrets_file"]
            )
        
        try:
            # Check if client secrets file exists
            client_secrets_path = Path(self.client_secrets_file)
            if not client_secrets_path.exists():
                raise ConfigError(
                    f"Client secrets file not found: {self.client_secrets_file}",
                    config_file=self.client_secrets_file
                )
            
            # Validate client secrets JSON
            try:
                with open(client_secrets_path, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                raise ConfigError(
                    f"Invalid JSON in client secrets file: {self.client_secrets_file}",
                    config_file=self.client_secrets_file,
                    original_error=e
                )
            
            # Credentials file is optional - it will be created during OAuth flow
            if self.credentials_file:
                credentials_path = Path(self.credentials_file)
                if credentials_path.exists():
                    # Validate credentials JSON if it exists
                    try:
                        with open(credentials_path, 'r') as f:
                            json.load(f)
                    except json.JSONDecodeError as e:
                        raise ConfigError(
                            f"Invalid JSON in credentials file: {self.credentials_file}",
                            config_file=self.credentials_file,
                            original_error=e
                        )
        
        except OSError as e:
            raise ConfigError(
                f"Error checking file existence: {e}",
                original_error=e
            )
    
    def load_existing_credentials(self) -> bool:
        """
        Load existing credentials from file if available.
        
        Returns:
            True if credentials were loaded successfully, False otherwise
            
        Raises:
            ConfigError: If credentials file is invalid
        """
        if not self.credentials_file:
            self.logger.debug("No credentials file configured")
            return False
        
        credentials_path = Path(self.credentials_file)
        if not credentials_path.exists():
            self.logger.debug(f"Credentials file not found: {self.credentials_file}")
            return False
        
        try:
            with open(credentials_path, 'r') as f:
                credentials_data = json.load(f)
            
            # Create credentials object from saved data
            self.credentials = Credentials.from_authorized_user_info(credentials_data, self.SCOPES)
            
            self.logger.info("Existing credentials loaded successfully")
            return True
            
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Invalid JSON in credentials file: {self.credentials_file}",
                config_file=self.credentials_file,
                original_error=e
            )
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            return False
    
    def validate_credentials(self) -> bool:
        """
        Validate current credentials by making a test API call.
        
        Returns:
            True if credentials are valid, False otherwise
            
        Raises:
            AuthenticationError: If validation fails due to API error
        """
        if not self.credentials:
            self.logger.debug("No credentials to validate")
            return False
        
        if not self.credentials.valid:
            self.logger.debug("Credentials are not valid")
            return False
        
        if self.credentials.expired:
            self.logger.debug("Credentials are expired")
            return False
        
        try:
            # Test credentials with a simple API call
            service = build('youtube', 'v3', credentials=self.credentials)
            request = service.channels().list(part='id', mine=True)
            response = request.execute()
            
            self.logger.info("Credentials validated successfully")
            return True
            
        except Exception as e:
            raise AuthenticationError(
                f"Failed to validate YouTube credentials: {e}",
                platform=self.platform_name,
                auth_type="oauth",
                original_error=e
            )
    
    def refresh_token(self) -> bool:
        """
        Refresh expired access token using refresh token.
        
        Returns:
            True if token was refreshed successfully, False otherwise
            
        Raises:
            AuthenticationError: If refresh fails
        """
        if not self.credentials:
            self.logger.debug("No credentials to refresh")
            return False
        
        if not self.credentials.refresh_token:
            self.logger.debug("No refresh token available")
            return False
        
        try:
            # Refresh the token
            request = Request()
            self.credentials.refresh(request)
            
            self.logger.info("Token refreshed successfully")
            return True
            
        except Exception as e:
            raise AuthenticationError(
                f"Failed to refresh YouTube token: {e}",
                platform=self.platform_name,
                auth_type="token_refresh",
                token_expired=True,
                original_error=e
            )
    
    def start_oauth_flow(self) -> bool:
        """
        Start OAuth flow to obtain new credentials.
        
        Returns:
            True if OAuth flow completed successfully, False otherwise
            
        Raises:
            ConfigError: If client secrets file is not configured
            AuthenticationError: If OAuth flow fails
        """
        if not self.client_secrets_file:
            raise ConfigError(
                "Client secrets file not configured for OAuth flow",
                missing_fields=["client_secrets_file"]
            )
        
        try:
            # Create OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_file,
                self.SCOPES
            )
            
            # Run OAuth flow
            self.credentials = flow.run_local_server(port=0)
            
            self.logger.info("OAuth flow completed successfully")
            return True
            
        except Exception as e:
            raise AuthenticationError(
                f"OAuth flow failed: {e}",
                platform=self.platform_name,
                auth_type="oauth",
                original_error=e
            )
    
    def save_credentials(self) -> None:
        """
        Save current credentials to file for future use.
        
        Raises:
            ConfigError: If credentials file is not configured or save fails
            AuthenticationError: If no credentials to save
        """
        if not self.credentials:
            raise AuthenticationError(
                "No credentials to save",
                platform=self.platform_name
            )
        
        if not self.credentials_file:
            raise ConfigError(
                "Credentials file not configured",
                missing_fields=["credentials_file"]
            )
        
        try:
            # Convert credentials to JSON
            credentials_data = self.credentials.to_json()
            
            # Save to file
            credentials_path = Path(self.credentials_file)
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(credentials_path, 'w') as f:
                f.write(credentials_data)
            
            self.logger.info(f"Credentials saved to {self.credentials_file}")
            
        except Exception as e:
            raise ConfigError(
                f"Failed to save credentials to {self.credentials_file}: {e}",
                config_file=self.credentials_file,
                original_error=e
            )
    
    async def authenticate(self) -> bool:
        """
        Main authentication method that handles the complete auth flow.
        
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
            ConfigError: If configuration is invalid
        """
        try:
            # Try to load existing credentials
            if self.load_existing_credentials():
                # Validate existing credentials
                if self.validate_credentials():
                    self.is_authenticated = True
                    self.logger.info("Authentication successful with existing credentials")
                    return True
                
                # Try to refresh expired credentials
                if self.refresh_token():
                    if self.validate_credentials():
                        self.save_credentials()
                        self.is_authenticated = True
                        self.logger.info("Authentication successful after token refresh")
                        return True
            
            # If existing credentials don't work, start OAuth flow
            if self.start_oauth_flow():
                if self.validate_credentials():
                    self.save_credentials()
                    self.is_authenticated = True
                    self.logger.info("Authentication successful with new OAuth flow")
                    return True
            
            # If we get here, authentication failed
            self.is_authenticated = False
            return False
            
        except Exception as e:
            self.is_authenticated = False
            if isinstance(e, (AuthenticationError, ConfigError)):
                raise
            else:
                raise AuthenticationError(
                    f"Authentication failed: {e}",
                    platform=self.platform_name,
                    original_error=e
                )
    
    def get_required_scopes(self) -> List[str]:
        """
        Get list of required OAuth scopes.
        
        Returns:
            List of OAuth scope URLs
        """
        return self.SCOPES.copy()
    
    def is_token_expired(self) -> bool:
        """
        Check if current token is expired.
        
        Returns:
            True if token is expired or missing, False otherwise
        """
        if not self.credentials:
            return True
        
        return self.credentials.expired
    
    def get_auth_status(self) -> Dict[str, Any]:
        """
        Get current authentication status information.
        
        Returns:
            Dictionary with authentication status details
        """
        return {
            "authenticated": self.is_authenticated,
            "has_credentials": self.credentials is not None,
            "token_expired": self.is_token_expired(),
            "platform": self.platform_name,
            "scopes": self.SCOPES
        }
    
    async def cleanup(self) -> None:
        """
        Clean up authentication resources.
        
        Note: This doesn't reset authentication state to allow reuse.
        """
        self.logger.debug("YouTube auth cleanup completed")
        # Don't reset authentication state - credentials can be reused 