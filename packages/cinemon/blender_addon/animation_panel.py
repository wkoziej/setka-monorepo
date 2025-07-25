# ABOUTME: Dynamic animation panel that shows animations for currently active strip in VSE
# ABOUTME: Context-aware UI that updates based on strip selection and manages per-strip animations

"""Dynamic animation panel for context-aware strip animations."""

from typing import Any, Dict

try:
    import bpy
    from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        IntProperty,
        StringProperty,
    )
    from bpy.types import CollectionProperty, Panel, PropertyGroup
except ImportError:
    # For testing without Blender
    class Panel:
        pass

    class PropertyGroup:
        pass

    def CollectionProperty(**kwargs):
        return []

    def StringProperty(**kwargs):
        return kwargs.get('default', '')

    def FloatProperty(**kwargs):
        return kwargs.get('default', 0.0)

    def BoolProperty(**kwargs):
        return kwargs.get('default', False)

    def EnumProperty(**kwargs):
        return kwargs.get('default', '')

    def IntProperty(**kwargs):
        return kwargs.get('default', 0)

try:
    from .animation_ui import AnimationPropertyGroup, AnimationUIManager
    from .apply_system import ApplyUIManager
    from .strip_context import get_strip_context_manager
except ImportError:
    # For direct module execution/testing
    from apply_system import ApplyUIManager
    from strip_context import get_strip_context_manager


