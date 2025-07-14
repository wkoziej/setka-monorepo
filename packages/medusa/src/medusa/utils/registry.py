"""
Platform Registry System for Medusa Library.

Provides platform discovery, registration, and management capabilities.
Supports automatic platform discovery, validation, and health checking.
"""

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Type, Any, Union
from datetime import datetime, timezone

from ..models import PlatformConfig
from ..exceptions import MedusaError, ValidationError
from ..uploaders.base import BaseUploader
from ..publishers.base import BasePublisher


class PlatformCapability(Enum):
    """Enumeration of platform capabilities."""
    VIDEO_UPLOAD = "VIDEO_UPLOAD"
    AUDIO_UPLOAD = "AUDIO_UPLOAD"
    IMAGE_UPLOAD = "IMAGE_UPLOAD"
    TEXT_PUBLISHING = "TEXT_PUBLISHING"
    LINK_PUBLISHING = "LINK_PUBLISHING"
    METADATA_SUPPORT = "METADATA_SUPPORT"
    PROGRESS_TRACKING = "PROGRESS_TRACKING"
    SCHEDULING = "SCHEDULING"
    THUMBNAIL_UPLOAD = "THUMBNAIL_UPLOAD"
    BATCH_OPERATIONS = "BATCH_OPERATIONS"


@dataclass
class PlatformInfo:
    """Information about a registered platform."""
    name: str
    display_name: str
    platform_type: str  # "uploader" or "publisher"
    implementation_class: Type[Union[BaseUploader, BasePublisher]]
    capabilities: List[PlatformCapability] = field(default_factory=list)
    version: str = "1.0.0"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Valid platform types
    VALID_PLATFORM_TYPES = {"uploader", "publisher"}
    
    def __post_init__(self):
        """Validate platform info after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate platform information.
        
        Raises:
            ValidationError: If validation fails
        """
        if not self.name or not self.name.strip():
            raise ValidationError("Platform name cannot be empty")
        
        if self.platform_type not in self.VALID_PLATFORM_TYPES:
            raise ValidationError(f"Invalid platform type: {self.platform_type}")
        
        if self.implementation_class is None:
            raise ValidationError("Implementation class cannot be None")
        
        # Validate name format (alphanumeric and underscores only)
        if not self.name.replace('_', '').isalnum():
            raise ValidationError("Platform name must contain only alphanumeric characters and underscores")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize PlatformInfo to dictionary.
        
        Returns:
            Dictionary representation (excludes implementation_class)
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "platform_type": self.platform_type,
            "capabilities": [cap.value for cap in self.capabilities],
            "version": self.version,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        } 


class RegistryError(MedusaError):
    """Exception raised for registry-related errors."""
    
    def __init__(self, message: str, platform_name: Optional[str] = None):
        super().__init__(message)
        self.platform_name = platform_name 


