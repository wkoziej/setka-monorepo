"""
Tests for platform registry system.
Comprehensive test coverage for platform discovery, registration, and validation.
"""

import pytest
from unittest.mock import Mock, patch

from medusa.utils.registry import (
    PlatformRegistry,
    PlatformInfo,
    PlatformCapability,
    RegistryError,
)
from medusa.uploaders.base import BaseUploader
from medusa.uploaders.mock import MockUploader
from medusa.publishers.mock import MockPublisher
from medusa.models import PlatformConfig
from medusa.exceptions import MedusaError, ValidationError


class TestPlatformInfo:
    """Test PlatformInfo dataclass."""

    def test_create_platform_info(self):
        """Test creating PlatformInfo with valid data."""
        info = PlatformInfo(
            name="youtube",
            display_name="YouTube",
            platform_type="uploader",
            implementation_class=MockUploader,
            capabilities=[
                PlatformCapability.VIDEO_UPLOAD,
                PlatformCapability.METADATA_SUPPORT,
            ],
            version="1.0.0",
            description="YouTube video uploader",
        )

        assert info.name == "youtube"
        assert info.display_name == "YouTube"
        assert info.platform_type == "uploader"
        assert info.implementation_class == MockUploader
        assert PlatformCapability.VIDEO_UPLOAD in info.capabilities
        assert info.version == "1.0.0"
        assert info.description == "YouTube video uploader"

    def test_platform_info_validation(self):
        """Test PlatformInfo validation."""
        # Test empty name
        with pytest.raises(ValidationError, match="Platform name cannot be empty"):
            PlatformInfo(
                name="",
                display_name="Test",
                platform_type="uploader",
                implementation_class=MockUploader,
                capabilities=[],
                version="1.0.0",
            )

        # Test invalid platform type
        with pytest.raises(ValidationError, match="Invalid platform type"):
            PlatformInfo(
                name="test",
                display_name="Test",
                platform_type="invalid",
                implementation_class=MockUploader,
                capabilities=[],
                version="1.0.0",
            )

        # Test None implementation class
        with pytest.raises(
            ValidationError, match="Implementation class cannot be None"
        ):
            PlatformInfo(
                name="test",
                display_name="Test",
                platform_type="uploader",
                implementation_class=None,
                capabilities=[],
                version="1.0.0",
            )

    def test_platform_info_to_dict(self):
        """Test PlatformInfo serialization."""
        info = PlatformInfo(
            name="facebook",
            display_name="Facebook",
            platform_type="publisher",
            implementation_class=MockPublisher,
            capabilities=[PlatformCapability.TEXT_PUBLISHING],
            version="2.0.0",
            description="Facebook publisher",
        )

        result = info.to_dict()

        assert result["name"] == "facebook"
        assert result["display_name"] == "Facebook"
        assert result["platform_type"] == "publisher"
        assert result["capabilities"] == ["TEXT_PUBLISHING"]
        assert result["version"] == "2.0.0"
        assert result["description"] == "Facebook publisher"
        assert "implementation_class" not in result  # Should not be serialized


class TestPlatformCapability:
    """Test PlatformCapability enum."""

    def test_capability_values(self):
        """Test that all expected capabilities exist."""
        expected_capabilities = [
            "VIDEO_UPLOAD",
            "AUDIO_UPLOAD",
            "IMAGE_UPLOAD",
            "TEXT_PUBLISHING",
            "LINK_PUBLISHING",
            "METADATA_SUPPORT",
            "PROGRESS_TRACKING",
            "SCHEDULING",
            "THUMBNAIL_UPLOAD",
            "BATCH_OPERATIONS",
        ]

        for capability in expected_capabilities:
            assert hasattr(PlatformCapability, capability)
            assert isinstance(
                getattr(PlatformCapability, capability), PlatformCapability
            )