class CINEMON_PT_active_strip_animations(Panel):
    """Panel showing animations for currently active strip."""

    bl_label = "Active Strip Animations"
    bl_idname = "CINEMON_PT_active_strip_animations"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Cinemon"
    bl_parent_id = "CINEMON_PT_main_panel"

    def draw(self, context):
        """Draw the active strip animations panel."""
        layout = self.layout

        try:
            # Get current active strip
            manager = get_strip_context_manager()
            active_strip_name = manager.get_active_strip_name()

            # Debug info
            print(f"DEBUG Animation Panel: active_strip_name = '{active_strip_name}'")

            if not active_strip_name:
                layout.label(text="No strip selected", icon='INFO')
                layout.label(text="Select a strip in timeline to edit animations")
                return

            # Show active strip name
            layout.label(text=f"Strip: {active_strip_name}", icon='SEQUENCE')
            layout.separator()

            # Get animations for active strip
            animations = manager.get_active_strip_animations()
            print(f"DEBUG Animation Panel: Strip '{active_strip_name}' has {len(animations)} animations")

            # Debug: print loaded config
            if hasattr(manager, 'config') and 'strip_animations' in manager.config:
                print(f"DEBUG Animation Panel: Available strips in config: {list(manager.config['strip_animations'].keys())}")
            else:
                print("DEBUG Animation Panel: No strip_animations in config or no config loaded")

            if not animations:
                layout.label(text="No animations", icon='X')
            else:
                # Show existing animations
                for i, animation in enumerate(animations):
                    self.draw_animation_item(layout, animation, i)

            layout.separator()

            # Add new animation section
            self.draw_add_animation_section(layout)

            layout.separator()

            # Apply/Discard changes section
            apply_ui = ApplyUIManager()
            apply_ui.draw_apply_status(layout)

        except Exception as e:
            layout.label(text=f"Error: {e}", icon='ERROR')

    def draw_animation_item(self, layout, animation: Dict[str, Any], index: int):
        """Draw single animation item with controls."""
        try:
            # Animation box
            box = layout.box()

            # Header row with type and enabled checkbox
            header = box.row()

            # Animation type and trigger
            anim_type = animation.get('type', 'unknown')
            trigger = animation.get('trigger', 'unknown')
            header.label(text=f"{anim_type.title()} ({trigger})", icon='ANIM')

            # Remove button
            remove_op = header.operator("cinemon.remove_animation", text="", icon='X')
            remove_op.animation_index = index

            # Parameters section
            self.draw_animation_parameters(box, animation, index)

        except Exception as e:
            layout.label(text=f"Animation error: {e}", icon='ERROR')

    def draw_animation_parameters(self, layout, animation: Dict[str, Any], index: int):
        """Draw editable parameters for animation."""
        try:
            anim_type = animation.get('type', '')

            # Common parameters
            if 'intensity' in animation:
                row = layout.row()
                row.label(text="Intensity:")
                intensity_op = row.operator("cinemon.update_animation_param", text=f"{animation['intensity']:.2f}")
                intensity_op.animation_index = index
                intensity_op.param_name = "intensity"
                intensity_op.param_value = animation['intensity']

            # Type-specific parameters
            # Duration frames for animations that support it
            if anim_type in ['scale', 'rotation', 'brightness_flicker', 'desaturate_pulse', 'contrast_flash'] and 'duration_frames' in animation:
                row = layout.row()
                row.label(text="Duration:")
                duration_op = row.operator("cinemon.update_animation_param", text=f"{animation['duration_frames']:.0f} frames")
                duration_op.animation_index = index
                duration_op.param_name = "duration_frames"
                duration_op.param_value = animation['duration_frames']

            elif anim_type == 'shake' and 'return_frames' in animation:
                row = layout.row()
                row.label(text="Return:")
                return_op = row.operator("cinemon.update_animation_param", text=f"{animation['return_frames']:.0f} frames")
                return_op.animation_index = index
                return_op.param_name = "return_frames"
                return_op.param_value = animation['return_frames']

            elif anim_type == 'rotation' and 'degrees' in animation:
                row = layout.row()
                row.label(text="Degrees:")
                degrees_op = row.operator("cinemon.update_animation_param", text=f"{animation['degrees']:.1f}°")
                degrees_op.animation_index = index
                degrees_op.param_name = "degrees"
                degrees_op.param_value = animation['degrees']

            elif anim_type == 'vintage_color':
                if 'sepia_amount' in animation:
                    row = layout.row()
                    row.label(text="Sepia:")
                    sepia_op = row.operator("cinemon.update_animation_param", text=f"{animation['sepia_amount']:.2f}")
                    sepia_op.animation_index = index
                    sepia_op.param_name = "sepia_amount"
                    sepia_op.param_value = animation['sepia_amount']

                if 'contrast_boost' in animation:
                    row = layout.row()
                    row.label(text="Contrast:")
                    contrast_op = row.operator("cinemon.update_animation_param", text=f"{animation['contrast_boost']:.2f}")
                    contrast_op.animation_index = index
                    contrast_op.param_name = "contrast_boost"
                    contrast_op.param_value = animation['contrast_boost']

                if 'grain_intensity' in animation:
                    row = layout.row()
                    row.label(text="Grain:")
                    grain_op = row.operator("cinemon.update_animation_param", text=f"{animation['grain_intensity']:.2f}")
                    grain_op.animation_index = index
                    grain_op.param_name = "grain_intensity"
                    grain_op.param_value = animation['grain_intensity']

        except Exception as e:
            layout.label(text=f"Parameter error: {e}", icon='ERROR')

    def draw_add_animation_section(self, layout):
        """Draw section for adding new animations."""
        try:
            box = layout.box()
            box.label(text="Add Animation:", icon='PLUS')

            # Animation type dropdown
            row = box.row()
            row.label(text="Type:")
            row.operator_menu_enum("cinemon.add_animation", property="animation_type", text="Select Type")

        except Exception as e:
            layout.label(text=f"Add animation error: {e}", icon='ERROR')


class CINEMON_OT_remove_animation(bpy.types.Operator):
    """Remove animation from active strip."""

    bl_idname = "cinemon.remove_animation"
    bl_label = "Remove Animation"
    bl_description = "Remove this animation from the active strip"
    bl_options = {'REGISTER', 'UNDO'}

    animation_index: IntProperty(
        name="Animation Index",
        description="Index of animation to remove"
    )

    def execute(self, context):
        """Execute remove animation."""
        try:
            manager = get_strip_context_manager()

            if manager.remove_animation_from_active_strip(self.animation_index):
                self.report({'INFO'}, "Animation removed")
            else:
                self.report({'WARNING'}, "Failed to remove animation")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error removing animation: {e}")
            return {'CANCELLED'}


