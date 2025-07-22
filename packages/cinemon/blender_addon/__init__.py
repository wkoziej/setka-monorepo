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
            return kwargs.get('default', '')
    
    class MockTypes:
        class Operator:
            pass
    
    class MockBpy:
        props = MockProps()
        types = MockTypes()
    
    bpy = MockBpy()

# Import addon modules
try:
    from . import operators
    from . import layout_ui
    from . import apply_system
    from . import animation_panel
except ImportError:
    # For testing - import operators directly
    import operators
    import layout_ui
    import apply_system
    import animation_panel

# Add vendor path for PyYAML
vendor_path = Path(__file__).parent / "vendor"
if str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))


class CINEMON_PT_main_panel(Panel):
    """Main panel for Cinemon addon in VSE."""
    
    bl_label = "Cinemon VSE Animator"
    bl_idname = "CINEMON_PT_main_panel"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
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
                box.label(text="Pending Changes:", icon='INFO')
                if animation_changes > 0:
                    box.label(text=f"  • {animation_changes} strip animations")
                if layout_changes > 0:
                    box.label(text="  • Layout configuration")
                
                # Apply button
                layout.operator("cinemon.apply_all_changes", text="Apply to VSE", icon='PLAY')
                layout.operator("cinemon.discard_all_changes", text="Discard Changes", icon='CANCEL')
            else:
                layout.label(text="No pending changes", icon='CHECKMARK')
        except ImportError:
            pass
        
        layout.separator()


class CINEMON_PT_presets_panel(Panel):
    """Panel for unified preset management."""
    
    bl_label = "Presets"
    bl_idname = "CINEMON_PT_presets_panel"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Cinemon"
    bl_parent_id = "CINEMON_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}  # Start collapsed
    
    def draw(self, context):
        """Draw the unified presets panel UI."""
        layout = self.layout
        
        # Unified preset dropdown
        layout.label(text="Select Preset:", icon='PRESET')
        
        # Preset selection dropdown - will be populated by enum operator
        layout.prop(context.scene, "cinemon_selected_preset", text="")
        
        # Load preset button
        layout.operator("cinemon.load_selected_preset", text="Load Preset", icon='IMPORT')
        
        # Current loaded preset info
        current_preset = getattr(context.scene, 'cinemon_current_preset', '')
        if current_preset:
            box = layout.box()
            box.label(text=f"Loaded: {current_preset}", icon='CHECKMARK')
        
        layout.separator()
        
        # Save preset controls
        layout.label(text="Save Current Config:", icon='EXPORT')
        layout.prop(context.scene, "cinemon_new_preset_name", text="Name")
        layout.operator("cinemon.save_preset", text="Save as New Preset", icon='FILE_NEW')


