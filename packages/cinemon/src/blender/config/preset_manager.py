# ABOUTME: PresetManager class for managing built-in and custom configuration presets
# ABOUTME: Provides preset templates, validation, and persistence for cinemon configurations

"""Preset management for cinemon configurations."""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .device_names import DeviceNames


@dataclass
class PresetConfig:
    """Configuration preset for cinemon."""
    name: str
    description: str
    layout: Dict[str, Any]
    animations: List[Dict[str, Any]]


class PresetManager:
    """
    Manages built-in and custom configuration presets.
    
    Provides access to predefined preset templates and allows
    creation and persistence of custom presets.
    
    Example:
        manager = PresetManager()
        vintage_preset = manager.get_preset("vintage")
        manager.create_custom_preset("my-style", custom_config)
    """
    
    # Built-in preset definitions
    BUILTIN_PRESETS = {
        "vintage": {
            "description": "Classic film effects with jitter, grain, and vintage color",
            "layout": {
                "type": "random",
                "config": {
                    "overlap_allowed": False,
                    "margin": 0.1,
                    "min_scale": 0.5,
                    "max_scale": 0.8,
                    "seed": 1950
                }
            },
            "animations": [
                {
                    "type": "shake",
                    "trigger": "beat",
                    "intensity": 2.0,
                    "return_frames": 2,
                    "target_strips": []
                },
                {
                    "type": "jitter",
                    "trigger": "continuous",
                    "intensity": 1.0,
                    "min_interval": 3,
                    "max_interval": 8,
                    "target_strips": []
                },
                {
                    "type": "brightness_flicker",
                    "trigger": "beat",
                    "intensity": 0.1,
                    "return_frames": 1,
                    "target_strips": []
                },
                {
                    "type": "black_white",
                    "trigger": "one_time",
                    "intensity": 0.6,
                    "target_strips": []
                },
                {
                    "type": "film_grain",
                    "trigger": "one_time",
                    "intensity": 0.15,
                    "target_strips": []
                },
                {
                    "type": "vintage_color",
                    "trigger": "one_time",
                    "sepia_amount": 0.4,
                    "contrast_boost": 0.3,
                    "target_strips": []
                }
            ]
        },
        "minimal": {
            "description": "Clean, simple animation with basic scale on bass only",
            "layout": {
                "type": "random",
                "config": {
                    "overlap_allowed": False,
                    "margin": 0.1,
                    "min_scale": 0.6,
                    "max_scale": 0.9,
                    "seed": 1
                }
            },
            "animations": [
                {
                    "type": "scale",
                    "trigger": "energy_peaks",
                    "intensity": 0.2,
                    "duration_frames": 3,
                    "target_strips": []
                }
            ]
        },
        "multi-pip": {
            "description": "Two main cameras fullscreen with corner PiPs, replicating legacy multi-pip behavior",
            "layout": {
                "type": "main-pip",
                "config": {
                    "pip_scale": 0.25,
                    "margin_percent": 0.05
                }
            },
            "animations": [
                {
                    "type": "visibility",
                    "trigger": "sections",
                    "pattern": "alternate",
                    "target_strips": DeviceNames.MAIN_CAMERAS
                },
                {
                    "type": "vintage_color",
                    "trigger": "one_time",
                    "sepia_amount": 0.4,
                    "contrast_boost": 0.3,
                    "target_strips": DeviceNames.MAIN_CAMERAS
                },
                {
                    "type": "jitter",
                    "trigger": "continuous",
                    "intensity": 1.0,
                    "min_interval": 3,
                    "max_interval": 8,
                    "target_strips": DeviceNames.MAIN_CAMERAS
                },
                {
                    "type": "scale",
                    "trigger": "energy_peaks",
                    "intensity": 0.5,
                    "duration_frames": 3,
                    "target_strips": DeviceNames.PIP_CAMERAS
                },
                {
                    "type": "shake",
                    "trigger": "beat",
                    "intensity": 8.0,
                    "return_frames": 2,
                    "target_strips": DeviceNames.PIP_CAMERAS
                }
            ]
        }
    }
    
    def __init__(self):
        """Initialize PresetManager."""
        self._custom_presets_cache = None
    
    def get_preset(self, name: str) -> PresetConfig:
        """
        Get preset configuration by name.
        
        Args:
            name: Preset name
            
        Returns:
            PresetConfig object
            
        Raises:
            ValueError: If preset doesn't exist
        """
        # Check built-in presets first
        if name in self.BUILTIN_PRESETS:
            preset_data = self.BUILTIN_PRESETS[name]
            return PresetConfig(
                name=name,
                description=preset_data["description"],
                layout=preset_data["layout"],
                animations=preset_data["animations"]
            )
        
        # Check custom presets
        custom_presets = self._load_custom_presets()
        if name in custom_presets:
            preset_data = custom_presets[name]
            return PresetConfig(
                name=name,
                description=preset_data["description"],
                layout=preset_data["layout"],
                animations=preset_data["animations"]
            )
        
        raise ValueError(f"Preset '{name}' not found")
    
    def list_presets(self) -> List[str]:
        """
        List all available preset names.
        
        Returns:
            List of preset names (built-in + custom)
        """
        builtin_names = list(self.BUILTIN_PRESETS.keys())
        custom_names = list(self._load_custom_presets().keys())
        return sorted(builtin_names + custom_names)
    
    def create_custom_preset(self, name: str, config: Dict[str, Any], description: str = "") -> None:
        """
        Create and save custom preset.
        
        Args:
            name: Preset name
            config: Preset configuration
            description: Preset description
            
        Raises:
            ValueError: If trying to overwrite built-in preset or invalid config
        """
        # Prevent overwriting built-in presets
        if name in self.BUILTIN_PRESETS:
            raise ValueError(f"Cannot overwrite built-in preset '{name}'")
        
        # Validate configuration
        self._validate_preset_config(config)
        
        # Prepare preset data
        preset_data = {
            "description": description,
            "layout": config["layout"],
            "animations": config["animations"]
        }
        
        # Save to custom presets directory
        custom_presets_dir = self._get_custom_presets_dir()
        custom_presets_dir.mkdir(parents=True, exist_ok=True)
        
        preset_file = custom_presets_dir / f"{name}.json"
        with preset_file.open('w', encoding='utf-8') as f:
            json.dump(preset_data, f, indent=2, ensure_ascii=False)
        
        # Clear cache to reload on next access
        self._custom_presets_cache = None
    
    def _validate_preset_config(self, config: Dict[str, Any]) -> None:
        """
        Validate preset configuration structure.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        required_fields = ["layout", "animations"]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Invalid preset configuration: missing '{field}' field")
        
        # Validate layout structure
        if not isinstance(config["layout"], dict):
            raise ValueError("Invalid preset configuration: 'layout' must be a dictionary")
        
        if "type" not in config["layout"]:
            raise ValueError("Invalid preset configuration: 'layout' missing 'type' field")
        
        # Validate animations structure
        if not isinstance(config["animations"], list):
            raise ValueError("Invalid preset configuration: 'animations' must be a list")
        
        for i, animation in enumerate(config["animations"]):
            if not isinstance(animation, dict):
                raise ValueError(f"Invalid preset configuration: animation {i} must be a dictionary")
            
            if "type" not in animation:
                raise ValueError(f"Invalid preset configuration: animation {i} missing 'type' field")
            
            if "trigger" not in animation:
                raise ValueError(f"Invalid preset configuration: animation {i} missing 'trigger' field")
    
    def _load_custom_presets(self) -> Dict[str, Dict[str, Any]]:
        """
        Load custom presets from disk.
        
        Returns:
            Dictionary of custom preset configurations
        """
        if self._custom_presets_cache is not None:
            return self._custom_presets_cache
        
        custom_presets = {}
        custom_presets_dir = self._get_custom_presets_dir()
        
        if not custom_presets_dir.exists():
            self._custom_presets_cache = custom_presets
            return custom_presets
        
        # Load all JSON files in custom presets directory
        for preset_file in custom_presets_dir.glob("*.json"):
            try:
                with preset_file.open('r', encoding='utf-8') as f:
                    preset_data = json.load(f)
                
                preset_name = preset_file.stem
                custom_presets[preset_name] = preset_data
                
            except (json.JSONDecodeError, KeyError, IOError):
                # Skip corrupt or invalid preset files
                continue
        
        self._custom_presets_cache = custom_presets
        return custom_presets
    
    def _get_custom_presets_dir(self) -> Path:
        """
        Get path to custom presets directory.
        
        Returns:
            Path to custom presets directory
        """
        # Use user's home directory for persistent storage
        home_dir = Path.home()
        return home_dir / ".cinemon" / "presets"