class CINEMON_OT_update_animation_param(bpy.types.Operator):
    """Update animation parameter for active strip."""

    bl_idname = "cinemon.update_animation_param"
    bl_label = "Update Parameter"
    bl_description = "Update animation parameter"
    bl_options = {'REGISTER', 'UNDO'}

    animation_index: IntProperty(
        name="Animation Index",
        description="Index of animation to update"
    )

    param_name: StringProperty(
        name="Parameter Name",
        description="Name of parameter to update"
    )

    param_value: FloatProperty(
        name="Parameter Value",
        description="New parameter value"
    )

    # Override for input
    new_value: FloatProperty(
        name="New Value",
        description="Enter new value for parameter"
    )

    def invoke(self, context, event):
        """Invoke with current value."""
        self.new_value = self.param_value
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Draw parameter input dialog."""
        layout = self.layout
        layout.label(text=f"Update {self.param_name}:")
        layout.prop(self, "new_value")

    def execute(self, context):
        """Execute parameter update."""
        try:
            manager = get_strip_context_manager()

            if manager.update_animation_parameter(self.animation_index, self.param_name, self.new_value):
                self.report({'INFO'}, f"Updated {self.param_name} to {self.new_value}")
            else:
                self.report({'WARNING'}, "Failed to update parameter")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error updating parameter: {e}")
            return {'CANCELLED'}


class CINEMON_OT_add_animation(bpy.types.Operator):
    """Add new animation to active strip."""

    bl_idname = "cinemon.add_animation"
    bl_label = "Add Animation"
    bl_description = "Add new animation to the active strip"
    bl_options = {'REGISTER', 'UNDO'}

    animation_type: EnumProperty(
        name="Animation Type",
        description="Type of animation to add",
        items=[
            ('scale', 'Scale', 'Scale animation on beats/bass'),
            ('shake', 'Shake', 'Position shake on energy peaks'),
            ('rotation', 'Rotation', 'Rotation animation on beats'),
            ('jitter', 'Jitter', 'Continuous random position changes'),
            ('brightness_flicker', 'Brightness Flicker', 'Brightness modulation'),
            ('desaturate_pulse', 'Desaturate Pulse', 'Animated color to B&W pulse'),
            ('contrast_flash', 'Contrast Flash', 'Brief contrast increases')
        ],
        default='scale'
    )

    trigger: EnumProperty(
        name="Trigger",
        description="What triggers this animation",
        items=[
            ('beat', 'Beat', 'Trigger on beat events'),
            ('bass', 'Bass', 'Trigger on bass events'),
            ('energy_peaks', 'Energy Peaks', 'Trigger on energy peak events'),
            ('one_time', 'One Time', 'Apply once at start'),
            ('continuous', 'Continuous', 'Apply continuously')
        ],
        default='beat'
    )

    def invoke(self, context, event):
        """Invoke with trigger selection."""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Draw add animation dialog."""
        layout = self.layout
        layout.prop(self, "animation_type")
        layout.prop(self, "trigger")

    def execute(self, context):
        """Execute add animation."""
        try:
            manager = get_strip_context_manager()

            # Create default animation
            new_animation = manager.create_default_animation(self.animation_type, self.trigger)

            if manager.add_animation_to_active_strip(new_animation):
                self.report({'INFO'}, f"Added {self.animation_type} animation")
            else:
                self.report({'WARNING'}, "Failed to add animation - no active strip")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error adding animation: {e}")
            return {'CANCELLED'}


# Registration
classes = [
    CINEMON_PT_active_strip_animations,
    CINEMON_OT_remove_animation,
    CINEMON_OT_update_animation_param,
    CINEMON_OT_add_animation
]


def register():
    """Register animation panel classes."""
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
        print("Animation panel registered successfully")
    except Exception as e:
        print(f"Animation panel registration error: {e}")


def unregister():
    """Unregister animation panel classes."""
    try:
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
        print("Animation panel unregistered")
    except Exception as e:
        print(f"Animation panel unregistration error: {e}")


if __name__ == "__main__":
    register()
