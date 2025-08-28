# ABOUTME: PresetManager class for managing built-in and custom configuration presets
# ABOUTME: Provides preset templates, validation, and persistence for cinemon configurations

"""Preset management for cinemon configurations."""

import json
from pathlib import Path
from typing import Dict, List

import yaml
from setka_common.config.yaml_config import BlenderYAMLConfig, YAMLConfigLoader

# PresetConfig removed - using BlenderYAMLConfig from common instead


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

    # No more hardcoded presets - will load from YAML files

    def __init__(self, preset_dir: Path = None):
        """Initialize PresetManager.

        Args:
            preset_dir: Optional path to preset directory. If None, uses default.
        """
        self._custom_presets_cache = None
        self.builtin_presets = {}
        if preset_dir is not None:
            self.preset_dir = preset_dir
        else:
            self.preset_dir = (
                Path(__file__).parent.parent.parent.parent
                / "blender_addon"
                / "example_presets"
            )
        self._load_builtin_presets()

    def get_preset(self, name: str) -> BlenderYAMLConfig:
        """
        Get preset configuration by name.

        Args:
            name: Preset name

        Returns:
            BlenderYAMLConfig object

        Raises:
            ValueError: If preset doesn't exist
        """
        # Check built-in presets first
        if name in self.builtin_presets:
            return self.builtin_presets[name]

        # Check custom presets
        custom_presets = self._load_custom_presets()
        if name in custom_presets:
            return custom_presets[name]

        raise ValueError(f"Preset '{name}' not found")

    def list_presets(self) -> List[str]:
        """
        List all available preset names.

        Returns:
            List of preset names (built-in + custom)
        """
        builtin_names = list(self.builtin_presets.keys())
        custom_names = list(self._load_custom_presets().keys())
        return sorted(builtin_names + custom_names)

    def _load_custom_presets(self) -> Dict[str, BlenderYAMLConfig]:
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
                with preset_file.open("r", encoding="utf-8") as f:
                    preset_data = json.load(f)

                preset_name = preset_file.stem

                # Convert dict to BlenderYAMLConfig
                loader = YAMLConfigLoader(resolve_paths=False)
                config = loader._parse_and_validate(preset_data)
                custom_presets[preset_name] = config

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

    def _load_builtin_presets(self):
        """Load all YAML presets from preset directory."""
        self.builtin_presets = {}

        if not self.preset_dir.exists():
            print(f"Warning: Preset directory not found: {self.preset_dir}")
            return

        for yaml_file in self.preset_dir.glob("*.yaml"):
            preset_name = yaml_file.stem
            try:
                # Load preset without validation (presets are templates)
                config = self._load_preset_template(yaml_file)
                self.builtin_presets[preset_name] = config

            except Exception as e:
                print(f"Error loading preset {yaml_file}: {e}")
                continue

    def _load_preset_template(self, yaml_file: Path) -> BlenderYAMLConfig:
        """Load preset template without validation."""
        # Use YAMLConfigLoader but without path resolution (presets don't have base_directory)
        loader = YAMLConfigLoader(resolve_paths=False)
        return loader.load_from_file(yaml_file)
