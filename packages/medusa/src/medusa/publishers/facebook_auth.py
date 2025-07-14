"""
Facebook API authentication module.

This module provides authentication and authorization functionality
for Facebook Graph API, including token validation, permission
verification, and page access management.
"""

import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, quote

from medusa.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    ValidationError
)

logger = logging.getLogger(__name__)


class FacebookAuth:
    """
    Facebook Graph API authentication and authorization handler.
    
    This class manages Facebook page access tokens, validates permissions,
    and provides methods for testing API connectivity.
    """
    
    # Required permissions for posting to Facebook pages
    REQUIRED_PERMISSIONS = ["pages_manage_posts"]
    
    # Optional permissions that enhance functionality
    OPTIONAL_PERMISSIONS = ["pages_read_engagement", "publish_pages"]
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize FacebookAuth with configuration.
        
        Args:
            config: Dictionary containing Facebook API configuration
                   Required keys: page_id, access_token, app_id, app_secret
                   Optional keys: api_version
        
        Raises:
            ConfigurationError: If required configuration is missing
            ValidationError: If configuration values are invalid
        """
        self._validate_config(config)
        
        self.page_id = config["page_id"]
        self.access_token = config["access_token"]
        self.app_id = config["app_id"]
        self.app_secret = config["app_secret"]
        self.api_version = config.get("api_version", "v19.0")
        
        # Base URL for Facebook Graph API
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        logger.info(f"FacebookAuth initialized for page {self.page_id}")
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate Facebook configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ConfigurationError: If required fields are missing
            ValidationError: If field types are invalid
        """
        required_fields = ["page_id", "access_token", "app_id", "app_secret"]
        
        # Check for missing required fields
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ConfigurationError(
                f"Missing required Facebook configuration fields: {missing_fields}"
            )
        
        # Validate field types
        for field in required_fields:
            value = config[field]
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(
                    f"Invalid configuration type for '{field}': expected non-empty string, "
                    f"got {type(value).__name__}",
                    platform="facebook"
                )
        
        # Validate optional fields
        if "api_version" in config:
            api_version = config["api_version"]
            if not isinstance(api_version, str) or not api_version.startswith("v"):
                raise ValidationError(
                    f"Invalid API version format: {api_version}. "
                    "Expected format: 'vX.Y' (e.g., 'v19.0')",
                    platform="facebook"
                )
    
    def _build_api_url(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Build complete Facebook Graph API URL.
        
        Args:
            endpoint: API endpoint (e.g., "/me", "/debug_token")
            params: Optional query parameters
            
        Returns:
            Complete API URL with parameters
        """
        url = f"{self.base_url}{endpoint}"
        
        if params:
            # Add access token to parameters
            params = dict(params)
            if "access_token" not in params:
                params["access_token"] = self.access_token
            
            url += "?" + urlencode(params, quote_via=quote)
        else:
            url += f"?access_token={self.access_token}"
        
        return url
    
    def _make_api_request(self, method: str, endpoint: str, 
                         params: Optional[Dict[str, Any]] = None,
                         data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make authenticated request to Facebook Graph API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            API response as dictionary
            
        Raises:
            NetworkError: If API request fails
        """
        url = self._build_api_url(endpoint, params)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=30)
            else:
                raise NetworkError(
                    f"Unsupported HTTP method: {method}",
                    platform="facebook"
                )
            
            # Handle rate limiting
            if response.status_code == 429:
                error_data = response.json().get("error", {})
                raise NetworkError(
                    f"Rate limit exceeded: {error_data.get('message', 'Unknown error')}",
                    platform="facebook",
                    status_code=429
                )
            
            # Parse JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                raise NetworkError(
                    f"Invalid JSON response from Facebook API: {e}",
                    platform="facebook"
                )
            
            # Check for API errors
            if response.status_code >= 400:
                error_info = response_data.get("error", {})
                error_message = error_info.get("message", "Unknown API error")
                error_type = error_info.get("type", "Unknown")
                
                raise NetworkError(
                    f"API error during {method} {endpoint}: {error_message} ({error_type})",
                    platform="facebook",
                    status_code=response.status_code,
                    endpoint=endpoint
                )
            
            return response_data
            
        except requests.RequestException as e:
            raise NetworkError(
                f"Network error during API request: {e}",
                platform="facebook"
            )
    
    def validate_token(self) -> bool:
        """
        Validate the access token using Facebook's debug_token endpoint.
        
        Returns:
            True if token is valid and not expired
            
        Raises:
            AuthenticationError: If token is invalid or expired
            NetworkError: If validation request fails
        """
        logger.info("Validating Facebook access token")
        
        try:
            params = {
                "input_token": self.access_token,
                "access_token": f"{self.app_id}|{self.app_secret}"
            }
            
            response_data = self._make_api_request("GET", "/debug_token", params)
            token_data = response_data.get("data", {})
            
            # Check if token is valid
            if not token_data.get("is_valid", False):
                error_info = token_data.get("error", {})
                error_message = error_info.get("message", "Token validation failed")
                raise AuthenticationError(
                    f"Invalid access token: {error_message}",
                    platform="facebook"
                )
            
            # Check token expiration
            expires_at = token_data.get("expires_at", 0)
            if expires_at > 0:  # 0 means never expires
                expiry_time = datetime.fromtimestamp(expires_at)
                if expiry_time <= datetime.now():
                    raise AuthenticationError(
                        f"Token has expired at {expiry_time.isoformat()}",
                        platform="facebook"
                    )
            
            logger.info("Access token validation successful")
            return True
            
        except (NetworkError, AuthenticationError):
            raise
        except Exception as e:
            raise NetworkError(
                f"Failed to validate token: {e}",
                platform="facebook"
            )
    
    def check_permissions(self, required_permissions: Optional[List[str]] = None) -> bool:
        """
        Check if the access token has required permissions.
        
        Args:
            required_permissions: List of required permissions.
                                If None, uses default required permissions.
        
        Returns:
            True if all required permissions are granted
            
        Raises:
            AuthenticationError: If required permissions are missing or declined
            NetworkError: If permission check fails
        """
        if required_permissions is None:
            required_permissions = self.REQUIRED_PERMISSIONS
        
        logger.info(f"Checking Facebook permissions: {required_permissions}")
        
        try:
            response_data = self._make_api_request("GET", f"/{self.page_id}/permissions")
            permissions_data = response_data.get("data", [])
            
            # Build permission status map
            permissions = {
                perm["permission"]: perm["status"] 
                for perm in permissions_data
            }
            
            # Check for missing permissions
            missing_permissions = [
                perm for perm in required_permissions 
                if perm not in permissions
            ]
            if missing_permissions:
                raise AuthenticationError(
                    f"Missing required permissions: {missing_permissions}",
                    platform="facebook"
                )
            
            # Check for declined permissions
            declined_permissions = [
                perm for perm in required_permissions
                if permissions.get(perm) == "declined"
            ]
            if declined_permissions:
                raise AuthenticationError(
                    f"Required permissions declined: {declined_permissions}",
                    platform="facebook"
                )
            
            logger.info("Permission check successful")
            return True
            
        except (NetworkError, AuthenticationError):
            raise
        except Exception as e:
            raise NetworkError(
                f"Failed to check permissions: {e}",
                platform="facebook"
            )
    
    def verify_page_access(self) -> bool:
        """
        Verify access to the specified Facebook page.
        
        Returns:
            True if page access is confirmed
            
        Raises:
            AuthenticationError: If page access is denied or page not found
            NetworkError: If verification request fails
        """
        logger.info(f"Verifying access to Facebook page {self.page_id}")
        
        try:
            response_data = self._make_api_request("GET", f"/{self.page_id}")
            
            # If we get here without exception, access is confirmed
            page_name = response_data.get("name", "Unknown")
            logger.info(f"Page access verified for '{page_name}' ({self.page_id})")
            return True
            
        except NetworkError as e:
            if "404" in str(e) or "Page not found" in str(e):
                raise AuthenticationError(
                    f"Page not found or access denied: {self.page_id}",
                    platform="facebook"
                )
            elif "403" in str(e) or "Insufficient permissions" in str(e):
                raise AuthenticationError(
                    f"Insufficient permissions to access page: {self.page_id}",
                    platform="facebook"
                )
            else:
                raise
    
    def get_page_info(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get information about the Facebook page.
        
        Args:
            fields: List of fields to retrieve. If None, gets default fields.
        
        Returns:
            Dictionary containing page information
            
        Raises:
            NetworkError: If request fails
        """
        if fields is None:
            fields = ["id", "name", "category", "access_token", "fan_count"]
        
        params = {"fields": ",".join(fields)}
        
        logger.info(f"Retrieving page info for {self.page_id}")
        return self._make_api_request("GET", f"/{self.page_id}", params)
    
    def test_connection(self) -> bool:
        """
        Test Facebook API connection by performing validation checks.
        
        Returns:
            True if all connection tests pass
            
        Raises:
            AuthenticationError: If any validation fails
            NetworkError: If connection test fails
        """
        logger.info("Testing Facebook API connection")
        
        # Test 1: Validate access token
        self.validate_token()
        
        # Test 2: Check permissions
        self.check_permissions()
        
        # Test 3: Verify page access
        self.verify_page_access()
        
        logger.info("Facebook API connection test successful")
        return True
    
    def get_long_lived_token(self) -> str:
        """
        Exchange short-lived token for long-lived token.
        
        Returns:
            Long-lived access token
            
        Raises:
            AuthenticationError: If token exchange fails
            NetworkError: If request fails
        """
        logger.info("Exchanging for long-lived token")
        
        try:
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": self.access_token
            }
            
            response_data = self._make_api_request("GET", "/oauth/access_token", params)
            
            long_lived_token = response_data.get("access_token")
            if not long_lived_token:
                raise AuthenticationError(
                    "No access token in exchange response",
                    platform="facebook"
                )
            
            expires_in = response_data.get("expires_in", 0)
            logger.info(f"Long-lived token obtained (expires in {expires_in} seconds)")
            
            return long_lived_token
            
        except (NetworkError, AuthenticationError):
            raise
        except Exception as e:
            raise AuthenticationError(
                f"Failed to exchange token: {e}",
                platform="facebook"
            )
    
    def __repr__(self) -> str:
        """Return string representation of FacebookAuth instance."""
        return f"FacebookAuth(page_id={self.page_id}, api_version={self.api_version})" 