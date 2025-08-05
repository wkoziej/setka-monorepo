# ABOUTME: Main Blender addon file with bl_info and registration system
# ABOUTME: Provides Cinemon VSE animation configuration through YAML presets

"""Cinemon Blender Addon for VSE Animation Configuration.

This addon allows users to load YAML configuration presets and apply them
to create animated Video Sequence Editor projects with audio-driven animations.
"""

# Blender addon metadata
bl_info = {
    "name": "Cinemon VSE Animator",
    "author": "Setka Development Team",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Video Sequence Editor > N-Panel > Cinemon",
    "description": "Audio-driven VSE animation configuration using YAML presets",
    "warning": "Requires audio analysis files for animation timing",
    "doc_url": "https://github.com/setka-dev/cinemon",
    "category": "Sequencer",
}

import sys
from pathlib import Path

# Import Blender API
try:
    import bpy
    from bpy.types import Panel
except ImportError:
    # For testing without Blender
    class Panel:
        pass

    # Mock bpy for testing
    class MockProps:
        @staticmethod
        def StringProperty(**kwargs):
            return kwargs.get("default", "")

    class MockTypes:
        class Operator:
            pass

    class MockBpy:
        props = MockProps()
        types = MockTypes()

    bpy = MockBpy()

# Import addon modules
try:
    from . import animation_panel, layout_ui, operators
except ImportError:
    # For testing - import operators directly
    import animation_panel
    import layout_ui
    import operators

# Add vendor path for PyYAML
vendor_path = Path(__file__).parent / "vendor"
if str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))

# Add vse path for vse modules
vse_path = Path(__file__).parent / "vse"
if str(vse_path) not in sys.path:
    sys.path.insert(0, str(vse_path))


class CINEMON_PT_main_panel(Panel):
    """Main panel for Cinemon addon in VSE."""

    bl_label = "Cinemon VSE Animator"
    bl_idname = "CINEMON_PT_main_panel"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Cinemon"

    def draw(self, context):
        """Draw the main panel UI."""
        layout = self.layout

        # Configuration section
        layout.label(text="Configuration:", icon="FILE_FOLDER")

        # Load config button
        layout.operator(
            "cinemon.load_config", text="Load YAML Config", icon="FILEBROWSER"
        )

        # Show loaded config info
        config_path = getattr(context.scene, "cinemon_config_path", "")
        if config_path:
            box = layout.box()
            box.label(text=f"Loaded: {Path(config_path).name}", icon="CHECKMARK")

            # Show stored config info
            if "cinemon_layout_type" in context.scene:
                box.label(text=f"Layout: {context.scene['cinemon_layout_type']}")
            if "cinemon_animations_count" in context.scene:
                box.label(
                    text=f"Animations: {context.scene['cinemon_animations_count']}"
                )

            # Apply button
            layout.separator()
            layout.operator("cinemon.apply_config", text="Apply to VSE", icon="PLAY")
        else:
            layout.label(text="No config loaded", icon="ERROR")

        layout.separator()

        # Quick presets section
        layout.label(text="Quick Presets:", icon="PRESET")

        preset_buttons = [
            ("minimal.yaml", "Minimal", "DOT"),
        ]

        for preset_file, label, icon in preset_buttons:
            op = layout.operator("cinemon.load_preset", text=label, icon=icon)
            op.preset_name = preset_file


