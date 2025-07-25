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
        default = kwargs.get('default', '')
        return default

# Import setka-common configuration system
try:
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
except ImportError as e:
    print(f"Warning: setka-common not available in operators.py: {e}")
    # Fallback for testing
    class YAMLConfigLoader:
        def load_config(self, path):
            return {}

    class ValidationError(Exception):
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
    bl_options = {'REGISTER', 'UNDO'}

    # File browser properties
    filename_ext = ".yaml"

    # Properties - use try/except for testing compatibility
    try:
        filter_glob: StringProperty(
            default="*.yaml;*.yml",
            options={'HIDDEN'},
            maxlen=255,
        )

        filepath: StringProperty(
            name="File Path",
            description="Path to YAML configuration file",
            maxlen=1024,
            subtype='FILE_PATH'
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

            # Store configuration in scene for later use
            context.scene.cinemon_config = config

            # Store filepath for reference
            context.scene.cinemon_config_path = self.filepath

            self.report({'INFO'}, f"Loaded configuration from {Path(self.filepath).name}")
            return {'FINISHED'}

        except ValidationError as e:
            self.report({'ERROR'}, f"Configuration validation error: {e}")
            return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to load configuration: {e}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        """Open file browser for config selection."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ApplyConfigOperator(Operator):
    """Apply loaded YAML configuration to create VSE project."""

    bl_idname = "cinemon.apply_config"
    bl_label = "Apply Cinemon Config"
    bl_description = "Apply loaded configuration to create animated VSE project"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Apply loaded configuration to VSE."""
        # Check if configuration is loaded
        if not hasattr(context.scene, 'cinemon_config'):
            self.report({'ERROR'}, "No config loaded. Use 'Load Cinemon Config' first.")
            return {'CANCELLED'}

        try:
            config = context.scene.cinemon_config

            # Convert config to internal format and create configurator
            loader = YAMLConfigLoader()
            internal_config = loader.convert_to_internal(config)

            # Create temporary file path for vse_script compatibility
            # In real usage, this would be handled differently

            # Create configurator with direct config data
            configurator = BlenderVSEConfiguratorDirect(internal_config)

            # Apply configuration
            success = configurator.setup_vse_project()

            if success:
                config_name = getattr(context.scene, 'cinemon_config_path', 'loaded config')
                self.report({'INFO'}, f"VSE project created successfully from {Path(config_name).name}")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to setup VSE project")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error applying configuration: {e}")
            return {'CANCELLED'}


class BlenderVSEConfiguratorDirect(BlenderVSEConfigurator):
    """VSE Configurator that accepts config data directly instead of file path."""

    def __init__(self, config_data):
        """Initialize with config data instead of file path."""
        # Set config data directly
        self.config_data = config_data

        # Set attributes from config (maintaining compatibility)
        project = self.config_data['project']
        self.video_files = [Path(f) for f in project['video_files']]
        self.main_audio = Path(project['main_audio']) if project.get('main_audio') else None
        self.output_blend = Path(project['output_blend']) if project.get('output_blend') else None
        self.render_output = Path(project['render_output']) if project.get('render_output') else None
        self.fps = project.get('fps', 30)
        resolution = project.get('resolution', {})
        self.resolution_x = resolution.get('width', 1920)
        self.resolution_y = resolution.get('height', 1080)
        self.beat_division = project.get('beat_division', 8)

        # Animation mode is always compositional
        self.animation_mode = "compositional"

        # Initialize project setup with config (if we have BlenderProjectSetup available)
        try:
            from vse.project_setup import BlenderProjectSetup
            self.project_setup = BlenderProjectSetup({
                "fps": self.fps,
                "resolution_x": self.resolution_x,
                "resolution_y": self.resolution_y,
                "video_files": self.video_files,
                "main_audio": self.main_audio,
                "output_blend": self.output_blend,
                "render_output": self.render_output,
            })
        except ImportError:
            # For testing
            self.project_setup = None


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
