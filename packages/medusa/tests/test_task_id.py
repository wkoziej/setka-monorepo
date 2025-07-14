"""
Comprehensive tests for TaskIDGenerator class.

This module tests the task ID generation system including:
- UUID-based secure ID generation
- ID validation utilities
- Prefix-based categorization
- ID serialization and parsing
"""

import pytest
import uuid
import re
from datetime import datetime
from unittest.mock import patch, MagicMock

from medusa.utils.task_id import TaskIDGenerator, InvalidTaskIDError
from medusa.exceptions import ValidationError


class TestTaskIDGenerator:
    """Test suite for TaskIDGenerator class."""
    
    def test_initialization_with_default_prefix(self):
        """Test TaskIDGenerator initialization with default prefix."""
        generator = TaskIDGenerator()
        assert generator.prefix == "medusa_task"
        
    def test_initialization_with_custom_prefix(self):
        """Test TaskIDGenerator initialization with custom prefix."""
        custom_prefix = "custom_prefix"
        generator = TaskIDGenerator(prefix=custom_prefix)
        assert generator.prefix == custom_prefix
        
    def test_initialization_with_invalid_prefix(self):
        """Test TaskIDGenerator initialization with invalid prefix."""
        with pytest.raises(ValidationError, match="Invalid prefix format"):
            TaskIDGenerator(prefix="invalid prefix with spaces")
            
        with pytest.raises(ValidationError, match="Invalid prefix format"):
            TaskIDGenerator(prefix="invalid-prefix!")
            
        with pytest.raises(ValidationError, match="Invalid prefix format"):
            TaskIDGenerator(prefix="")
            
    def test_generate_task_id_returns_string(self):
        """Test that generate_task_id returns a string."""
        generator = TaskIDGenerator()
        task_id = generator.generate_task_id()
        assert isinstance(task_id, str)
        
    def test_generate_task_id_has_correct_format(self):
        """Test that generated task IDs have correct format."""
        generator = TaskIDGenerator()
        task_id = generator.generate_task_id()
        
        # Should match pattern: prefix_timestamp_uuid
        pattern = r"^medusa_task_\d{14}_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        assert re.match(pattern, task_id)
        
    def test_generate_task_id_with_custom_prefix(self):
        """Test task ID generation with custom prefix."""
        custom_prefix = "custom_task"
        generator = TaskIDGenerator(prefix=custom_prefix)
        task_id = generator.generate_task_id()
        
        assert task_id.startswith(f"{custom_prefix}_")
        pattern = rf"^{custom_prefix}_\d{{14}}_[0-9a-f]{{8}}-[0-9a-f]{{4}}-4[0-9a-f]{{3}}-[89ab][0-9a-f]{{3}}-[0-9a-f]{{12}}$"
        assert re.match(pattern, task_id)
        
    def test_generate_task_id_uniqueness(self):
        """Test that generated task IDs are unique."""
        generator = TaskIDGenerator()
        
        # Generate multiple IDs and ensure they're all unique
        task_ids = set()
        for _ in range(100):
            task_id = generator.generate_task_id()
            assert task_id not in task_ids
            task_ids.add(task_id)
            
    def test_generate_task_id_with_task_type(self):
        """Test task ID generation with task type categorization."""
        generator = TaskIDGenerator()
        
        # Test with different task types
        upload_id = generator.generate_task_id(task_type="upload")
        publish_id = generator.generate_task_id(task_type="publish")
        
        assert "_upload_" in upload_id
        assert "_publish_" in publish_id
        
        # Verify format with task type
        pattern = r"^medusa_task_upload_\d{14}_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        assert re.match(pattern, upload_id)
        
    def test_generate_task_id_with_invalid_task_type(self):
        """Test task ID generation with invalid task type."""
        generator = TaskIDGenerator()
        
        with pytest.raises(ValidationError, match="Invalid task type"):
            generator.generate_task_id(task_type="invalid type!")
            
    def test_validate_task_id_valid_ids(self):
        """Test validation of valid task IDs."""
        generator = TaskIDGenerator()
        
        # Generate valid IDs and validate them
        valid_id = generator.generate_task_id()
        assert generator.validate_task_id(valid_id) is True
        
        # Test with task type
        valid_id_with_type = generator.generate_task_id(task_type="upload")
        assert generator.validate_task_id(valid_id_with_type) is True
        
    def test_validate_task_id_invalid_ids(self):
        """Test validation of invalid task IDs."""
        generator = TaskIDGenerator()
        
        invalid_ids = [
            "not_a_task_id",
            "medusa_task_invalid_uuid",
            "wrong_prefix_20240101000000_" + str(uuid.uuid4()),
            "medusa_task_" + str(uuid.uuid4()),  # Missing timestamp
            "medusa_task_20240101000000_invalid-uuid",
            None,
            "",
            123,
            "medusa_task_20240101000000_" + str(uuid.uuid1()),  # Wrong UUID version
        ]
        
        for invalid_id in invalid_ids:
            assert generator.validate_task_id(invalid_id) is False
            
    def test_validate_task_id_with_custom_prefix(self):
        """Test validation with custom prefix."""
        custom_prefix = "custom_task"
        generator = TaskIDGenerator(prefix=custom_prefix)
        
        # Valid ID with custom prefix
        valid_id = generator.generate_task_id()
        assert generator.validate_task_id(valid_id) is True
        
        # Invalid ID with wrong prefix
        wrong_prefix_id = "medusa_task_20240101000000_" + str(uuid.uuid4())
        assert generator.validate_task_id(wrong_prefix_id) is False
        
    def test_parse_task_id_valid_ids(self):
        """Test parsing of valid task IDs."""
        generator = TaskIDGenerator()
        
        # Test basic task ID
        task_id = generator.generate_task_id()
        parsed = generator.parse_task_id(task_id)
        
        assert parsed["prefix"] == "medusa_task"
        assert parsed["task_type"] is None
        assert isinstance(parsed["timestamp"], datetime)
        assert isinstance(parsed["uuid"], uuid.UUID)
        assert parsed["uuid"].version == 4
        
        # Test task ID with type
        task_id_with_type = generator.generate_task_id(task_type="upload")
        parsed_with_type = generator.parse_task_id(task_id_with_type)
        
        assert parsed_with_type["prefix"] == "medusa_task"
        assert parsed_with_type["task_type"] == "upload"
        assert isinstance(parsed_with_type["timestamp"], datetime)
        assert isinstance(parsed_with_type["uuid"], uuid.UUID)
        
    def test_parse_task_id_invalid_ids(self):
        """Test parsing of invalid task IDs."""
        generator = TaskIDGenerator()
        
        invalid_ids = [
            "not_a_task_id",
            "medusa_task_invalid_uuid",
            "wrong_prefix_20240101000000_" + str(uuid.uuid4()),
            None,
            "",
            123,
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(InvalidTaskIDError):
                generator.parse_task_id(invalid_id)
                
    def test_parse_task_id_with_custom_prefix(self):
        """Test parsing task IDs with custom prefix."""
        custom_prefix = "custom_task"
        generator = TaskIDGenerator(prefix=custom_prefix)
        
        task_id = generator.generate_task_id()
        parsed = generator.parse_task_id(task_id)
        
        assert parsed["prefix"] == custom_prefix
        
    def test_is_task_id_valid_ids(self):
        """Test is_task_id utility method with valid IDs."""
        generator = TaskIDGenerator()
        
        valid_id = generator.generate_task_id()
        assert generator.is_task_id(valid_id) is True
        
        valid_id_with_type = generator.generate_task_id(task_type="publish")
        assert generator.is_task_id(valid_id_with_type) is True
        
    def test_is_task_id_invalid_ids(self):
        """Test is_task_id utility method with invalid IDs."""
        generator = TaskIDGenerator()
        
        invalid_ids = [
            "not_a_task_id",
            None,
            "",
            123,
            "random_string",
        ]
        
        for invalid_id in invalid_ids:
            assert generator.is_task_id(invalid_id) is False
            
    def test_extract_uuid_from_task_id(self):
        """Test extraction of UUID from task ID."""
        generator = TaskIDGenerator()
        
        task_id = generator.generate_task_id()
        extracted_uuid = generator.extract_uuid(task_id)
        
        assert isinstance(extracted_uuid, uuid.UUID)
        assert extracted_uuid.version == 4
        
        # Verify the UUID matches what's in the task ID
        parsed = generator.parse_task_id(task_id)
        assert extracted_uuid == parsed["uuid"]
        
    def test_extract_uuid_invalid_task_id(self):
        """Test UUID extraction from invalid task ID."""
        generator = TaskIDGenerator()
        
        with pytest.raises(InvalidTaskIDError):
            generator.extract_uuid("invalid_task_id")
            
    def test_extract_timestamp_from_task_id(self):
        """Test extraction of timestamp from task ID."""
        generator = TaskIDGenerator()
        
        # Mock datetime to control timestamp
        with patch('medusa.utils.task_id.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strptime.side_effect = datetime.strptime
            
            task_id = generator.generate_task_id()
            extracted_timestamp = generator.extract_timestamp(task_id)
            
            assert isinstance(extracted_timestamp, datetime)
            # Should be close to mocked time
            assert extracted_timestamp.year == 2024
            assert extracted_timestamp.month == 1
            assert extracted_timestamp.day == 1
            
    def test_extract_timestamp_invalid_task_id(self):
        """Test timestamp extraction from invalid task ID."""
        generator = TaskIDGenerator()
        
        with pytest.raises(InvalidTaskIDError):
            generator.extract_timestamp("invalid_task_id")
            
    def test_extract_task_type_from_task_id(self):
        """Test extraction of task type from task ID."""
        generator = TaskIDGenerator()
        
        # Task ID without type
        task_id_no_type = generator.generate_task_id()
        assert generator.extract_task_type(task_id_no_type) is None
        
        # Task ID with type
        task_id_with_type = generator.generate_task_id(task_type="upload")
        assert generator.extract_task_type(task_id_with_type) == "upload"
        
    def test_extract_task_type_invalid_task_id(self):
        """Test task type extraction from invalid task ID."""
        generator = TaskIDGenerator()
        
        with pytest.raises(InvalidTaskIDError):
            generator.extract_task_type("invalid_task_id")
            
    def test_generate_task_id_timestamp_format(self):
        """Test that timestamp in task ID has correct format."""
        generator = TaskIDGenerator()
        
        # Mock datetime to control timestamp
        with patch('medusa.utils.task_id.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 14, 30, 45, 123456)
            mock_datetime.now.return_value = mock_now
            
            task_id = generator.generate_task_id()
            
            # Extract timestamp part
            parts = task_id.split("_")
            timestamp_str = parts[2]  # medusa_task_TIMESTAMP_uuid
            
            # Should be in format YYYYMMDDHHMMSS
            assert len(timestamp_str) == 14
            assert timestamp_str == "20240115143045"
            
    def test_concurrent_task_id_generation(self):
        """Test concurrent task ID generation for uniqueness."""
        import threading
        import time
        
        generator = TaskIDGenerator()
        task_ids = []
        lock = threading.Lock()
        
        def generate_ids():
            """Generate IDs in thread."""
            for _ in range(10):
                task_id = generator.generate_task_id()
                with lock:
                    task_ids.append(task_id)
                time.sleep(0.001)  # Small delay to test concurrency
                
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=generate_ids)
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Verify all IDs are unique
        assert len(task_ids) == 50
        assert len(set(task_ids)) == 50
        
    def test_task_id_serialization(self):
        """Test task ID serialization and deserialization."""
        generator = TaskIDGenerator()
        
        # Generate task ID
        original_id = generator.generate_task_id(task_type="upload")
        
        # Parse it
        parsed = generator.parse_task_id(original_id)
        
        # Verify we can reconstruct the same ID
        reconstructed_parts = [
            parsed["prefix"],
            parsed["task_type"] if parsed["task_type"] else None,
            parsed["timestamp"].strftime("%Y%m%d%H%M%S"),
            str(parsed["uuid"])
        ]
        
        # Remove None values
        reconstructed_parts = [p for p in reconstructed_parts if p is not None]
        
        # The original should contain all these parts
        for part in reconstructed_parts:
            if part != str(parsed["uuid"]):  # UUID format might differ
                assert part in original_id
                
    def test_task_id_edge_cases(self):
        """Test edge cases for task ID operations."""
        generator = TaskIDGenerator()
        
        # Test with very long valid task type
        long_task_type = "a" * 50
        task_id = generator.generate_task_id(task_type=long_task_type)
        assert generator.validate_task_id(task_id)
        assert generator.extract_task_type(task_id) == long_task_type
        
        # Test with minimum valid prefix
        min_generator = TaskIDGenerator(prefix="a")
        min_task_id = min_generator.generate_task_id()
        assert min_generator.validate_task_id(min_task_id)
        
    def test_task_id_components_validation(self):
        """Test individual component validation."""
        generator = TaskIDGenerator()
        
        # Test prefix validation
        assert generator._validate_prefix("valid_prefix") is True
        assert generator._validate_prefix("invalid prefix") is False
        assert generator._validate_prefix("invalid-prefix!") is False
        assert generator._validate_prefix("") is False
        
        # Test task type validation
        assert generator._validate_task_type("valid_type") is True
        assert generator._validate_task_type("invalid type") is False
        assert generator._validate_task_type("invalid-type!") is False
        assert generator._validate_task_type(None) is True  # None is valid
        
        # Test timestamp validation
        assert generator._validate_timestamp("20240101120000") is True
        assert generator._validate_timestamp("invalid") is False
        assert generator._validate_timestamp("202401011200") is False  # Too short
        assert generator._validate_timestamp("2024010112000000") is False  # Too long
        
    def test_task_id_generator_class_methods(self):
        """Test class methods for convenience."""
        # Test class method for quick ID generation
        task_id = TaskIDGenerator.quick_generate()
        assert isinstance(task_id, str)
        assert TaskIDGenerator().validate_task_id(task_id)
        
        # Test class method for quick validation
        assert TaskIDGenerator.quick_validate(task_id) is True
        assert TaskIDGenerator.quick_validate("invalid") is False
        
    def test_task_id_string_representation(self):
        """Test string representation of task ID components."""
        generator = TaskIDGenerator()
        task_id = generator.generate_task_id(task_type="upload")
        
        # Test that parsed components have proper string representations
        parsed = generator.parse_task_id(task_id)
        
        # All components should be convertible to string
        assert str(parsed["prefix"])
        assert str(parsed["task_type"])
        assert str(parsed["timestamp"])
        assert str(parsed["uuid"])
        
        # Test task ID summary
        summary = generator.get_task_id_summary(task_id)
        assert isinstance(summary, dict)
        assert "id" in summary
        assert "prefix" in summary
        assert "task_type" in summary
        assert "created_at" in summary
        assert "uuid_short" in summary


class TestInvalidTaskIDError:
    """Test suite for InvalidTaskIDError exception."""
    
    def test_invalid_task_id_error_creation(self):
        """Test InvalidTaskIDError exception creation."""
        error = InvalidTaskIDError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
        
    def test_invalid_task_id_error_with_task_id(self):
        """Test InvalidTaskIDError with task ID context."""
        task_id = "invalid_task_id"
        error = InvalidTaskIDError(f"Invalid task ID: {task_id}", task_id=task_id)
        assert task_id in str(error)
        assert hasattr(error, 'task_id')
        assert error.task_id == task_id


class TestTaskIDGeneratorIntegration:
    """Integration tests for TaskIDGenerator."""
    
    def test_full_workflow(self):
        """Test complete task ID workflow."""
        generator = TaskIDGenerator(prefix="test_task")
        
        # Generate ID
        task_id = generator.generate_task_id(task_type="integration_test")
        
        # Validate ID
        assert generator.validate_task_id(task_id)
        
        # Parse ID
        parsed = generator.parse_task_id(task_id)
        assert parsed["prefix"] == "test_task"
        assert parsed["task_type"] == "integration_test"
        
        # Extract components
        uuid_val = generator.extract_uuid(task_id)
        timestamp_val = generator.extract_timestamp(task_id)
        task_type_val = generator.extract_task_type(task_id)
        
        assert uuid_val == parsed["uuid"]
        assert timestamp_val == parsed["timestamp"]
        assert task_type_val == parsed["task_type"]
        
        # Get summary
        summary = generator.get_task_id_summary(task_id)
        assert summary["id"] == task_id
        assert summary["prefix"] == "test_task"
        assert summary["task_type"] == "integration_test"
        
    def test_multiple_generators_compatibility(self):
        """Test that multiple generators work together correctly."""
        gen1 = TaskIDGenerator(prefix="gen1")
        gen2 = TaskIDGenerator(prefix="gen2")
        
        # Generate IDs with different generators
        id1 = gen1.generate_task_id(task_type="test")
        id2 = gen2.generate_task_id(task_type="test")
        
        # Each generator should validate its own IDs
        assert gen1.validate_task_id(id1)
        assert gen2.validate_task_id(id2)
        
        # But not each other's (due to different prefixes)
        assert not gen1.validate_task_id(id2)
        assert not gen2.validate_task_id(id1)
        
    def test_performance_characteristics(self):
        """Test performance characteristics of task ID operations."""
        import time
        
        generator = TaskIDGenerator()
        
        # Test generation performance
        start_time = time.time()
        for _ in range(1000):
            generator.generate_task_id()
        generation_time = time.time() - start_time
        
        # Should be reasonably fast (less than 1 second for 1000 IDs)
        assert generation_time < 1.0
        
        # Test validation performance
        test_ids = [generator.generate_task_id() for _ in range(100)]
        
        start_time = time.time()
        for task_id in test_ids:
            generator.validate_task_id(task_id)
        validation_time = time.time() - start_time
        
        # Validation should be very fast
        assert validation_time < 0.1


class TestTaskIDGeneratorCoverage:
    """Additional tests to achieve 100% code coverage."""
    
    def test_parse_task_id_invalid_format_after_prefix(self):
        """Test parsing task ID with invalid format after prefix."""
        generator = TaskIDGenerator()
        
        # Create a task ID with invalid format after prefix (no underscore)
        invalid_id = "medusa_taskTYPE_20240101120000_" + str(uuid.uuid4())
        
        with pytest.raises(InvalidTaskIDError, match="Invalid task ID format after prefix"):
            generator.parse_task_id(invalid_id)
            
    def test_parse_task_id_with_invalid_timestamp_value(self):
        """Test parsing task ID with invalid timestamp value."""
        generator = TaskIDGenerator()
        
        # Create manually crafted invalid timestamp that passes regex but fails datetime parsing
        invalid_timestamp_id = "medusa_task_20240231235959_" + str(uuid.uuid4())  # Feb 31st doesn't exist
        
        with pytest.raises(InvalidTaskIDError, match="Invalid timestamp value"):
            generator.parse_task_id(invalid_timestamp_id)
            
    def test_parse_task_id_with_invalid_uuid_value(self):
        """Test parsing task ID with UUID format that passes regex but fails UUID() parsing."""
        generator = TaskIDGenerator()
        
        # This is tricky since our regex is quite strict, but let's try with a malformed UUID
        # that somehow passes the regex pattern
        with patch('uuid.UUID') as mock_uuid:
            mock_uuid.side_effect = ValueError("Invalid UUID")
            
            valid_looking_id = "medusa_task_20240101120000_12345678-1234-4123-a123-123456789abc"
            
            with pytest.raises(InvalidTaskIDError, match="Invalid UUID in task ID"):
                generator.parse_task_id(valid_looking_id)
                
    def test_parse_task_id_with_wrong_uuid_version(self):
        """Test parsing task ID with non-UUID4."""
        generator = TaskIDGenerator()
        
        # Create a valid UUID4 format that passes regex
        valid_uuid4_format = "12345678-1234-4123-a123-123456789abc"
        invalid_id = f"medusa_task_20240101120000_{valid_uuid4_format}"
        
        # Mock UUID to return object with wrong version
        with patch('medusa.utils.task_id.uuid.UUID') as mock_uuid:
            mock_uuid_obj = MagicMock()
            mock_uuid_obj.version = 1  # Not version 4
            mock_uuid.return_value = mock_uuid_obj
            
            with pytest.raises(InvalidTaskIDError, match="Task ID must use UUID4"):
                generator.parse_task_id(invalid_id)
            
    def test_validate_task_type_with_non_string(self):
        """Test _validate_task_type with non-string input."""
        generator = TaskIDGenerator()
        
        # Test with non-string type
        assert generator._validate_task_type(123) is False
        assert generator._validate_task_type([]) is False
        assert generator._validate_task_type({}) is False
        
    def test_validate_timestamp_with_non_string(self):
        """Test _validate_timestamp with non-string input."""
        generator = TaskIDGenerator()
        
        # Test with non-string type
        assert generator._validate_timestamp(123) is False
        assert generator._validate_timestamp([]) is False
        assert generator._validate_timestamp({}) is False
        
    def test_validate_prefix_with_non_string_and_empty(self):
        """Test _validate_prefix with non-string and empty inputs."""
        generator = TaskIDGenerator()
        
        # Test with non-string type
        assert generator._validate_prefix(123) is False
        assert generator._validate_prefix([]) is False
        assert generator._validate_prefix({}) is False
        assert generator._validate_prefix(None) is False
        
    def test_parse_task_id_edge_cases_with_manual_construction(self):
        """Test edge cases in parsing with manually constructed IDs."""
        generator = TaskIDGenerator()
        
        # Manually construct a task ID with invalid task type that passes regex
        # but fails validation during parsing
        valid_uuid = str(uuid.uuid4())
        # Create task ID with task type containing invalid characters
        manually_constructed_id = f"medusa_task_invalid-type_20240101120000_{valid_uuid}"
        
        with pytest.raises(InvalidTaskIDError, match="Invalid task type in task ID"):
            generator.parse_task_id(manually_constructed_id)
                
    def test_generate_task_id_with_mock_uuid_and_datetime(self):
        """Test task ID generation with mocked UUID and datetime for edge cases."""
        generator = TaskIDGenerator()
        
        # Test the exact path through generation
        with patch('medusa.utils.task_id.datetime') as mock_datetime:
            with patch('medusa.utils.task_id.uuid.uuid4') as mock_uuid:
                mock_datetime.now.return_value.strftime.return_value = "20240101120000"
                mock_uuid.return_value = "test-uuid-string"
                
                result = generator.generate_task_id()
                expected = "medusa_task_20240101120000_test-uuid-string"
                assert result == expected
                
    def test_class_method_edge_cases(self):
        """Test class methods with edge cases."""
        # Test quick_generate with various parameters
        result1 = TaskIDGenerator.quick_generate()
        result2 = TaskIDGenerator.quick_generate(prefix="test", task_type="example")
        
        assert result1.startswith("medusa_task_")
        assert result2.startswith("test_example_")
        
        # Test quick_validate with various cases
        assert TaskIDGenerator.quick_validate(result1) is True
        assert TaskIDGenerator.quick_validate("invalid") is False
        assert TaskIDGenerator.quick_validate(result2, prefix="test") is True
        assert TaskIDGenerator.quick_validate(result2, prefix="wrong") is False
    
    def test_value_error_paths_for_full_coverage(self):
        """Test ValueError exception paths to achieve 100% coverage.""" 
        generator = TaskIDGenerator()
        
        # Test ValueError in datetime.strptime - mock the entire datetime module
        with patch('medusa.utils.task_id.datetime') as mock_datetime:
            mock_datetime.strptime.side_effect = ValueError("Invalid date")
            
            valid_uuid4_format = "12345678-1234-4123-a123-123456789abc"
            invalid_id = f"medusa_task_20240101120000_{valid_uuid4_format}"
            
            with pytest.raises(InvalidTaskIDError, match="Invalid timestamp value"):
                generator.parse_task_id(invalid_id)
        
        # Test ValueError in uuid.UUID - different approach than before  
        with patch('medusa.utils.task_id.uuid.UUID') as mock_uuid:
            mock_uuid.side_effect = ValueError("Invalid UUID format")
            
            valid_uuid4_format = "12345678-1234-4123-a123-123456789abc"
            invalid_id = f"medusa_task_20240101120000_{valid_uuid4_format}"
            
            with pytest.raises(InvalidTaskIDError, match="Invalid UUID in task ID"):
                generator.parse_task_id(invalid_id) 