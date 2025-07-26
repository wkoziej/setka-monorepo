"""
Tests for Facebook API authentication functionality.

This module contains comprehensive tests for the FacebookAuth class,
covering token management, validation, and permission verification.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from datetime import datetime, timedelta
import json

from medusa.publishers.facebook_auth import FacebookAuth
from medusa.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    ValidationError,
)


class TestFacebookAuth:
    """Test suite for FacebookAuth class."""

    @pytest.fixture
    def valid_config(self):
        """Valid Facebook configuration for testing."""
        return {
            "page_id": "123456789",
            "access_token": "valid_token_12345",
            "app_id": "app_123",
            "app_secret": "secret_456",
        }

    @pytest.fixture
    def facebook_auth(self, valid_config):
        """FacebookAuth instance for testing."""
        return FacebookAuth(valid_config)

    @pytest.fixture
    def mock_requests_get(self):
        """Mock requests.get for API calls."""
        with patch("requests.get") as mock:
            yield mock

    @pytest.fixture
    def mock_requests_post(self):
        """Mock requests.post for API calls."""
        with patch("requests.post") as mock:
            yield mock

    def test_init_with_valid_config(self, valid_config):
        """Test FacebookAuth initialization with valid configuration."""
        auth = FacebookAuth(valid_config)

        assert auth.page_id == "123456789"
        assert auth.access_token == "valid_token_12345"
        assert auth.app_id == "app_123"
        assert auth.app_secret == "secret_456"
        assert auth.api_version == "v19.0"  # Default version

    def test_init_with_custom_api_version(self, valid_config):
        """Test FacebookAuth initialization with custom API version."""
        valid_config["api_version"] = "v18.0"
        auth = FacebookAuth(valid_config)

        assert auth.api_version == "v18.0"

    def test_init_missing_required_fields(self):
        """Test FacebookAuth initialization with missing required fields."""
        incomplete_configs = [
            {},  # Empty config
            {"page_id": "123"},  # Missing access_token
            {"access_token": "token"},  # Missing page_id
            {"page_id": "123", "access_token": "token"},  # Missing app_id
            {
                "page_id": "123",
                "access_token": "token",
                "app_id": "app",
            },  # Missing app_secret
        ]

        for config in incomplete_configs:
            with pytest.raises(ConfigurationError) as exc_info:
                FacebookAuth(config)
            assert "Missing required Facebook configuration" in str(exc_info.value)

    def test_init_invalid_field_types(self):
        """Test FacebookAuth initialization with invalid field types."""
        invalid_configs = [
            {
                "page_id": 123,
                "access_token": "token",
                "app_id": "app",
                "app_secret": "secret",
            },
            {
                "page_id": "123",
                "access_token": None,
                "app_id": "app",
                "app_secret": "secret",
            },
            {
                "page_id": "123",
                "access_token": "token",
                "app_id": [],
                "app_secret": "secret",
            },
        ]

        for config in invalid_configs:
            with pytest.raises(ValidationError) as exc_info:
                FacebookAuth(config)
            assert "Invalid configuration type" in str(exc_info.value)

    def test_validate_token_success(self, facebook_auth, mock_requests_get):
        """Test successful token validation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "app_id": "app_123",
                "type": "PAGE",
                "application": "Test App",
                "expires_at": 0,  # Never expires
                "is_valid": True,
                "scopes": ["pages_manage_posts", "pages_read_engagement"],
            }
        }
        mock_requests_get.return_value = mock_response

        result = facebook_auth.validate_token()

        assert result is True
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        assert "debug_token" in call_args[0][0]
        assert "input_token=valid_token_12345" in call_args[0][0]

    def test_validate_token_invalid_token(self, facebook_auth, mock_requests_get):
        """Test token validation with invalid token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "is_valid": False,
                "error": {
                    "message": "Invalid OAuth access token.",
                    "type": "OAuthException",
                },
            }
        }
        mock_requests_get.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            facebook_auth.validate_token()
        assert "Invalid access token" in str(exc_info.value)

    def test_validate_token_expired_token(self, facebook_auth, mock_requests_get):
        """Test token validation with expired token."""
        past_timestamp = int((datetime.now() - timedelta(days=1)).timestamp())

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"is_valid": True, "expires_at": past_timestamp}
        }
        mock_requests_get.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            facebook_auth.validate_token()
        assert "Token has expired" in str(exc_info.value)

    def test_validate_token_network_error(self, facebook_auth, mock_requests_get):
        """Test token validation with network error."""
        mock_requests_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(NetworkError) as exc_info:
            facebook_auth.validate_token()
        assert "Network error during API request" in str(exc_info.value)

    def test_validate_token_api_error_response(self, facebook_auth, mock_requests_get):
        """Test token validation with API error response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Invalid request", "type": "GraphMethodException"}
        }
        mock_requests_get.return_value = mock_response

        with pytest.raises(NetworkError) as exc_info:
            facebook_auth.validate_token()
        assert "API error during GET /debug_token" in str(exc_info.value)

    def test_check_permissions_success(self, facebook_auth, mock_requests_get):
        """Test successful permission verification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"permission": "pages_manage_posts", "status": "granted"},
                {"permission": "pages_read_engagement", "status": "granted"},
                {"permission": "publish_pages", "status": "granted"},
            ]
        }
        mock_requests_get.return_value = mock_response

        result = facebook_auth.check_permissions()

        assert result is True
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        assert "/123456789/permissions" in call_args[0][0]

    def test_check_permissions_missing_required(self, facebook_auth, mock_requests_get):
        """Test permission verification with missing required permissions."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"permission": "pages_read_engagement", "status": "granted"}
                # Missing pages_manage_posts
            ]
        }
        mock_requests_get.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            facebook_auth.check_permissions()
        assert "Missing required permissions" in str(exc_info.value)
        assert "pages_manage_posts" in str(exc_info.value)

    def test_check_permissions_declined(self, facebook_auth, mock_requests_get):
        """Test permission verification with declined permissions."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"permission": "pages_manage_posts", "status": "declined"},
                {"permission": "pages_read_engagement", "status": "granted"},
            ]
        }
        mock_requests_get.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            facebook_auth.check_permissions()
        assert "Required permissions declined" in str(exc_info.value)

    def test_check_permissions_custom_required(self, facebook_auth, mock_requests_get):
        """Test permission verification with custom required permissions."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"permission": "custom_permission", "status": "granted"}]
        }
        mock_requests_get.return_value = mock_response

        result = facebook_auth.check_permissions(
            required_permissions=["custom_permission"]
        )
        assert result is True

    def test_verify_page_access_success(self, facebook_auth, mock_requests_get):
        """Test successful page access verification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456789",
            "name": "Test Page",
            "access_token": "page_token_xyz",
        }
        mock_requests_get.return_value = mock_response

        result = facebook_auth.verify_page_access()

        assert result is True
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        assert "/123456789" in call_args[0][0]

    def test_verify_page_access_not_found(self, facebook_auth, mock_requests_get):
        """Test page access verification with page not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": {"message": "Page not found", "type": "GraphMethodException"}
        }
        mock_requests_get.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            facebook_auth.verify_page_access()
        assert "Page not found or access denied" in str(exc_info.value)

    def test_verify_page_access_no_permission(self, facebook_auth, mock_requests_get):
        """Test page access verification without permission."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "error": {"message": "Insufficient permissions", "type": "OAuthException"}
        }
        mock_requests_get.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            facebook_auth.verify_page_access()
        assert "Insufficient permissions" in str(exc_info.value)

    def test_get_page_info_success(self, facebook_auth, mock_requests_get):
        """Test successful page information retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456789",
            "name": "Test Page",
            "category": "Business",
            "access_token": "page_token_xyz",
            "fan_count": 1000,
        }
        mock_requests_get.return_value = mock_response

        result = facebook_auth.get_page_info()

        assert result["id"] == "123456789"
        assert result["name"] == "Test Page"
        assert result["category"] == "Business"
        assert "access_token" in result

    def test_get_page_info_with_fields(self, facebook_auth, mock_requests_get):
        """Test page information retrieval with specific fields."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123456789", "name": "Test Page"}
        mock_requests_get.return_value = mock_response

        result = facebook_auth.get_page_info(fields=["id", "name"])

        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        assert "fields=id%2Cname" in call_args[0][0]

    def test_test_connection_success(self, facebook_auth, mock_requests_get):
        """Test successful connection test."""
        # Mock successful responses for all checks
        responses = [
            # Token validation
            Mock(
                status_code=200,
                json=lambda: {"data": {"is_valid": True, "expires_at": 0}},
            ),
            # Permission check
            Mock(
                status_code=200,
                json=lambda: {
                    "data": [{"permission": "pages_manage_posts", "status": "granted"}]
                },
            ),
            # Page access
            Mock(
                status_code=200, json=lambda: {"id": "123456789", "name": "Test Page"}
            ),
        ]
        mock_requests_get.side_effect = responses

        result = facebook_auth.test_connection()

        assert result is True
        assert mock_requests_get.call_count == 3

    def test_test_connection_failure(self, facebook_auth, mock_requests_get):
        """Test connection test with failure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"is_valid": False}}
        mock_requests_get.return_value = mock_response

        with pytest.raises(AuthenticationError):
            facebook_auth.test_connection()

    def test_get_long_lived_token_success(self, facebook_auth, mock_requests_get):
        """Test successful long-lived token exchange."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "long_lived_token_xyz",
            "token_type": "bearer",
            "expires_in": 5183944,  # ~60 days
        }
        mock_requests_get.return_value = mock_response

        result = facebook_auth.get_long_lived_token()

        assert result == "long_lived_token_xyz"
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args
        assert "oauth/access_token" in call_args[0][0]
        assert "grant_type=fb_exchange_token" in call_args[0][0]

    def test_get_long_lived_token_error(self, facebook_auth, mock_requests_get):
        """Test long-lived token exchange with error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Invalid client_id", "type": "OAuthException"}
        }
        mock_requests_get.return_value = mock_response

        with pytest.raises(NetworkError) as exc_info:
            facebook_auth.get_long_lived_token()
        assert "API error during GET /oauth/access_token" in str(exc_info.value)

    def test_api_url_construction(self, facebook_auth):
        """Test API URL construction."""
        url = facebook_auth._build_api_url("/me")
        assert (
            url == "https://graph.facebook.com/v19.0/me?access_token=valid_token_12345"
        )

        url = facebook_auth._build_api_url("/me", {"fields": "id,name"})
        assert "fields=id%2Cname" in url

    def test_error_handling_json_decode_error(self, facebook_auth, mock_requests_get):
        """Test error handling when API returns invalid JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid response"
        mock_requests_get.return_value = mock_response

        with pytest.raises(NetworkError) as exc_info:
            facebook_auth.validate_token()
        assert "Invalid JSON response" in str(exc_info.value)

    def test_rate_limit_handling(self, facebook_auth, mock_requests_get):
        """Test handling of rate limit responses."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {
                "message": "Rate limit exceeded",
                "type": "OAuthException",
                "code": 4,
            }
        }
        mock_requests_get.return_value = mock_response

        with pytest.raises(NetworkError) as exc_info:
            facebook_auth.validate_token()
        assert "Rate limit exceeded" in str(exc_info.value)

    def test_repr_method(self, facebook_auth):
        """Test string representation of FacebookAuth."""
        repr_str = repr(facebook_auth)
        assert "FacebookAuth" in repr_str
        assert "page_id=123456789" in repr_str
        # Should not expose sensitive information
        assert "access_token" not in repr_str
        assert "app_secret" not in repr_str