class PlatformRegistry:
    """
    Registry for managing platform implementations.
    
    Provides:
    - Platform registration and discovery
    - Implementation validation
    - Instance creation
    - Health checking
    - Capability querying
    """
    
    _instance: Optional['PlatformRegistry'] = None
    
    def __init__(self):
        """Initialize the platform registry."""
        self._platforms: Dict[str, PlatformInfo] = {}
        self._auto_discovery_enabled = True
        self.logger = logging.getLogger("medusa.registry")
    
    @classmethod
    def get_instance(cls) -> 'PlatformRegistry':
        """
        Get singleton instance of the registry.
        
        Returns:
            PlatformRegistry singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_platform(self, platform_info: PlatformInfo, force: bool = False) -> None:
        """
        Register a platform in the registry.
        
        Args:
            platform_info: Platform information to register
            force: If True, overwrite existing registration
            
        Raises:
            RegistryError: If platform already registered and force=False
            ValidationError: If platform info is invalid
        """
        # Validate platform info
        platform_info.validate()
        
        # Check if already registered
        if platform_info.name in self._platforms and not force:
            raise RegistryError(
                f"Platform '{platform_info.name}' is already registered",
                platform_name=platform_info.name
            )
        
        # Validate implementation
        self._validate_platform_implementation(platform_info)
        
        # Register platform
        self._platforms[platform_info.name] = platform_info
        
        self.logger.info(
            f"Registered platform '{platform_info.name}' "
            f"({platform_info.platform_type}) version {platform_info.version}"
        )
    
    def unregister_platform(self, platform_name: str) -> None:
        """
        Unregister a platform from the registry.
        
        Args:
            platform_name: Name of platform to unregister
        """
        if platform_name in self._platforms:
            del self._platforms[platform_name]
            self.logger.info(f"Unregistered platform '{platform_name}'")
    
    def get_platform_info(self, platform_name: str) -> Optional[PlatformInfo]:
        """
        Get information about a registered platform.
        
        Args:
            platform_name: Name of the platform
            
        Returns:
            PlatformInfo if registered, None otherwise
        """
        return self._platforms.get(platform_name)
    
    def is_platform_registered(self, platform_name: str) -> bool:
        """
        Check if a platform is registered.
        
        Args:
            platform_name: Name of the platform
            
        Returns:
            True if platform is registered
        """
        return platform_name in self._platforms 
    
    def list_platforms(
        self,
        platform_type: Optional[str] = None,
        capability: Optional[PlatformCapability] = None
    ) -> List[PlatformInfo]:
        """
        List registered platforms with optional filtering.
        
        Args:
            platform_type: Filter by platform type ("uploader" or "publisher")
            capability: Filter by capability
            
        Returns:
            List of matching PlatformInfo objects
        """
        platforms = list(self._platforms.values())
        
        # Filter by platform type
        if platform_type:
            if platform_type in PlatformInfo.VALID_PLATFORM_TYPES:
                platforms = [p for p in platforms if p.platform_type == platform_type]
            else:
                return []  # Invalid type returns empty list
        
        # Filter by capability
        if capability:
            platforms = [p for p in platforms if capability in p.capabilities]
        
        return platforms
    
    def create_platform_instance(
        self,
        platform_name: str,
        config: PlatformConfig
    ) -> Union[BaseUploader, BasePublisher]:
        """
        Create an instance of a registered platform.
        
        Args:
            platform_name: Name of the platform
            config: Platform configuration
            
        Returns:
            Platform instance
            
        Raises:
            RegistryError: If platform not registered or instantiation fails
        """
        if platform_name not in self._platforms:
            raise RegistryError(
                f"Platform '{platform_name}' is not registered",
                platform_name=platform_name
            )
        
        platform_info = self._platforms[platform_name]
        
        try:
            # Create instance with platform name and config
            instance = platform_info.implementation_class(platform_name, config)
            
            self.logger.debug(f"Created instance of platform '{platform_name}'")
            return instance
            
        except Exception as e:
            raise RegistryError(
                f"Failed to create platform instance for '{platform_name}': {e}",
                platform_name=platform_name
            )
    
    def check_platform_health(self, platform_name: str, config: PlatformConfig) -> bool:
        """
        Check if a platform is healthy and available.
        
        Args:
            platform_name: Name of the platform
            config: Platform configuration
            
        Returns:
            True if platform is healthy
            
        Raises:
            RegistryError: If platform not registered
        """
        if platform_name not in self._platforms:
            raise RegistryError(
                f"Platform '{platform_name}' is not registered",
                platform_name=platform_name
            )
        
        try:
            # Create instance and check health
            instance = self.create_platform_instance(platform_name, config)
            
            # Check if instance has health_check method
            if hasattr(instance, 'health_check'):
                return instance.health_check()
            else:
                # If no health check method, assume healthy if instance created
                return True
                
        except Exception as e:
            self.logger.warning(f"Health check failed for platform '{platform_name}': {e}")
            return False 
    
    def discover_platforms(self, packages: List[str]) -> List[PlatformInfo]:
        """
        Discover platforms in specified packages.
        
        Args:
            packages: List of package names to search
            
        Returns:
            List of discovered PlatformInfo objects
        """
        discovered = []
        
        for package_name in packages:
            try:
                # Import package
                package = importlib.import_module(package_name)
                
                # Iterate through modules in package
                for finder, module_name, ispkg in pkgutil.iter_modules(package.__path__):
                    if ispkg:
                        continue
                    
                    try:
                        # Import module
                        full_module_name = f"{package_name}.{module_name}"
                        module = importlib.import_module(full_module_name)
                        
                        # Check if module has PLATFORM_INFO
                        if hasattr(module, 'PLATFORM_INFO'):
                            platform_info = module.PLATFORM_INFO
                            
                            # Validate and register
                            platform_info.validate()
                            self.register_platform(platform_info, force=True)
                            discovered.append(platform_info)
                            
                            self.logger.info(
                                f"Discovered platform '{platform_info.name}' "
                                f"in module '{full_module_name}'"
                            )
                    
                    except (ImportError, AttributeError, ValidationError) as e:
                        self.logger.debug(
                            f"Skipping module '{module_name}' in package '{package_name}': {e}"
                        )
                        continue
            
            except ImportError as e:
                self.logger.warning(f"Could not import package '{package_name}': {e}")
                continue
        
        return discovered
    
    def clear(self) -> None:
        """Clear all registered platforms."""
        self._platforms.clear()
        self.logger.info("Cleared all registered platforms")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        uploaders = sum(1 for p in self._platforms.values() if p.platform_type == "uploader")
        publishers = sum(1 for p in self._platforms.values() if p.platform_type == "publisher")
        
        # Count capabilities
        capability_counts = {}
        for platform in self._platforms.values():
            for capability in platform.capabilities:
                capability_counts[capability.value] = capability_counts.get(capability.value, 0) + 1
        
        return {
            "total_platforms": len(self._platforms),
            "uploaders": uploaders,
            "publishers": publishers,
            "capabilities": capability_counts,
            "auto_discovery_enabled": self._auto_discovery_enabled
        }
    
    def export_config(self) -> Dict[str, Any]:
        """
        Export registry configuration.
        
        Returns:
            Dictionary with registry configuration
        """
        return {
            "platforms": [platform.to_dict() for platform in self._platforms.values()],
            "auto_discovery_enabled": self._auto_discovery_enabled,
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _validate_platform_implementation(self, platform_info: PlatformInfo) -> None:
        """
        Validate that platform implementation conforms to expected interface.
        
        Args:
            platform_info: Platform information to validate
            
        Raises:
            ValidationError: If implementation is invalid
        """
        implementation_class = platform_info.implementation_class
        
        if platform_info.platform_type == "uploader":
            if not issubclass(implementation_class, BaseUploader):
                raise ValidationError(
                    f"Uploader implementation must inherit from BaseUploader"
                )
        
        elif platform_info.platform_type == "publisher":
            if not issubclass(implementation_class, BasePublisher):
                raise ValidationError(
                    f"Publisher implementation must inherit from BasePublisher"
                )
        
        else:
            raise ValidationError(f"Unknown platform type: {platform_info.platform_type}")
        
        self.logger.debug(f"Validated implementation for platform '{platform_info.name}'")


# Global registry instance
_global_registry: Optional[PlatformRegistry] = None


def get_registry() -> PlatformRegistry:
    """
    Get the global platform registry instance.
    
    Returns:
        Global PlatformRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PlatformRegistry()
    return _global_registry 