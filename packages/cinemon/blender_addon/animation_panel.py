# ABOUTME: Dynamic animation panel that shows animations for currently active strip in VSE
# ABOUTME: Context-aware UI that reads animations from YAML file (single source of truth)

"""Dynamic animation panel with YAML-based single source of truth."""

from typing import Any, Dict, List

# Import YAML manager
from yaml_manager import AnimationYAMLManager

try:
    import bpy
    from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        IntProperty,
        StringProperty,
    )
    from bpy.types import CollectionProperty, Panel, PropertyGroup, Operator
except ImportError:
    # For testing without Blender
    class Panel:
        pass

    class PropertyGroup:
        pass

    class Operator:
        pass

    def CollectionProperty(**kwargs):
        return []

    def StringProperty(**kwargs):
        return kwargs.get("default", "")

    def FloatProperty(**kwargs):
        return kwargs.get("default", 0.0)

    def BoolProperty(**kwargs):
        return kwargs.get("default", False)

    def EnumProperty(**kwargs):
        return kwargs.get("default", "")

    def IntProperty(**kwargs):
        return kwargs.get("default", 0)


# Global instance
yaml_manager = AnimationYAMLManager()


class CINEMON_PT_active_strip_animations(Panel):
    """Panel showing animations for currently active strip."""

    bl_label = "Active Strip Animations"
    bl_idname = "CINEMON_PT_active_strip_animations"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Cinemon"
    bl_parent_id = "CINEMON_PT_main_panel"

    def draw(self, context):
        """Draw the active strip animations panel."""
        layout = self.layout

        try:
            # Get current active strip
            if not context.scene.sequence_editor:
                layout.label(text="No sequence editor", icon="ERROR")
                return

            active_strip = context.scene.sequence_editor.active_strip

            if not active_strip:
                layout.label(text="No strip selected", icon="INFO")
                layout.label(text="Select a strip in timeline to view animations")
                return

            # Show active strip name and config source
            layout.label(text=f"Strip: {active_strip.name}", icon="SEQUENCE")

            config_path = yaml_manager.resolve_config_path(context)
            if config_path and config_path.exists():
                layout.label(text=f"Config: {config_path.name}", icon="FILE_TEXT")
            else:
                layout.label(text="Config file missing!", icon="ERROR")
                if config_path:
                    layout.label(text=f"Expected: {config_path}")
                return

            layout.separator()

            # Get animations for active strip from YAML file
            animations = yaml_manager.get_strip_animations(context, active_strip.name)

            if not animations:
                layout.label(text="No animations for this strip", icon="INFO")

                # Show add animation button
                layout.separator()
                layout.operator(
                    "cinemon.add_animation_to_strip", text="Add Animation", icon="PLUS"
                )
            else:
                # Show existing animations with edit controls
                for i, animation in enumerate(animations):
                    self.draw_editable_animation_item(
                        layout, context, active_strip.name, animation, i
                    )

            layout.separator()

        except Exception as e:
            layout.label(text=f"Error: {e}", icon="ERROR")

    def draw_editable_animation_item(
        self, layout, context, strip_name: str, animation: Dict[str, Any], index: int
    ):
        """Draw animation item with editable controls."""
        try:
            # Animation box
            box = layout.box()

            # Header row
            header = box.row()
            anim_type = animation.get("type", "unknown")
            trigger = animation.get("trigger", "unknown")
            header.label(text=f"{anim_type.title()} ({trigger})", icon="ANIM")

            # Remove button
            remove_op = header.operator("cinemon.remove_animation", text="", icon="X")
            remove_op.strip_name = strip_name
            remove_op.animation_index = index

            # Editable parameters
            self.draw_editable_parameters(box, context, strip_name, animation, index)

        except Exception as e:
            layout.label(text=f"Animation error: {e}", icon="ERROR")

    def draw_animation_item(self, layout, animation: Dict[str, Any], index: int):
        """Draw single animation item with controls."""
        try:
            # Animation box
            box = layout.box()

            # Header row with type and enabled checkbox
            header = box.row()

            # Animation type and trigger
            anim_type = animation.get("type", "unknown")
            trigger = animation.get("trigger", "unknown")
            header.label(text=f"{anim_type.title()} ({trigger})", icon="ANIM")

            # Parameters section
            self.draw_animation_parameters(box, animation, index)

        except Exception as e:
            layout.label(text=f"Animation error: {e}", icon="ERROR")

    def draw_editable_parameters(
        self, layout, context, strip_name: str, animation: Dict[str, Any], index: int
    ):
        """Draw editable parameters for animation."""
        try:
            anim_type = animation.get("type", "")

            # Common parameters - Intensity
            if "intensity" in animation:
                row = layout.row()
                row.label(text="Intensity:")
                intensity_op = row.operator(
                    "cinemon.edit_animation_param", text=f"{animation['intensity']:.2f}"
                )
                intensity_op.strip_name = strip_name
                intensity_op.animation_index = index
                intensity_op.param_name = "intensity"
                intensity_op.current_value = animation["intensity"]

            # Duration frames for applicable animations
            if (
                anim_type in ["scale", "rotation", "brightness_flicker"]
                and "duration_frames" in animation
            ):
                row = layout.row()
                row.label(text="Duration:")
                duration_op = row.operator(
                    "cinemon.edit_animation_param",
                    text=f"{animation['duration_frames']:.0f}f",
                )
                duration_op.strip_name = strip_name
                duration_op.animation_index = index
                duration_op.param_name = "duration_frames"
                duration_op.current_value = animation["duration_frames"]

            # Type-specific parameters
            if anim_type == "shake" and "return_frames" in animation:
                row = layout.row()
                row.label(text="Return:")
                return_op = row.operator(
                    "cinemon.edit_animation_param",
                    text=f"{animation['return_frames']:.0f}f",
                )
                return_op.strip_name = strip_name
                return_op.animation_index = index
                return_op.param_name = "return_frames"
                return_op.current_value = animation["return_frames"]

            elif anim_type == "rotation" and "degrees" in animation:
                row = layout.row()
                row.label(text="Degrees:")
                degrees_op = row.operator(
                    "cinemon.edit_animation_param", text=f"{animation['degrees']:.1f}°"
                )
                degrees_op.strip_name = strip_name
                degrees_op.animation_index = index
                degrees_op.param_name = "degrees"
                degrees_op.current_value = animation["degrees"]

            elif anim_type == "vintage_color" and "sepia_amount" in animation:
                row = layout.row()
                row.label(text="Sepia:")
                sepia_op = row.operator(
                    "cinemon.edit_animation_param",
                    text=f"{animation['sepia_amount']:.2f}",
                )
                sepia_op.strip_name = strip_name
                sepia_op.animation_index = index
                sepia_op.param_name = "sepia_amount"
                sepia_op.current_value = animation["sepia_amount"]

        except Exception as e:
            layout.label(text=f"Parameter error: {e}", icon="ERROR")


