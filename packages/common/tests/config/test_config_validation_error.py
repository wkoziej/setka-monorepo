# ABOUTME: Test file for ConfigValidationError exception class.
# ABOUTME: Validates proper exception handling and error messages.

"""Tests for ConfigValidationError exception class."""

import pytest
from setka_common.config import ConfigValidationError


class TestConfigValidationError:
    """Test ConfigValidationError exception functionality."""

    def test_basic_exception_creation(self):
        """Test creating ConfigValidationError with message."""
        msg = "Invalid configuration: missing required field"
        error = ConfigValidationError(msg)

        assert str(error) == msg
        assert isinstance(error, Exception)

    def test_exception_inheritance(self):
        """Test that ConfigValidationError inherits from Exception."""
        error = ConfigValidationError("test")

        assert isinstance(error, Exception)
        assert isinstance(error, ConfigValidationError)

    def test_exception_raising(self):
        """Test raising and catching ConfigValidationError."""
        with pytest.raises(ConfigValidationError) as exc_info:
            raise ConfigValidationError("Configuration invalid")

        assert str(exc_info.value) == "Configuration invalid"

    def test_exception_with_context(self):
        """Test ConfigValidationError with additional context."""
        field_name = "animation_type"
        invalid_value = "bounce"
        valid_values = ["scale", "shake", "rotation"]

        msg = f"Invalid {field_name}: '{invalid_value}'. Must be one of {valid_values}"

        with pytest.raises(ConfigValidationError) as exc_info:
            raise ConfigValidationError(msg)

        assert field_name in str(exc_info.value)
        assert invalid_value in str(exc_info.value)

    def test_exception_chaining(self):
        """Test ConfigValidationError with exception chaining."""
        original_error = ValueError("Original error")

        try:
            raise original_error
        except ValueError as e:
            with pytest.raises(ConfigValidationError) as exc_info:
                raise ConfigValidationError("Validation failed") from e

            assert exc_info.value.__cause__ is original_error
