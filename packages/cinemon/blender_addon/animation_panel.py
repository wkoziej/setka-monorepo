# ABOUTME: Dynamic animation panel that shows animations for currently active strip in VSE
# ABOUTME: Context-aware UI that updates based on strip selection and manages per-strip animations

"""Dynamic animation panel for context-aware strip animations."""

from typing import Any, Dict, List

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
        return kwargs.get("default", "")

    def FloatProperty(**kwargs):
        return kwargs.get("default", 0.0)

    def BoolProperty(**kwargs):
        return kwargs.get("default", False)

    def EnumProperty(**kwargs):
        return kwargs.get("default", "")

    def IntProperty(**kwargs):
        return kwargs.get("default", 0)


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

            # Show active strip name
            layout.label(text=f"Strip: {active_strip.name}", icon="SEQUENCE")
            layout.separator()

            # Get animations for active strip from stored config
            animations = self.get_strip_animations(context, active_strip.name)
            
            if not animations:
                layout.label(text="No animations", icon="X")
                layout.label(text="Apply a config to add animations", icon="INFO")
            else:
                # Show existing animations
                for i, animation in enumerate(animations):
                    self.draw_animation_item(layout, animation, i)

            layout.separator()

        except Exception as e:
            layout.label(text=f"Error: {e}", icon="ERROR")

    def get_strip_animations(self, context, strip_name: str) -> List[Dict[str, Any]]:
        """Get animations for a specific strip from the loaded config."""
        try:
            # Check if we have a loaded config with strip_animations
            if "cinemon_strip_animations" not in context.scene:
                return []
                
            strip_animations = context.scene["cinemon_strip_animations"]
            if not isinstance(strip_animations, dict):
                return []
                
            # First check for strip-specific animations
            if strip_name in strip_animations:
                return strip_animations[strip_name]
                    
            # Fall back to "all" animations that apply to every strip
            if "all" in strip_animations:
                return strip_animations["all"]
                    
            return []
            
        except Exception as e:
            print(f"Error getting strip animations: {e}")
            return []

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

    def draw_animation_parameters(self, layout, animation: Dict[str, Any], index: int):
        """Draw animation parameters for display."""
        try:
            anim_type = animation.get("type", "")

            # Common parameters
            if "intensity" in animation:
                row = layout.row()
                row.label(text=f"Intensity: {animation['intensity']:.2f}")

            # Type-specific parameters
            if anim_type in ["scale", "rotation", "brightness_flicker"] and "duration_frames" in animation:
                row = layout.row()
                row.label(text=f"Duration: {animation['duration_frames']:.0f} frames")

            elif anim_type == "shake" and "return_frames" in animation:
                row = layout.row()
                row.label(text=f"Return: {animation['return_frames']:.0f} frames")

            elif anim_type == "rotation" and "degrees" in animation:
                row = layout.row()
                row.label(text=f"Degrees: {animation['degrees']:.1f}°")

            elif anim_type == "vintage_color":
                if "sepia_amount" in animation:
                    row = layout.row()
                    row.label(text=f"Sepia: {animation['sepia_amount']:.2f}")

                if "contrast_boost" in animation:
                    row = layout.row()
                    row.label(text=f"Contrast: {animation['contrast_boost']:.2f}")

            elif anim_type == "film_grain" and "intensity" in animation:
                row = layout.row()
                row.label(text=f"Grain intensity: {animation.get('intensity', 0.15):.2f}")
                
            elif anim_type == "jitter" and "intensity" in animation:
                row = layout.row()
                row.label(text=f"Jitter intensity: {animation.get('intensity', 1.0):.1f}")
                
            elif anim_type == "black_white" and "intensity" in animation:
                row = layout.row()
                row.label(text=f"B&W amount: {animation.get('intensity', 0.8):.2f}")

        except Exception as e:
            layout.label(text=f"Parameter error: {e}", icon="ERROR")


# Registration
classes = [
    CINEMON_PT_active_strip_animations,
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