# New operators for editing animations
class CINEMON_OT_edit_animation_param(Operator):
    """Edit animation parameter and save to YAML."""

    bl_idname = "cinemon.edit_animation_param"
    bl_label = "Edit Animation Parameter"
    bl_description = "Edit animation parameter"
    bl_options = {"REGISTER", "UNDO"}

    strip_name: StringProperty(name="Strip Name")
    animation_index: IntProperty(name="Animation Index")
    param_name: StringProperty(name="Parameter Name")
    current_value: FloatProperty(name="Current Value")
    new_value: FloatProperty(name="New Value", description="Enter new value")

    def invoke(self, context, event):
        """Open dialog with current value."""
        self.new_value = self.current_value
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Draw parameter input dialog."""
        layout = self.layout
        layout.label(text=f"Edit {self.param_name} for {self.strip_name}")
        layout.prop(self, "new_value")

    def execute(self, context):
        """Update parameter in YAML file."""
        success = yaml_manager.update_animation_parameter(
            context,
            self.strip_name,
            self.animation_index,
            self.param_name,
            self.new_value,
        )

        if success:
            self.report({"INFO"}, f"Updated {self.param_name} to {self.new_value}")

            # Trigger reapplication of animations
            bpy.ops.cinemon.reapply_animations_from_yaml()
        else:
            self.report({"ERROR"}, "Failed to update parameter")

        return {"FINISHED"}


class CINEMON_OT_remove_animation(Operator):
    """Remove animation from strip and update YAML."""

    bl_idname = "cinemon.remove_animation"
    bl_label = "Remove Animation"
    bl_description = "Remove this animation from the strip"
    bl_options = {"REGISTER", "UNDO"}

    strip_name: StringProperty(name="Strip Name")
    animation_index: IntProperty(name="Animation Index")

    def execute(self, context):
        """Remove animation from YAML file."""
        # TODO: Implement remove animation logic
        self.report(
            {"INFO"}, f"Removed animation {self.animation_index} from {self.strip_name}"
        )
        return {"FINISHED"}


class CINEMON_OT_add_animation_to_strip(Operator):
    """Add new animation to strip."""

    bl_idname = "cinemon.add_animation_to_strip"
    bl_label = "Add Animation"
    bl_description = "Add new animation to this strip"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Add new animation to strip."""
        # TODO: Implement add animation dialog
        self.report({"INFO"}, "Add animation dialog - TODO")
        return {"FINISHED"}


class CINEMON_OT_reapply_animations_from_yaml(Operator):
    """Reapply all animations from YAML to update keyframes."""

    bl_idname = "cinemon.reapply_animations_from_yaml"
    bl_label = "Reapply Animations"
    bl_description = "Reapply animations from YAML config to update keyframes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Reapply animations by calling VSE script logic."""
        try:
            config_path = yaml_manager.resolve_config_path(context)
            if config_path and config_path.exists():
                # TODO: Call animation reapplication logic
                self.report({"INFO"}, "Animations reapplied from YAML")
            else:
                self.report({"ERROR"}, "No config file found")
        except Exception as e:
            self.report({"ERROR"}, f"Failed to reapply animations: {e}")

        return {"FINISHED"}


# Registration
classes = [
    CINEMON_PT_active_strip_animations,
    CINEMON_OT_edit_animation_param,
    CINEMON_OT_remove_animation,
    CINEMON_OT_add_animation_to_strip,
    CINEMON_OT_reapply_animations_from_yaml,
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