class CINEMON_OT_load_selected_preset(bpy.types.Operator):
    """Load the selected preset from dropdown."""
    
    bl_idname = "cinemon.load_selected_preset"
    bl_label = "Load Selected Preset"
    bl_description = "Load the selected preset configuration"
    bl_options = {'REGISTER', 'UNDO'}
    
    def report(self, level, message):
        """Mock report method for testing."""
        pass
    
    def execute(self, context):
        """Load the selected preset."""
        selected_preset = context.scene.cinemon_selected_preset
        if not selected_preset or selected_preset == 'NONE':
            self.report({'WARNING'}, "No preset selected")
            return {'CANCELLED'}
        
        print(f"DEBUG: Loading selected preset: {selected_preset}")
        try:
            preset_path = self.get_preset_path(selected_preset)
            
            if not preset_path or not preset_path.exists():
                self.report({'ERROR'}, f"Preset not found: {selected_preset}")
                return {'CANCELLED'}
            
            # Load and parse preset
            config_data = self.load_preset_yaml(preset_path)
            if not config_data:
                return {'CANCELLED'}
            
            # Store configuration in scene
            self.store_config_in_scene(context, config_data, preset_path, selected_preset)
            
            preset_display = selected_preset.replace('.yaml', '').replace('-', ' ').replace('_', ' ').title()
            self.report({'INFO'}, f"Loaded {preset_display} preset")
            return {'FINISHED'}
            
        except Exception as e:
            print(f"DEBUG: Preset loading exception: {e}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Failed to load preset: {e}")
            return {'CANCELLED'}
    
    def get_preset_path(self, preset_name):
        """Get full path for preset, checking user presets first, then built-in."""
        from pathlib import Path
        import os
        
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
            with open(preset_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
                
        except ImportError as e:
            self.report({'ERROR'}, f"PyYAML not available: {e}")
            return None
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load YAML: {e}")
            return None
    
    def map_video_names_to_strips(self, context, config_data):
        """Map Video_X names from presets to actual strip names in VSE."""
        if not context.scene.sequence_editor:
            print("DEBUG: No sequence editor - cannot map strip names")
            return config_data
        
        # Get all video strips sorted by channel
        sequences = context.scene.sequence_editor.sequences
        video_strips = [s for s in sequences if s.type == 'MOVIE']
        video_strips.sort(key=lambda s: s.channel)
        
        print(f"DEBUG: Found {len(video_strips)} video strips in VSE")
        for i, strip in enumerate(video_strips):
            print(f"  Video_{i+1} -> {strip.name}")
        
        # Create mapping from Video_X to actual names
        strip_mapping = {}
        for i, strip in enumerate(video_strips):
            video_key = f"Video_{i+1}"
            strip_mapping[video_key] = strip.name
        
        # Apply mapping to strip_animations
        strip_animations = config_data.get('strip_animations', {})
        mapped_animations = {}
        
        for video_key, animations in strip_animations.items():
            if video_key in strip_mapping:
                actual_name = strip_mapping[video_key]
                mapped_animations[actual_name] = animations
                print(f"DEBUG: Mapped {video_key} -> {actual_name} with {len(animations)} animations")
            else:
                # Keep non-Video_X names as-is (for custom presets)
                mapped_animations[video_key] = animations
                print(f"DEBUG: Kept {video_key} as-is with {len(animations)} animations")
        
        # Return updated config
        updated_config = config_data.copy()
        updated_config['strip_animations'] = mapped_animations
        return updated_config
    
    def store_config_in_scene(self, context, config_data, preset_path, preset_name):
        """Store configuration data in scene properties."""
        # Store basic paths and info
        context.scene.cinemon_config_path = str(preset_path)
        context.scene.cinemon_current_preset = preset_name.replace('.yaml', '')
        
        # Store layout info
        layout_data = config_data.get('layout', {})
        context.scene['cinemon_layout_type'] = layout_data.get('type', 'unknown')
        
        # Map Video_X names to actual strip names before storing
        config_data = self.map_video_names_to_strips(context, config_data)
        
        # Store strip animations for animation panel
        strip_animations = config_data.get('strip_animations', {})
        context.scene['cinemon_strip_animations'] = str(strip_animations)  # Store as string for now
        
        # Update strip context manager with loaded config
        try:
            from .strip_context import get_strip_context_manager
            manager = get_strip_context_manager()
            # Use load_preset_for_apply to mark all strips as changed
            manager.load_preset_for_apply(config_data)
            print(f"DEBUG: Updated strip context manager with {len(strip_animations)} strips (marked for Apply)")
            
            # Debug: Print all loaded strip animations
            for strip_name, animations in strip_animations.items():
                print(f"DEBUG: Strip '{strip_name}' has {len(animations)} animations:")
                for i, anim in enumerate(animations):
                    print(f"  {i}: {anim.get('type', 'unknown')} ({anim.get('trigger', 'unknown')})")
            
            # Check if changes are pending and auto-apply them
            if manager.has_pending_changes():
                print(f"DEBUG: {len(manager.get_changed_strips())} strips marked for Apply")
                # Auto-apply all changes (layout + animations)
                bpy.ops.cinemon.apply_all_changes()
                print("DEBUG: Auto-applied all changes after preset load")
            else:
                print(f"DEBUG: WARNING - No pending changes after preset load")
                    
        except ImportError as e:
            print(f"DEBUG: Could not update strip context manager: {e}")
        except Exception as e:
            print(f"DEBUG: Exception in strip context manager: {e}")
            import traceback
            traceback.print_exc()
        
        # Count animations for display
        total_animations = sum(len(anims) for anims in strip_animations.values()) if strip_animations else 0
        context.scene['cinemon_animations_count'] = total_animations
        
        print(f"DEBUG: Stored config for {len(strip_animations)} strips with {total_animations} total animations")


class CINEMON_OT_apply_all_changes(bpy.types.Operator):
    """Apply all pending changes to VSE."""
    
    bl_idname = "cinemon.apply_all_changes"
    bl_label = "Apply Changes"
    bl_description = "Apply all pending layout and animation changes to VSE"
    bl_options = {'REGISTER', 'UNDO'}
    
    def apply_layout_to_strips(self, context, layout_config):
        """Apply layout configuration to strips using extracted layout_applicators module."""
        print(f"DEBUG: apply_layout_to_strips called with layout_config: {layout_config}")
        
        # Use extracted layout applicators module (DRY principle)
        from .layout_applicators import apply_layout_to_strips
        
        success = apply_layout_to_strips(layout_config, context)
        if not success:
            self.report({'WARNING'}, "Failed to apply layout to strips")
        else:
            print("DEBUG: Layout applied successfully")
    
    def execute(self, context):
        """Apply all pending changes."""
        try:
            from .strip_context import get_strip_context_manager
            from .vse_operators import regenerate_animations_for_strips
            
            manager = get_strip_context_manager()
            
            if not manager.has_pending_changes():
                self.report({'INFO'}, "No changes to apply")
                return {'FINISHED'}
            
            # Check for layout changes BEFORE applying (apply clears the buffer)
            has_layout_changes = bool(manager.layout_changes)
            
            # Get current config with all changes
            config = manager.apply_changes()
            
            # Apply layout changes if any
            self.report({'INFO'}, f"DEBUG: Checking layout - layout in config: {'layout' in config}, had_layout_changes: {has_layout_changes}")
            if 'layout' in config and has_layout_changes:
                self.report({'INFO'}, f"DEBUG: Applying layout type: {config['layout'].get('type', 'unknown')}")
                # Apply layout to strips
                self.apply_layout_to_strips(context, config['layout'])
                self.report({'INFO'}, "DEBUG: Layout applied successfully")
            else:
                self.report({'INFO'}, "DEBUG: No layout to apply")
            
            # Get changed strips BEFORE applying (apply clears the buffer)
            changed_strips = manager.get_changed_strips()
            
            # Apply all changes to config
            config = manager.apply_changes()
            
            # Apply animation changes
            if changed_strips:
                regenerate_animations_for_strips(changed_strips, config)
            
            self.report({'INFO'}, "All changes applied successfully")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to apply changes: {e}")
            return {'CANCELLED'}


class CINEMON_OT_discard_all_changes(bpy.types.Operator):
    """Discard all pending changes."""
    
    bl_idname = "cinemon.discard_all_changes"
    bl_label = "Discard Changes"
    bl_description = "Discard all pending changes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Discard all pending changes."""
        try:
            from .strip_context import get_strip_context_manager
            
            manager = get_strip_context_manager()
            manager.discard_changes()
            
            self.report({'INFO'}, "All changes discarded")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to discard changes: {e}")
            return {'CANCELLED'}


class CINEMON_OT_save_preset(bpy.types.Operator):
    """Save current configuration as a new preset."""
    
    bl_idname = "cinemon.save_preset"
    bl_label = "Save Preset"
    bl_description = "Save current configuration as a preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    def report(self, level, message):
        """Mock report method for testing."""
        pass
    
    def execute(self, context):
        """Save current config as preset."""
        preset_name = context.scene.cinemon_new_preset_name.strip()
        
        if not preset_name:
            self.report({'WARNING'}, "Please enter a preset name")
            return {'CANCELLED'}
        
        # Add .yaml extension if not present
        if not preset_name.endswith('.yaml'):
            preset_name += '.yaml'
        
        try:
            # Create user presets directory if it doesn't exist
            from pathlib import Path
            user_presets_dir = Path.home() / ".cinemon" / "presets"
            user_presets_dir.mkdir(parents=True, exist_ok=True)
            
            preset_path = user_presets_dir / preset_name
            
            # For now, just copy current loaded config
            # TODO: Build config from current UI state
            current_config_path = getattr(context.scene, 'cinemon_config_path', '')
            if current_config_path and Path(current_config_path).exists():
                import shutil
                shutil.copy2(current_config_path, preset_path)
                self.report({'INFO'}, f"Preset saved as {preset_name}")
                
                # Update preset dropdown
                context.scene.cinemon_selected_preset = preset_name
                
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "No configuration loaded to save")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save preset: {e}")
            return {'CANCELLED'}


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
    
    presets = [('NONE', 'Select Preset...', 'No preset selected')]
    
    # Add built-in presets
    try:
        addon_dir = Path(__file__).parent
        builtin_presets_dir = addon_dir / "example_presets"
        
        if builtin_presets_dir.exists():
            for preset_file in sorted(builtin_presets_dir.glob("*.yaml")):
                preset_name = preset_file.name
                display_name = preset_name.replace('.yaml', '').replace('-', ' ').replace('_', ' ').title()
                presets.append((preset_name, f"{display_name} (Built-in)", f"Built-in preset: {display_name}"))
    except Exception as e:
        print(f"DEBUG: Error loading built-in presets: {e}")
    
    # Add user presets
    try:
        user_presets_dir = Path.home() / ".cinemon" / "presets"
        if user_presets_dir.exists():
            for preset_file in sorted(user_presets_dir.glob("*.yaml")):
                preset_name = preset_file.name
                display_name = preset_name.replace('.yaml', '').replace('-', ' ').replace('_', ' ').title()
                presets.append((preset_name, f"{display_name} (User)", f"User preset: {display_name}"))
    except Exception as e:
        print(f"DEBUG: Error loading user presets: {e}")
    
    return presets



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
            default=0
        )
        
        bpy.types.Scene.cinemon_current_preset = bpy.props.StringProperty(
            name="Current Preset",
            description="Currently loaded preset name",
            default=""
        )
        
        bpy.types.Scene.cinemon_new_preset_name = bpy.props.StringProperty(
            name="New Preset Name",
            description="Name for new preset to save",
            default="my_preset"
        )
        
        # Register main scene properties for config storage
        bpy.types.Scene.cinemon_config = bpy.props.PointerProperty(
            name="Cinemon Config",
            description="Loaded YAML configuration object",
            type=bpy.types.PropertyGroup  # Will store the actual config object
        )
        
        bpy.types.Scene.cinemon_config_path = bpy.props.StringProperty(
            name="Config Path",
            description="Path to the loaded YAML configuration file",
            default=""
        )
        
        # Collection property will be registered after AnimationPropertyGroup
        
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
        # Unregister UI classes
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
        
        # Clean up scene properties
        if hasattr(bpy.types.Scene, 'cinemon_selected_preset'):
            delattr(bpy.types.Scene, 'cinemon_selected_preset')
        if hasattr(bpy.types.Scene, 'cinemon_current_preset'):
            delattr(bpy.types.Scene, 'cinemon_current_preset')
        if hasattr(bpy.types.Scene, 'cinemon_new_preset_name'):
            delattr(bpy.types.Scene, 'cinemon_new_preset_name')
        if hasattr(bpy.types.Scene, 'cinemon_config'):
            delattr(bpy.types.Scene, 'cinemon_config')
        if hasattr(bpy.types.Scene, 'cinemon_config_path'):
            delattr(bpy.types.Scene, 'cinemon_config_path')
        if hasattr(bpy.types.Scene, 'cinemon_animations'):
            delattr(bpy.types.Scene, 'cinemon_animations')
        
        print("Cinemon VSE Animator addon unregistered")
    except (NameError, AttributeError):
        # bpy not available in test environment
        pass
    
    # Unregister animation panel
    animation_panel.unregister()
    
    # Unregister apply system
    apply_system.unregister()
    
    # Unregister animation UI
    from . import animation_ui
    animation_ui.unregister()
    
    # Unregister layout UI
    layout_ui.unregister()
    
    # Unregister operators
    operators.unregister()


# For development/testing
if __name__ == "__main__":
    register()