class TestPlatformRegistry:
    """Test PlatformRegistry functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry instance for each test."""
        return PlatformRegistry()

    @pytest.fixture
    def sample_uploader_info(self):
        """Create sample uploader platform info."""
        return PlatformInfo(
            name="youtube",
            display_name="YouTube",
            platform_type="uploader",
            implementation_class=MockUploader,
            capabilities=[
                PlatformCapability.VIDEO_UPLOAD,
                PlatformCapability.METADATA_SUPPORT,
            ],
            version="1.0.0",
            description="YouTube video uploader",
        )

    @pytest.fixture
    def sample_publisher_info(self):
        """Create sample publisher platform info."""
        return PlatformInfo(
            name="facebook",
            display_name="Facebook",
            platform_type="publisher",
            implementation_class=MockPublisher,
            capabilities=[
                PlatformCapability.TEXT_PUBLISHING,
                PlatformCapability.LINK_PUBLISHING,
            ],
            version="1.0.0",
            description="Facebook publisher",
        )

    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert isinstance(registry._platforms, dict)
        assert len(registry._platforms) == 0
        assert registry._auto_discovery_enabled is True

    def test_register_platform_success(self, registry, sample_uploader_info):
        """Test successful platform registration."""
        registry.register_platform(sample_uploader_info)

        assert "youtube" in registry._platforms
        assert registry._platforms["youtube"] == sample_uploader_info

    def test_register_platform_duplicate(self, registry, sample_uploader_info):
        """Test registering duplicate platform."""
        registry.register_platform(sample_uploader_info)

        # Should raise error when registering duplicate without force
        with pytest.raises(
            RegistryError, match="Platform 'youtube' is already registered"
        ):
            registry.register_platform(sample_uploader_info)

        # Should succeed with force=True
        registry.register_platform(sample_uploader_info, force=True)
        assert "youtube" in registry._platforms

    def test_register_platform_validation_failure(self, registry):
        """Test registration with invalid platform info."""
        # ValidationError should be raised during PlatformInfo creation
        with pytest.raises(ValidationError):
            invalid_info = PlatformInfo(
                name="",  # Invalid empty name
                display_name="Test",
                platform_type="uploader",
                implementation_class=MockUploader,
                capabilities=[],
                version="1.0.0",
            )

    def test_unregister_platform(self, registry, sample_uploader_info):
        """Test platform unregistration."""
        # Register first
        registry.register_platform(sample_uploader_info)
        assert "youtube" in registry._platforms

        # Unregister
        registry.unregister_platform("youtube")
        assert "youtube" not in registry._platforms

        # Unregistering non-existent platform should not raise error
        registry.unregister_platform("nonexistent")

    def test_get_platform_info(self, registry, sample_uploader_info):
        """Test getting platform information."""
        registry.register_platform(sample_uploader_info)

        info = registry.get_platform_info("youtube")
        assert info == sample_uploader_info

        # Non-existent platform should return None
        info = registry.get_platform_info("nonexistent")
        assert info is None

    def test_is_platform_registered(self, registry, sample_uploader_info):
        """Test checking if platform is registered."""
        assert not registry.is_platform_registered("youtube")

        registry.register_platform(sample_uploader_info)
        assert registry.is_platform_registered("youtube")

    def test_list_platforms(
        self, registry, sample_uploader_info, sample_publisher_info
    ):
        """Test listing registered platforms."""
        # Empty registry
        platforms = registry.list_platforms()
        assert platforms == []

        # Register platforms
        registry.register_platform(sample_uploader_info)
        registry.register_platform(sample_publisher_info)

        platforms = registry.list_platforms()
        assert len(platforms) == 2
        assert "youtube" in [p.name for p in platforms]
        assert "facebook" in [p.name for p in platforms]

    def test_list_platforms_by_type(
        self, registry, sample_uploader_info, sample_publisher_info
    ):
        """Test listing platforms filtered by type."""
        registry.register_platform(sample_uploader_info)
        registry.register_platform(sample_publisher_info)

        uploaders = registry.list_platforms(platform_type="uploader")
        assert len(uploaders) == 1
        assert uploaders[0].name == "youtube"

        publishers = registry.list_platforms(platform_type="publisher")
        assert len(publishers) == 1
        assert publishers[0].name == "facebook"

        # Invalid type should return empty list
        invalid = registry.list_platforms(platform_type="invalid")
        assert invalid == []

    def test_list_platforms_by_capability(
        self, registry, sample_uploader_info, sample_publisher_info
    ):
        """Test listing platforms filtered by capability."""
        registry.register_platform(sample_uploader_info)
        registry.register_platform(sample_publisher_info)

        video_platforms = registry.list_platforms(
            capability=PlatformCapability.VIDEO_UPLOAD
        )
        assert len(video_platforms) == 1
        assert video_platforms[0].name == "youtube"

        text_platforms = registry.list_platforms(
            capability=PlatformCapability.TEXT_PUBLISHING
        )
        assert len(text_platforms) == 1
        assert text_platforms[0].name == "facebook"

        # Capability not supported by any platform
        batch_platforms = registry.list_platforms(
            capability=PlatformCapability.BATCH_OPERATIONS
        )
        assert batch_platforms == []

    def test_create_platform_instance(self, registry, sample_uploader_info):
        """Test creating platform instances."""
        registry.register_platform(sample_uploader_info)

        config = PlatformConfig(platform_name="youtube")
        instance = registry.create_platform_instance("youtube", config)

        assert isinstance(instance, MockUploader)
        assert instance.platform_name == "youtube"

    def test_create_platform_instance_unregistered(self, registry):
        """Test creating instance for unregistered platform."""
        config = PlatformConfig(platform_name="nonexistent")

        with pytest.raises(
            RegistryError, match="Platform 'nonexistent' is not registered"
        ):
            registry.create_platform_instance("nonexistent", config)

    def test_create_platform_instance_instantiation_error(self, registry):
        """Test handling instantiation errors."""

        # Create platform info with class that will fail to instantiate
        class FailingUploader(BaseUploader):
            def __init__(self, *args, **kwargs):
                raise ValueError("Instantiation failed")

            async def authenticate(self) -> bool:
                return False

            async def _upload_media(self, file_path, metadata, progress_callback=None):
                pass

            def _validate_metadata(self, metadata):
                pass

        failing_info = PlatformInfo(
            name="failing",
            display_name="Failing",
            platform_type="uploader",
            implementation_class=FailingUploader,
            capabilities=[],
            version="1.0.0",
        )

        registry.register_platform(failing_info)
        config = PlatformConfig(platform_name="failing")

        with pytest.raises(RegistryError, match="Failed to create platform instance"):
            registry.create_platform_instance("failing", config)

    def test_validate_platform_implementation(self, registry):
        """Test platform implementation validation."""
        # Valid uploader
        valid_uploader_info = PlatformInfo(
            name="valid_uploader",
            display_name="Valid Uploader",
            platform_type="uploader",
            implementation_class=MockUploader,
            capabilities=[],
            version="1.0.0",
        )

        # Should not raise
        registry._validate_platform_implementation(valid_uploader_info)

        # Valid publisher
        valid_publisher_info = PlatformInfo(
            name="valid_publisher",
            display_name="Valid Publisher",
            platform_type="publisher",
            implementation_class=MockPublisher,
            capabilities=[],
            version="1.0.0",
        )

        # Should not raise
        registry._validate_platform_implementation(valid_publisher_info)

        # Invalid uploader (not subclass of BaseUploader)
        class InvalidUploader:
            pass

        invalid_uploader_info = PlatformInfo(
            name="invalid_uploader",
            display_name="Invalid Uploader",
            platform_type="uploader",
            implementation_class=InvalidUploader,
            capabilities=[],
            version="1.0.0",
        )

        with pytest.raises(
            ValidationError,
            match="Uploader implementation must inherit from BaseUploader",
        ):
            registry._validate_platform_implementation(invalid_uploader_info)

        # Invalid publisher (not subclass of BasePublisher)
        class InvalidPublisher:
            pass

        invalid_publisher_info = PlatformInfo(
            name="invalid_publisher",
            display_name="Invalid Publisher",
            platform_type="publisher",
            implementation_class=InvalidPublisher,
            capabilities=[],
            version="1.0.0",
        )

        with pytest.raises(
            ValidationError,
            match="Publisher implementation must inherit from BasePublisher",
        ):
            registry._validate_platform_implementation(invalid_publisher_info)

    def test_check_platform_health(self, registry, sample_uploader_info):
        """Test platform health checking."""
        registry.register_platform(sample_uploader_info)

        # Mock the health check method
        with patch.object(
            MockUploader, "health_check", return_value=True
        ) as mock_health:
            config = PlatformConfig(platform_name="youtube")
            is_healthy = registry.check_platform_health("youtube", config)
            assert is_healthy is True
            mock_health.assert_called_once()

        # Test health check failure
        with patch.object(MockUploader, "health_check", return_value=False):
            is_healthy = registry.check_platform_health("youtube", config)
            assert is_healthy is False

        # Test health check exception
        with patch.object(
            MockUploader, "health_check", side_effect=Exception("Health check failed")
        ):
            is_healthy = registry.check_platform_health("youtube", config)
            assert is_healthy is False

    def test_check_platform_health_unregistered(self, registry):
        """Test health check for unregistered platform."""
        config = PlatformConfig(platform_name="nonexistent")

        with pytest.raises(
            RegistryError, match="Platform 'nonexistent' is not registered"
        ):
            registry.check_platform_health("nonexistent", config)

    @patch("medusa.utils.registry.importlib")
    def test_discover_platforms_success(self, mock_importlib, registry):
        """Test successful platform discovery."""
        # Mock package
        mock_package = Mock()
        mock_package.__path__ = ["/fake/path"]

        # Mock module discovery
        mock_module = Mock()
        mock_module.PLATFORM_INFO = PlatformInfo(
            name="discovered",
            display_name="Discovered Platform",
            platform_type="uploader",
            implementation_class=MockUploader,
            capabilities=[],
            version="1.0.0",
        )

        # Configure mock to return package first, then module
        mock_importlib.import_module.side_effect = [mock_package, mock_module]

        # Mock finding modules
        with patch("medusa.utils.registry.pkgutil.iter_modules") as mock_iter:
            mock_iter.return_value = [(None, "discovered_platform", False)]

            discovered = registry.discover_platforms(["test.package"])

            assert len(discovered) == 1
            assert discovered[0].name == "discovered"
            assert registry.is_platform_registered("discovered")

    @patch("medusa.utils.registry.importlib")
    def test_discover_platforms_import_error(self, mock_importlib, registry):
        """Test platform discovery with import errors."""
        mock_importlib.import_module.side_effect = ImportError("Module not found")

        with patch("medusa.utils.registry.pkgutil.iter_modules") as mock_iter:
            mock_iter.return_value = [(None, "failing_module", False)]

            # Should not raise, but should log the error
            discovered = registry.discover_platforms(["test.package"])
            assert len(discovered) == 0

    @patch("medusa.utils.registry.importlib")
    def test_discover_platforms_no_platform_info(self, mock_importlib, registry):
        """Test platform discovery when module has no PLATFORM_INFO."""
        # Mock package
        mock_package = Mock()
        mock_package.__path__ = ["/fake/path"]

        mock_module = Mock()
        del mock_module.PLATFORM_INFO  # Remove PLATFORM_INFO attribute

        # Configure mock to return package first, then module
        mock_importlib.import_module.side_effect = [mock_package, mock_module]

        with patch("medusa.utils.registry.pkgutil.iter_modules") as mock_iter:
            mock_iter.return_value = [(None, "no_platform_info", False)]

            discovered = registry.discover_platforms(["test.package"])
            assert len(discovered) == 0

    def test_clear_registry(
        self, registry, sample_uploader_info, sample_publisher_info
    ):
        """Test clearing the registry."""
        registry.register_platform(sample_uploader_info)
        registry.register_platform(sample_publisher_info)

        assert len(registry.list_platforms()) == 2

        registry.clear()

        assert len(registry.list_platforms()) == 0
        assert not registry.is_platform_registered("youtube")
        assert not registry.is_platform_registered("facebook")

    def test_registry_singleton_behavior(self):
        """Test that registry can be used as singleton."""
        registry1 = PlatformRegistry.get_instance()
        registry2 = PlatformRegistry.get_instance()

        assert registry1 is registry2

    def test_get_registry_stats(
        self, registry, sample_uploader_info, sample_publisher_info
    ):
        """Test getting registry statistics."""
        # Empty registry
        stats = registry.get_stats()
        assert stats["total_platforms"] == 0
        assert stats["uploaders"] == 0
        assert stats["publishers"] == 0
        assert stats["capabilities"] == {}

        # Add platforms
        registry.register_platform(sample_uploader_info)
        registry.register_platform(sample_publisher_info)

        stats = registry.get_stats()
        assert stats["total_platforms"] == 2
        assert stats["uploaders"] == 1
        assert stats["publishers"] == 1
        assert "VIDEO_UPLOAD" in stats["capabilities"]
        assert "TEXT_PUBLISHING" in stats["capabilities"]

    def test_export_registry_config(
        self, registry, sample_uploader_info, sample_publisher_info
    ):
        """Test exporting registry configuration."""
        registry.register_platform(sample_uploader_info)
        registry.register_platform(sample_publisher_info)

        config = registry.export_config()

        assert "platforms" in config
        assert len(config["platforms"]) == 2

        # Check that platform info is properly serialized
        youtube_config = next(p for p in config["platforms"] if p["name"] == "youtube")
        assert youtube_config["display_name"] == "YouTube"
        assert youtube_config["platform_type"] == "uploader"
        assert "VIDEO_UPLOAD" in youtube_config["capabilities"]