class CINEMON_OT_load_preset(bpy.types.Operator):
    """Load a built-in preset."""

    bl_idname = "cinemon.load_preset"
    bl_label = "Load Preset"
    bl_description = "Load a built-in YAML preset"
    bl_options = {"REGISTER", "UNDO"}

    def report(self, level, message):
        """Mock report method for testing."""
        pass

    preset_name: bpy.props.StringProperty(
        name="Preset Name", description="Name of the preset file to load"
    )

    def execute(self, context):
        """Load the specified preset."""
        print(f"DEBUG: Loading preset: {self.preset_name}")
        try:
            # Get preset path
            addon_dir = Path(__file__).parent
            preset_path = addon_dir / "example_presets" / self.preset_name

            if not preset_path.exists():
                self.report({"ERROR"}, f"Preset not found: {self.preset_name}")
                return {"CANCELLED"}

            # Use LoadConfigOperator logic - import setka-common
            try:
                # Add vendor path for PyYAML first
                vendor_path = Path(__file__).parent / "vendor"
                if str(vendor_path) not in sys.path:
                    sys.path.insert(0, str(vendor_path))

                # Add addon directory to path for local setka_common symlink
                addon_path = Path(__file__).parent
                if str(addon_path) not in sys.path:
                    sys.path.insert(0, str(addon_path))

                from setka_common.config.yaml_config import YAMLConfigLoader
            except ImportError as e:
                print(f"DEBUG: setka-common import failed: {e}")
                import traceback

                traceback.print_exc()
                self.report({"ERROR"}, f"setka-common not available: {e}")
                return {"CANCELLED"}

            # Load preset without validation (presets have empty video_files)
            # Use vendored yaml from addon
            import vendor.yaml as yaml

            with open(preset_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # Create simple config object for UI display
            class SimpleConfig:
                def __init__(self, data):
                    self._data = data
                    # Only create nested objects for actual dicts
                    if isinstance(data.get("project"), dict):
                        self.project = SimpleConfig(data["project"])
                    if isinstance(data.get("layout"), dict):
                        self.layout = SimpleConfig(data["layout"])
                    self.strip_animations = data.get("strip_animations", {})

                def __getattr__(self, name):
                    # Prevent recursion by checking _data directly
                    if hasattr(self, "_data") and name in self._data:
                        return self._data[name]
                    return ""

            config = SimpleConfig(config_data)

            # Store filepath for reference - ONLY THIS
            context.scene.cinemon_config_path = str(preset_path)

            # REMOVED: Don't parse and store in memory
            # OLD CODE REMOVED:
            # context.scene["cinemon_strip_animations"] = config.strip_animations

            # Basic display info can be read on-demand or stored minimally
            layout_type = (
                getattr(config.layout, "type", "unknown")
                if hasattr(config, "layout")
                else "unknown"
            )
            context.scene["cinemon_layout_type"] = layout_type

            # Count animations for display
            total_animations = (
                sum(len(anims) for anims in config.strip_animations.values())
                if config.strip_animations
                else 0
            )
            context.scene["cinemon_animations_count"] = total_animations

            preset_display = (
                self.preset_name.replace(".yaml", "").replace("-", " ").title()
            )
            self.report({"INFO"}, f"Loaded {preset_display} preset")
            return {"FINISHED"}

        except Exception as e:
            print(f"DEBUG: Preset loading exception: {e}")
            import traceback

            traceback.print_exc()
            self.report({"ERROR"}, f"Failed to load preset: {e}")
            return {"CANCELLED"}


# All classes for registration
classes = [
    CINEMON_PT_main_panel,
    CINEMON_OT_load_preset,
]


def register():
    """Register addon classes and operators."""
    # Register operators first
    operators.register()

    # Register main UI classes first
    if "bpy" in globals() and hasattr(bpy, "utils"):
        for cls in classes:
            bpy.utils.register_class(cls)

        # Register main scene properties for config storage
        bpy.types.Scene.cinemon_config = bpy.props.PointerProperty(
            name="Cinemon Config",
            description="Loaded YAML configuration object",
            type=bpy.types.PropertyGroup,  # Will store the actual config object
        )

        bpy.types.Scene.cinemon_config_path = bpy.props.StringProperty(
            name="Config Path",
            description="Path to the loaded YAML configuration file",
            default="",
        )

        print("Cinemon VSE Animator addon registered successfully")

    # Register layout UI after main panels
    layout_ui.register()

    # Register animation panel
    animation_panel.register()


def unregister():
    """Unregister addon classes and operators."""
    # Unregister animation panel
    animation_panel.unregister()

    # Unregister layout UI
    layout_ui.unregister()

    if "bpy" in globals() and hasattr(bpy, "utils"):
        # Unregister UI classes
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)

        # Clean up scene properties
        if hasattr(bpy.types.Scene, "cinemon_config"):
            delattr(bpy.types.Scene, "cinemon_config")
        if hasattr(bpy.types.Scene, "cinemon_config_path"):
            delattr(bpy.types.Scene, "cinemon_config_path")

        print("Cinemon VSE Animator addon unregistered")

    # Unregister operators
    operators.unregister()


# For development/testing
if __name__ == "__main__":
    register()
