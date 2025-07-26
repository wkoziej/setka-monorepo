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

import json
import sys
from pathlib import Path
from typing import Optional

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

    class MockApp:
        class Handlers:
            @staticmethod
            def persistent(func):
                return func

        handlers = Handlers()

    class MockBpy:
        props = MockProps()
        types = MockTypes()
        app = MockApp()

    bpy = MockBpy()

# Import addon modules
try:
    from . import animation_panel, apply_system, layout_ui, operators
except ImportError:
    # For testing - import operators directly
    import animation_panel
    import apply_system
    import layout_ui
    import operators

# Add vendor path for PyYAML
vendor_path = Path(__file__).parent / "vendor"
if str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))


def setup_cinemon_paths():
    """Setup paths for importing cinemon modules."""
    addon_path = Path(__file__).parent

    # In Blender, addon is installed in different location
    # Need to find the actual cinemon src path

    # Try to find cinemon src relative to addon installation
    possible_paths = [
        # Development path (monorepo structure)
        addon_path.parent / "src",
        # Alternative: look for cinemon in parent directories
        addon_path.parent.parent / "cinemon" / "src",
        # Installed package path
        Path(sys.prefix) / "lib" / "python3.12" / "site-packages",
    ]

    cinemon_src_path = None
    for path in possible_paths:
        if path.exists() and (path / "blender").exists():
            cinemon_src_path = path
            break

    if not cinemon_src_path:
        # Last resort: try to find it in the monorepo structure
        # Go up until we find setka-monorepo
        current = addon_path
        while current.parent != current:
            if (current / "packages" / "cinemon" / "src").exists():
                cinemon_src_path = current / "packages" / "cinemon" / "src"
                break
            current = current.parent

    if cinemon_src_path:
        # Add paths if not already present
        paths_to_add = [
            str(cinemon_src_path),
            str(
                cinemon_src_path.parent.parent.parent / "common" / "src"
            ),  # For setka_common
        ]

        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)
                print(f"DEBUG: Added to sys.path: {path}")
    else:
        print("WARNING: Could not find cinemon src path")


def get_recording_directory(context) -> Optional[Path]:
    """Get recording directory from current Blender file path."""
    try:
        blend_path = bpy.data.filepath
        if not blend_path:
            return None

        # Assume structure: recording_dir/blender/project.blend
        blend_path = Path(blend_path)
        if blend_path.parent.name == "blender":
            return blend_path.parent.parent

        return None
    except:
        return None


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

        # Apply section - show if there are any pending changes
        layout.separator()

        try:
            from .strip_context import get_strip_context_manager

            manager = get_strip_context_manager()

            if manager.has_pending_changes():
                # Count different types of changes
                animation_changes = len(manager.get_changed_strips())
                layout_changes = 1 if manager.get_pending_layout() else 0

                # Show what will be applied
                box = layout.box()
                box.label(text="Pending Changes:", icon="INFO")
                if animation_changes > 0:
                    box.label(text=f"  • {animation_changes} strip animations")
                if layout_changes > 0:
                    box.label(text="  • Layout configuration")

                # Apply button
                layout.operator(
                    "cinemon.apply_all_changes", text="Apply to VSE", icon="PLAY"
                )
                layout.operator(
                    "cinemon.discard_all_changes", text="Discard Changes", icon="CANCEL"
                )
            else:
                layout.label(text="No pending changes", icon="CHECKMARK")
        except ImportError:
            pass

        layout.separator()


class CINEMON_PT_presets_panel(Panel):
    """Panel for unified preset management."""

    bl_label = "Presets"
    bl_idname = "CINEMON_PT_presets_panel"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Cinemon"
    bl_parent_id = "CINEMON_PT_main_panel"
    bl_options = {"DEFAULT_CLOSED"}  # Start collapsed

    def draw(self, context):
        """Draw the unified presets panel UI."""
        layout = self.layout

        # Unified preset dropdown
        layout.label(text="Select Preset:", icon="PRESET")

        # Preset selection dropdown - will be populated by enum operator
        layout.prop(context.scene, "cinemon_selected_preset", text="")

        # Load preset button
        layout.operator(
            "cinemon.load_selected_preset", text="Load Preset", icon="IMPORT"
        )

        # Current loaded preset info
        current_preset = getattr(context.scene, "cinemon_current_preset", "")
        if current_preset:
            box = layout.box()
            box.label(text=f"Loaded: {current_preset}", icon="CHECKMARK")

        layout.separator()

        # Save preset controls
        layout.label(text="Save Current Config:", icon="EXPORT")
        layout.prop(context.scene, "cinemon_new_preset_name", text="Name")
        layout.operator(
            "cinemon.save_preset", text="Save as New Preset", icon="FILE_NEW"
        )


