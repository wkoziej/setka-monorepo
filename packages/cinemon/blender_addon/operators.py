# ABOUTME: Blender addon operators for loading and applying YAML configurations
# ABOUTME: LoadConfigOperator opens file browser, ApplyConfigOperator runs VSE setup

"""Blender addon operators for Cinemon configuration."""

import sys
from pathlib import Path

# Import Blender API
try:
    import bpy
    from bpy.props import StringProperty
    from bpy.types import Operator
    from bpy_extras.io_utils import ImportHelper
except ImportError:
    # For testing without Blender
    class Operator:
        def report(self, level, message):
            """Mock report method for testing."""
            pass

    class ImportHelper:
        pass

    def StringProperty(**kwargs):
        """Mock StringProperty for testing."""
        # Return actual value for testing
        default = kwargs.get("default", "")
        return default


# Import setka-common configuration system
# Add vendor path for PyYAML first (Blender doesn't have it)
vendor_path = Path(__file__).parent / "vendor"
if str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))

# Add addon directory to path for local setka_common symlink
addon_path = Path(__file__).parent
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))

from setka_common.config.yaml_config import YAMLConfigLoader


class ValidationError(Exception):
    """Validation error for compatibility."""

    pass


# Import vse_script for applying configurations
blender_path = Path(__file__).parent.parent / "src" / "blender"
if str(blender_path) not in sys.path:
    sys.path.insert(0, str(blender_path))

try:
    from vse_script import BlenderVSEConfigurator
except ImportError:
    # For testing
    class BlenderVSEConfigurator:
        def __init__(self, config_data=None):
            self.config_data = config_data

        def setup_vse_project(self):
            return True


class LoadConfigOperator(Operator, ImportHelper):
    """Load YAML configuration for Cinemon VSE setup."""

    bl_idname = "cinemon.load_config"
    bl_label = "Load Cinemon Config"
    bl_description = "Load YAML configuration for VSE animation setup"
    bl_options = {"REGISTER", "UNDO"}

    # File browser properties
    filename_ext = ".yaml"

    # Properties - use try/except for testing compatibility
    try:
        filter_glob: StringProperty(
            default="*.yaml;*.yml",
            options={"HIDDEN"},
            maxlen=255,
        )

        filepath: StringProperty(
            name="File Path",
            description="Path to YAML configuration file",
            maxlen=1024,
            subtype="FILE_PATH",
        )
    except NameError:
        # For testing without bpy
        filter_glob = "*.yaml;*.yml"
        filepath = ""

    def execute(self, context):
        """Load and validate YAML configuration file."""
        try:
            # Load configuration using YAMLConfigLoader
            loader = YAMLConfigLoader()
            config = loader.load_from_file(self.filepath)

            # Don't store config object - just path (config will be reloaded when needed)

            # Store filepath for reference - THIS IS THE KEY FOR PANEL
            context.scene.cinemon_config_path = self.filepath

            # REMOVED: Don't store strip_animations in memory anymore
            # OLD CODE REMOVED:
            # context.scene["cinemon_strip_animations"] = config.strip_animations

            # Store basic info for main panel display
            if hasattr(config, "layout") and hasattr(config.layout, "type"):
                context.scene["cinemon_layout_type"] = config.layout.type

            # Count animations by reading from config object (not storing)
            if hasattr(config, "strip_animations") and config.strip_animations:
                total_animations = sum(
                    len(anims) for anims in config.strip_animations.values()
                )
                context.scene["cinemon_animations_count"] = total_animations

            self.report(
                {"INFO"}, f"Loaded configuration from {Path(self.filepath).name}"
            )
            return {"FINISHED"}

        except ValidationError as e:
            self.report({"ERROR"}, f"Configuration validation error: {e}")
            return {"CANCELLED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to load configuration: {e}")
            return {"CANCELLED"}

    def invoke(self, context, event):
        """Open file browser for config selection."""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ApplyConfigOperator(Operator):
    """Apply loaded YAML configuration to create VSE project."""

    bl_idname = "cinemon.apply_config"
    bl_label = "Apply Cinemon Config"
    bl_description = "Apply loaded configuration to create animated VSE project"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Apply loaded configuration to VSE."""
        # Check if configuration path is available
        if (
            not hasattr(context.scene, "cinemon_config_path")
            or not context.scene.cinemon_config_path
        ):
            self.report({"ERROR"}, "No config loaded. Use 'Load Cinemon Config' first.")
            return {"CANCELLED"}

        try:
            # Re-load configuration from file (to get latest changes from YAML)
            config_path = context.scene.cinemon_config_path
            loader = YAMLConfigLoader()
            config = loader.load_from_file(config_path)

            # Use the original BlenderVSEConfigurator from vse_script directly
            from vse_script import BlenderVSEConfigurator

            # Create configurator with config file path (not object)
            configurator = BlenderVSEConfigurator(config_path)

            # Apply to existing project (not setup from scratch)
            success = configurator.apply_to_existing_project()

            if success:
                try:
                    self.report(
                        {"INFO"},
                        f"Changes applied successfully from {Path(config_path).name}",
                    )
                except:
                    print(
                        f"✓ Changes applied successfully from {Path(config_path).name}"
                    )
                return {"FINISHED"}
            else:
                try:
                    self.report({"ERROR"}, "Failed to apply changes to VSE project")
                except:
                    print("✗ Failed to apply changes to VSE project")
                return {"CANCELLED"}

        except Exception as e:
            try:
                self.report({"ERROR"}, f"Error applying configuration: {e}")
            except:
                print(f"✗ Error applying configuration: {e}")
            return {"CANCELLED"}


# Removed BlenderVSEConfiguratorDirect - using original BlenderVSEConfigurator instead


# Operator classes for registration
classes = [
    LoadConfigOperator,
    ApplyConfigOperator,
]


def register():
    """Register operators."""
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
    except (NameError, AttributeError):
        # bpy not available in test environment
        pass


def unregister():
    """Unregister operators."""
    try:
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
    except (NameError, AttributeError):
        # bpy not available in test environment
        pass