class TestRegistryError:
    """Test RegistryError exception."""

    def test_registry_error_creation(self):
        """Test RegistryError creation."""
        error = RegistryError("Test error", platform_name="test")

        assert "Test error" in str(error)
        assert error.platform_name == "test"
        assert isinstance(error, MedusaError)

    def test_registry_error_without_platform(self):
        """Test RegistryError without platform name."""
        error = RegistryError("Test error")

        assert "Test error" in str(error)
        assert error.platform_name is None


class TestIntegrationScenarios:
    """Integration tests for registry system."""

    @pytest.fixture
    def populated_registry(self):
        """Create registry with multiple platforms."""
        registry = PlatformRegistry()

        # Add uploader
        uploader_info = PlatformInfo(
            name="youtube",
            display_name="YouTube",
            platform_type="uploader",
            implementation_class=MockUploader,
            capabilities=[
                PlatformCapability.VIDEO_UPLOAD,
                PlatformCapability.METADATA_SUPPORT,
            ],
            version="1.0.0",
        )
        registry.register_platform(uploader_info)

        # Add publisher
        publisher_info = PlatformInfo(
            name="facebook",
            display_name="Facebook",
            platform_type="publisher",
            implementation_class=MockPublisher,
            capabilities=[
                PlatformCapability.TEXT_PUBLISHING,
                PlatformCapability.LINK_PUBLISHING,
            ],
            version="1.0.0",
        )
        registry.register_platform(publisher_info)

        return registry

    def test_full_workflow_uploader(self, populated_registry):
        """Test complete workflow for uploader platform."""
        registry = populated_registry

        # Check platform is registered
        assert registry.is_platform_registered("youtube")

        # Get platform info
        info = registry.get_platform_info("youtube")
        assert info.name == "youtube"
        assert info.platform_type == "uploader"

        # Create instance
        config = PlatformConfig(platform_name="youtube")
        instance = registry.create_platform_instance("youtube", config)
        assert isinstance(instance, MockUploader)

        # Check health (assuming MockUploader has health_check method)
        with patch.object(MockUploader, "health_check", return_value=True):
            is_healthy = registry.check_platform_health("youtube", config)
            assert is_healthy is True

    def test_full_workflow_publisher(self, populated_registry):
        """Test complete workflow for publisher platform."""
        registry = populated_registry

        # Check platform is registered
        assert registry.is_platform_registered("facebook")

        # Get platform info
        info = registry.get_platform_info("facebook")
        assert info.name == "facebook"
        assert info.platform_type == "publisher"

        # Create instance
        config = PlatformConfig(platform_name="facebook")
        instance = registry.create_platform_instance("facebook", config)
        assert isinstance(instance, MockPublisher)

        # Check health
        with patch.object(MockPublisher, "health_check", return_value=True):
            is_healthy = registry.check_platform_health("facebook", config)
            assert is_healthy is True

    def test_capability_based_platform_selection(self, populated_registry):
        """Test selecting platforms based on capabilities."""
        registry = populated_registry

        # Find platforms that support video upload
        video_platforms = registry.list_platforms(
            capability=PlatformCapability.VIDEO_UPLOAD
        )
        assert len(video_platforms) == 1
        assert video_platforms[0].name == "youtube"

        # Find platforms that support text publishing
        text_platforms = registry.list_platforms(
            capability=PlatformCapability.TEXT_PUBLISHING
        )
        assert len(text_platforms) == 1
        assert text_platforms[0].name == "facebook"

        # Find platforms that support metadata
        metadata_platforms = registry.list_platforms(
            capability=PlatformCapability.METADATA_SUPPORT
        )
        assert len(metadata_platforms) == 1
        assert metadata_platforms[0].name == "youtube"

    def test_registry_persistence_simulation(self, populated_registry):
        """Test simulating registry persistence through export/import."""
        registry = populated_registry

        # Export configuration
        config = registry.export_config()

        # Create new registry and simulate loading from config
        new_registry = PlatformRegistry()

        # In a real implementation, we would have an import_config method
        # For now, we'll manually register platforms to simulate this
        for platform_config in config["platforms"]:
            if platform_config["name"] == "youtube":
                info = PlatformInfo(
                    name=platform_config["name"],
                    display_name=platform_config["display_name"],
                    platform_type=platform_config["platform_type"],
                    implementation_class=MockUploader,
                    capabilities=[
                        PlatformCapability[cap]
                        for cap in platform_config["capabilities"]
                    ],
                    version=platform_config["version"],
                    description=platform_config.get("description", ""),
                )
                new_registry.register_platform(info)
            elif platform_config["name"] == "facebook":
                info = PlatformInfo(
                    name=platform_config["name"],
                    display_name=platform_config["display_name"],
                    platform_type=platform_config["platform_type"],
                    implementation_class=MockPublisher,
                    capabilities=[
                        PlatformCapability[cap]
                        for cap in platform_config["capabilities"]
                    ],
                    version=platform_config["version"],
                    description=platform_config.get("description", ""),
                )
                new_registry.register_platform(info)

        # Verify new registry has same platforms
        assert new_registry.is_platform_registered("youtube")
        assert new_registry.is_platform_registered("facebook")
        assert len(new_registry.list_platforms()) == 2