class CINEMON_OT_load_selected_preset(bpy.types.Operator):
    """Load the selected preset from dropdown."""

    bl_idname = "cinemon.load_selected_preset"
    bl_label = "Load Selected Preset"
    bl_description = "Load the selected preset configuration"
    bl_options = {"REGISTER", "UNDO"}

    def report(self, level, message):
        """Mock report method for testing."""
        pass

    def execute(self, context):
        """Load the selected preset."""
        selected_preset = context.scene.cinemon_selected_preset
        if not selected_preset or selected_preset == "NONE":
            self.report({"WARNING"}, "No preset selected")
            return {"CANCELLED"}

        # Remove .yaml extension if present
        preset_name = selected_preset.replace(".yaml", "")

        print(f"DEBUG: Loading selected preset: {preset_name}")
        try:
            # Get recording directory
            recording_dir = get_recording_directory(context)
            if not recording_dir:
                self.report(
                    {"ERROR"}, "Cannot determine recording directory from Blender file"
                )
                return {"CANCELLED"}

            # Setup paths for import
            setup_cinemon_paths()

            # Import and use CinemonConfigGenerator
            from blender.config import CinemonConfigGenerator

            generator = CinemonConfigGenerator()

            # Generate config with proper paths (like cinemon-blend-setup does)
            try:
                config_path = generator.generate_preset(recording_dir, preset_name)
                print(f"DEBUG: Generated config at: {config_path}")
            except ValueError as e:
                # If generation fails, try to use existing generated config
                config_path = recording_dir / f"animation_config_{preset_name}.yaml"
                if not config_path.exists():
                    self.report({"ERROR"}, f"Failed to generate config: {e}")
                    return {"CANCELLED"}
                print(f"DEBUG: Using existing config: {config_path}")

            # Load generated config
            config_data = self.load_preset_yaml(config_path)
            if not config_data:
                return {"CANCELLED"}

            # Store configuration in scene
            self.store_config_in_scene(context, config_data, config_path, preset_name)

            preset_display = preset_name.replace("-", " ").replace("_", " ").title()
            self.report({"INFO"}, f"Loaded {preset_display} preset")
            return {"FINISHED"}

        except Exception as e:
            print(f"DEBUG: Preset loading exception: {e}")
            import traceback

            traceback.print_exc()
            self.report({"ERROR"}, f"Failed to load preset: {e}")
            return {"CANCELLED"}

    def get_preset_path(self, preset_name):
        """Get full path for preset, checking user presets first, then built-in."""
        import os
        from pathlib import Path

        # Check user presets directory first
        user_presets_dir = Path.home() / ".cinemon" / "presets"
        user_preset_path = user_presets_dir / preset_name

        if user_preset_path.exists():
            return user_preset_path

        # Check built-in presets
        addon_dir = Path(__file__).parent
        builtin_preset_path = addon_dir / "example_presets" / preset_name

        if builtin_preset_path.exists():
            return builtin_preset_path

        return None

    def load_preset_yaml(self, preset_path):
        """Load and parse YAML preset file."""
        try:
            # Add vendor path for PyYAML first
            vendor_path = Path(__file__).parent / "vendor"
            if str(vendor_path) not in sys.path:
                sys.path.insert(0, str(vendor_path))

            import yaml

            with open(preset_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

        except ImportError as e:
            self.report({"ERROR"}, f"PyYAML not available: {e}")
            return None
        except Exception as e:
            self.report({"ERROR"}, f"Failed to load YAML: {e}")
            return None

    def map_video_names_to_strips(self, context, config_data):
        """Map Video_X names from presets to actual strip names in VSE."""
        if not context.scene.sequence_editor:
            print("DEBUG: No sequence editor - cannot map strip names")
            return config_data

        # Get all video strips sorted by channel
        sequences = context.scene.sequence_editor.sequences
        video_strips = [s for s in sequences if s.type == "MOVIE"]
        video_strips.sort(key=lambda s: s.channel)

        print(f"DEBUG: Found {len(video_strips)} video strips in VSE")
        for i, strip in enumerate(video_strips):
            print(f"  Video_{i + 1} -> {strip.name}")

        # Create mapping from Video_X to actual names
        strip_mapping = {}
        for i, strip in enumerate(video_strips):
            video_key = f"Video_{i + 1}"
            strip_mapping[video_key] = strip.name

        # Apply mapping to strip_animations
        strip_animations = config_data.get("strip_animations", {})
        mapped_animations = {}

        for video_key, animations in strip_animations.items():
            if video_key in strip_mapping:
                actual_name = strip_mapping[video_key]
                mapped_animations[actual_name] = animations
                print(
                    f"DEBUG: Mapped {video_key} -> {actual_name} with {len(animations)} animations"
                )
            else:
                # Keep non-Video_X names as-is (for custom presets)
                mapped_animations[video_key] = animations
                print(
                    f"DEBUG: Kept {video_key} as-is with {len(animations)} animations"
                )

        # Return updated config
        updated_config = config_data.copy()
        updated_config["strip_animations"] = mapped_animations
        return updated_config

    def store_config_in_scene(self, context, config_data, preset_path, preset_name):
        """Store configuration data in scene properties."""
        # Store basic paths and info
        context.scene.cinemon_config_path = str(preset_path)
        context.scene.cinemon_current_preset = preset_name.replace(".yaml", "")

        # Store layout info
        layout_data = config_data.get("layout", {})
        context.scene["cinemon_layout_type"] = layout_data.get("type", "unknown")

        # Map Video_X names to actual strip names before storing
        config_data = self.map_video_names_to_strips(context, config_data)

        # Store strip animations for animation panel
        strip_animations = config_data.get("strip_animations", {})
        context.scene["cinemon_strip_animations"] = str(
            strip_animations
        )  # Store as string for now

        # Update strip context manager with loaded config
        try:
            from .strip_context import get_strip_context_manager

            manager = get_strip_context_manager()
            # Use load_preset_for_apply to mark all strips as changed
            manager.load_preset_for_apply(config_data)
            print(
                f"DEBUG: Updated strip context manager with {len(strip_animations)} strips (marked for Apply)"
            )

            # Debug: Print all loaded strip animations
            for strip_name, animations in strip_animations.items():
                print(f"DEBUG: Strip '{strip_name}' has {len(animations)} animations:")
                for i, anim in enumerate(animations):
                    print(
                        f"  {i}: {anim.get('type', 'unknown')} ({anim.get('trigger', 'unknown')})"
                    )

            # Check if changes are pending and auto-apply them
            if manager.has_pending_changes():
                print(
                    f"DEBUG: {len(manager.get_changed_strips())} strips marked for Apply"
                )
                # Auto-apply all changes (layout + animations)
                bpy.ops.cinemon.apply_all_changes()
                print("DEBUG: Auto-applied all changes after preset load")
            else:
                print("DEBUG: WARNING - No pending changes after preset load")

        except ImportError as e:
            print(f"DEBUG: Could not update strip context manager: {e}")
        except Exception as e:
            print(f"DEBUG: Exception in strip context manager: {e}")
            import traceback

            traceback.print_exc()

        # Count animations for display
        total_animations = (
            sum(len(anims) for anims in strip_animations.values())
            if strip_animations
            else 0
        )
        context.scene["cinemon_animations_count"] = total_animations

        print(
            f"DEBUG: Stored config for {len(strip_animations)} strips with {total_animations} total animations"
        )


class CINEMON_OT_apply_all_changes(bpy.types.Operator):
    """Apply all pending changes to VSE."""

    bl_idname = "cinemon.apply_all_changes"
    bl_label = "Apply Changes"
    bl_description = "Apply all pending layout and animation changes to VSE"
    bl_options = {"REGISTER", "UNDO"}

    def apply_layout_to_strips(self, context, layout_config):
        """Apply layout configuration to strips using extracted layout_applicators module."""
        print(
            f"DEBUG: apply_layout_to_strips called with layout_config: {layout_config}"
        )

        # Use extracted layout applicators module (DRY principle)
        from .layout_applicators import apply_layout_to_strips

        success = apply_layout_to_strips(layout_config, context)
        if not success:
            self.report({"WARNING"}, "Failed to apply layout to strips")
        else:
            print("DEBUG: Layout applied successfully")

    def execute(self, context):
        """Apply all pending changes."""
        try:
            from .strip_context import get_strip_context_manager
            from .vse_operators import regenerate_animations_for_strips

            manager = get_strip_context_manager()

            if not manager.has_pending_changes():
                self.report({"INFO"}, "No changes to apply")
                return {"FINISHED"}

            # Get all data BEFORE applying (apply clears the buffer)
            has_layout_changes = bool(manager.layout_changes)
            changed_strips = manager.get_changed_strips()

            # Get current config with all changes (this clears the buffer)
            config = manager.apply_changes()

            # Apply layout changes if any
            self.report(
                {"INFO"},
                f"DEBUG: Checking layout - layout in config: {'layout' in config}, had_layout_changes: {has_layout_changes}",
            )
            if "layout" in config and has_layout_changes:
                self.report(
                    {"INFO"},
                    f"DEBUG: Applying layout type: {config['layout'].get('type', 'unknown')}",
                )
                # Apply layout to strips
                self.apply_layout_to_strips(context, config["layout"])
                self.report({"INFO"}, "DEBUG: Layout applied successfully")
            else:
                self.report({"INFO"}, "DEBUG: No layout to apply")

            # Apply animation changes
            if changed_strips:
                self.report(
                    {"INFO"},
                    f"DEBUG: Regenerating animations for {len(changed_strips)} strips: {changed_strips}",
                )
                regenerate_animations_for_strips(changed_strips, config)
            else:
                self.report({"INFO"}, "DEBUG: No strips to regenerate animations for")

            self.report({"INFO"}, "All changes applied successfully")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to apply changes: {e}")
            return {"CANCELLED"}


class CINEMON_OT_discard_all_changes(bpy.types.Operator):
    """Discard all pending changes."""

    bl_idname = "cinemon.discard_all_changes"
    bl_label = "Discard Changes"
    bl_description = "Discard all pending changes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Discard all pending changes."""
        try:
            from .strip_context import get_strip_context_manager

            manager = get_strip_context_manager()
            manager.discard_changes()

            self.report({"INFO"}, "All changes discarded")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to discard changes: {e}")
            return {"CANCELLED"}


class CINEMON_OT_save_preset(bpy.types.Operator):
    """Save current configuration as a new preset."""

    bl_idname = "cinemon.save_preset"
    bl_label = "Save Preset"
    bl_description = "Save current configuration as a preset"
    bl_options = {"REGISTER", "UNDO"}

    def report(self, level, message):
        """Mock report method for testing."""
        pass

    def execute(self, context):
        """Save current config as preset."""
        preset_name = context.scene.cinemon_new_preset_name.strip()

        if not preset_name:
            self.report({"WARNING"}, "Please enter a preset name")
            return {"CANCELLED"}

        # Add .yaml extension if not present
        if not preset_name.endswith(".yaml"):
            preset_name += ".yaml"

        try:
            # Create user presets directory if it doesn't exist
            from pathlib import Path

            user_presets_dir = Path.home() / ".cinemon" / "presets"
            user_presets_dir.mkdir(parents=True, exist_ok=True)

            preset_path = user_presets_dir / preset_name

            # For now, just copy current loaded config
            # TODO: Build config from current UI state
            current_config_path = getattr(context.scene, "cinemon_config_path", "")
            if current_config_path and Path(current_config_path).exists():
                import shutil

                shutil.copy2(current_config_path, preset_path)
                self.report({"INFO"}, f"Preset saved as {preset_name}")

                # Update preset dropdown
                context.scene.cinemon_selected_preset = preset_name

                return {"FINISHED"}
            else:
                self.report({"WARNING"}, "No configuration loaded to save")
                return {"CANCELLED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to save preset: {e}")
            return {"CANCELLED"}


# All classes for registration
classes = [
    CINEMON_PT_main_panel,
    CINEMON_PT_presets_panel,
    CINEMON_OT_load_selected_preset,
    CINEMON_OT_apply_all_changes,
    CINEMON_OT_discard_all_changes,
    CINEMON_OT_save_preset,
]


def get_available_presets(self, context):
    """Get list of available presets from user and built-in directories."""
    from pathlib import Path

    presets = [("NONE", "Select Preset...", "No preset selected")]

    # Add built-in presets
    try:
        addon_dir = Path(__file__).parent
        builtin_presets_dir = addon_dir / "example_presets"

        if builtin_presets_dir.exists():
            for preset_file in sorted(builtin_presets_dir.glob("*.yaml")):
                preset_name = preset_file.name
                display_name = (
                    preset_name.replace(".yaml", "")
                    .replace("-", " ")
                    .replace("_", " ")
                    .title()
                )
                presets.append(
                    (
                        preset_name,
                        f"{display_name} (Built-in)",
                        f"Built-in preset: {display_name}",
                    )
                )
    except Exception as e:
        print(f"DEBUG: Error loading built-in presets: {e}")

    # Add user presets
    try:
        user_presets_dir = Path.home() / ".cinemon" / "presets"
        if user_presets_dir.exists():
            for preset_file in sorted(user_presets_dir.glob("*.yaml")):
                preset_name = preset_file.name
                display_name = (
                    preset_name.replace(".yaml", "")
                    .replace("-", " ")
                    .replace("_", " ")
                    .title()
                )
                presets.append(
                    (
                        preset_name,
                        f"{display_name} (User)",
                        f"User preset: {display_name}",
                    )
                )
    except Exception as e:
        print(f"DEBUG: Error loading user presets: {e}")

    return presets


@bpy.app.handlers.persistent
def auto_load_handler(dummy):
    """Auto-load preset based on metadata JSON file."""
    try:
        blend_path = bpy.data.filepath
        if not blend_path:
            return  # No blend file loaded

        # Look for metadata file next to .blend
        metadata_file = Path(blend_path).with_suffix(".cinemon.json")
        if not metadata_file.exists():
            return  # No metadata file

        print(f"🔍 Found Cinemon metadata: {metadata_file}")

        # Load metadata
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Check if auto-loading is enabled
        if not metadata.get("auto_load", False):
            print("ℹ Auto-loading disabled in metadata")
            return

        # PRIORITY 1: Use config path from metadata (if exists)
        config_path = metadata.get("config", {}).get("path")
        if config_path and Path(config_path).exists():
            print(f"🎯 Auto-loading from config path: {config_path}")

            # Load config directly
            config_data = None
            with open(config_path, "r", encoding="utf-8") as f:
                vendor_path = Path(__file__).parent / "vendor"
                if str(vendor_path) not in sys.path:
                    sys.path.insert(0, str(vendor_path))

                import yaml

                config_data = yaml.safe_load(f)

            if config_data:
                # Store in scene
                bpy.context.scene.cinemon_config_path = str(config_path)
                bpy.context.scene.cinemon_current_preset = metadata.get(
                    "preset_name", "custom"
                )

                # Map video names and store config using existing preset operator
                # Cannot instantiate operator directly, must use its methods as static
                config_data = CINEMON_OT_load_selected_preset.map_video_names_to_strips(
                    None, bpy.context, config_data
                )
                CINEMON_OT_load_selected_preset.store_config_in_scene(
                    None,
                    bpy.context,
                    config_data,
                    Path(config_path),
                    metadata.get("preset_name", "custom"),
                )

                print(f"✅ Auto-loaded config from: {config_path}")
                return

        # PRIORITY 2: Generate from preset name (fallback)
        preset_name = metadata.get("preset_name")
        if preset_name:
            print(f"🎯 Auto-loading preset (generating config): {preset_name}")

            # Get recording directory
            recording_dir = get_recording_directory(bpy.context)
            if recording_dir:
                # Setup paths and generate config
                setup_cinemon_paths()

                try:
                    from blender.config import CinemonConfigGenerator

                    generator = CinemonConfigGenerator()

                    # Generate config
                    config_path = generator.generate_preset(recording_dir, preset_name)

                    # Load generated config
                    with open(config_path, "r", encoding="utf-8") as f:
                        import yaml

                        config_data = yaml.safe_load(f)

                    # Store in scene using static methods
                    config_data = (
                        CINEMON_OT_load_selected_preset.map_video_names_to_strips(
                            None, bpy.context, config_data
                        )
                    )
                    CINEMON_OT_load_selected_preset.store_config_in_scene(
                        None, bpy.context, config_data, config_path, preset_name
                    )

                    print(f"✅ Auto-loaded preset: {preset_name}")
                except Exception as e:
                    print(f"⚠ Failed to generate/load preset: {e}")
            return

        print("ℹ No preset or config specified in metadata")

    except Exception as e:
        print(f"⚠ Auto-load handler error: {e}")
        import traceback

        traceback.print_exc()


def register():
    """Register addon classes and operators."""
    # Register operators first
    operators.register()

    # Register main UI classes first
    try:
        for cls in classes:
            bpy.utils.register_class(cls)

        # Register preset selection properties
        bpy.types.Scene.cinemon_selected_preset = bpy.props.EnumProperty(
            name="Preset",
            description="Select a preset to load",
            items=get_available_presets,
            default=0,
        )

        bpy.types.Scene.cinemon_current_preset = bpy.props.StringProperty(
            name="Current Preset",
            description="Currently loaded preset name",
            default="",
        )

        bpy.types.Scene.cinemon_new_preset_name = bpy.props.StringProperty(
            name="New Preset Name",
            description="Name for new preset to save",
            default="my_preset",
        )

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

        # Collection property will be registered after AnimationPropertyGroup

        # Register auto-loading handler
        if auto_load_handler not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(auto_load_handler)

    except (NameError, AttributeError):
        # bpy not available in test environment
        pass

    # Register animation UI first (property groups need to be registered before use)
    from . import animation_ui

    animation_ui.register()

    # Now register collection property after AnimationPropertyGroup is registered
    try:
        from .animation_ui import AnimationPropertyGroup

        bpy.types.Scene.cinemon_animations = bpy.props.CollectionProperty(
            type=AnimationPropertyGroup
        )
    except (NameError, AttributeError):
        # bpy not available in test environment
        pass

    # Register layout UI after main panels
    layout_ui.register()

    # Register apply system
    apply_system.register()

    # Register animation panel
    animation_panel.register()

    try:
        print("Cinemon VSE Animator addon registered successfully")
    except (NameError, AttributeError):
        print("Cinemon VSE Animator addon registered successfully")


def unregister():
    """Unregister addon classes and operators."""
    try:
        # Remove auto-loading handler
        if auto_load_handler in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(auto_load_handler)

        # Unregister animation UI
        from . import animation_ui

        animation_ui.unregister()

        # Unregister layout UI
        from . import layout_ui

        layout_ui.unregister()

        # Unregister vse operators
        from . import vse_operators

        vse_operators.unregister()

        # Unregister apply system
        from . import apply_system

        apply_system.unregister()

        # Unregister animation panel
        from . import animation_panel

        animation_panel.unregister()

        # Remove scene properties
        if hasattr(bpy.types.Scene, "cinemon_config"):
            del bpy.types.Scene.cinemon_config
        if hasattr(bpy.types.Scene, "cinemon_config_path"):
            del bpy.types.Scene.cinemon_config_path
        if hasattr(bpy.types.Scene, "cinemon_selected_preset"):
            del bpy.types.Scene.cinemon_selected_preset
        if hasattr(bpy.types.Scene, "cinemon_current_preset"):
            del bpy.types.Scene.cinemon_current_preset
        if hasattr(bpy.types.Scene, "cinemon_new_preset_name"):
            del bpy.types.Scene.cinemon_new_preset_name

        # Unregister main UI classes
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)

    except (NameError, AttributeError, RuntimeError):
        # bpy not available in test environment or already unregistered
        pass

    # Unregister operators last
    operators.unregister()

    print("Cinemon VSE Animator addon unregistered")


# For development/testing
if __name__ == "__main__":
    register()
