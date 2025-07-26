# ABOUTME: VSE-specific operators for applying and managing strip animations
# ABOUTME: Handles Apply/Discard operations and regeneration of animations for changed strips

"""VSE operators for Cinemon animation system."""

import traceback
from pathlib import Path
from typing import Any, Dict, List

try:
    import bpy
    from bpy.types import Operator
except ImportError:
    # For testing without Blender
    class Operator:
        pass

    class MockBpy:
        class Utils:
            @staticmethod
            def register_class(cls):
                pass

            @staticmethod
            def unregister_class(cls):
                pass

        utils = Utils()

    bpy = MockBpy()

try:
    from .animation_applicators import apply_animation_to_strip, clear_strip_animations
    from .strip_context import get_strip_context_manager
except ImportError:
    # For direct module execution/testing
    from animation_applicators import apply_animation_to_strip, clear_strip_animations
    from strip_context import get_strip_context_manager


def regenerate_animations_for_strips(
    changed_strips: List[str], config: Dict[str, Any]
) -> None:
    """Regenerate animations only for specified strips."""
    print("\n=== REGENERATE ANIMATIONS CALLED ===")
    print(f"Changed strips: {changed_strips}")
    print(f"Config keys: {list(config.keys())}")

    try:
        # Get current VSE sequences
        if not (
            bpy.context.scene.sequence_editor
            and bpy.context.scene.sequence_editor.sequences
        ):
            print("No sequence editor or sequences found")
            return

        sequences = bpy.context.scene.sequence_editor.sequences
        strip_animations = config.get("strip_animations", {})
        print(f"Strip animations in config: {list(strip_animations.keys())}")
        for strip_name, anims in strip_animations.items():
            print(f"  {strip_name}: {len(anims)} animations")

        # Load audio analysis for events
        audio_events = {}
        fps = 30
        try:
            # Try to get fps from scene
            if bpy.context.scene:
                fps = bpy.context.scene.render.fps

            # Try to load audio analysis from config
            audio_analysis_config = config.get("audio_analysis", {})
            analysis_file = audio_analysis_config.get("file")
            if analysis_file:
                # Try to load audio analysis file with proper path resolution
                analysis_path = Path(analysis_file)
                if not analysis_path.is_absolute():
                    # Try to determine recording directory from scene/project
                    recording_dir = None

                    # Try to get recording directory from scene properties
                    if hasattr(bpy.context.scene, "cinemon_config_path"):
                        config_path = Path(bpy.context.scene.cinemon_config_path)
                        recording_dir = config_path.parent
                    else:
                        # Fallback: try to determine from sequence editor sequences
                        if bpy.context.scene.sequence_editor and sequences:
                            # Look for video files to determine recording directory
                            for seq in sequences:
                                if seq.type == "MOVIE" and hasattr(seq, "filepath"):
                                    video_path = Path(seq.filepath)
                                    # Assume structure: recording_dir/extracted/video.mp4
                                    if video_path.parent.name == "extracted":
                                        recording_dir = video_path.parent.parent
                                        break

                    if recording_dir:
                        # Try multiple locations relative to recording directory
                        test_paths = [
                            recording_dir / analysis_file,
                            recording_dir / "analysis" / analysis_file,
                            recording_dir / "analysis" / Path(analysis_file).name,
                        ]
                        for test_path in test_paths:
                            if test_path.exists():
                                analysis_path = test_path
                                break
                        if not analysis_path.exists():
                            print(
                                f"Audio analysis file not found in recording dir. Tried: {[str(p) for p in test_paths]}"
                            )
                    else:
                        # Try relative to current working directory
                        for base_path in [Path.cwd(), Path.cwd() / "analysis"]:
                            test_path = base_path / analysis_file
                            if test_path.exists():
                                analysis_path = test_path
                                break

                if analysis_path.exists():
                    import json

                    with open(analysis_path, "r") as f:
                        analysis_data = json.load(f)
                    audio_events = analysis_data.get("animation_events", {})
                    print(
                        f"Loaded audio events from {analysis_path}: {list(audio_events.keys())}"
                    )
                else:
                    print(
                        f"Audio analysis file not found: {analysis_file} (resolved to: {analysis_path})"
                    )
        except Exception as e:
            print(f"Failed to load audio analysis: {e}")

        # Find strips that need regeneration
        strips_to_process = []
        all_strip_names = [seq.name for seq in sequences]
        print(f"All strips in VSE: {all_strip_names}")

        for sequence in sequences:
            if sequence.name in changed_strips:
                strips_to_process.append(sequence)
                print(f"  ✓ Found strip '{sequence.name}' in VSE")
            else:
                if sequence.name in strip_animations:
                    print(
                        f"  ⚠ Strip '{sequence.name}' has animations but not in changed_strips!"
                    )

        print(f"DEBUG: changed_strips = {changed_strips}")
        print(f"DEBUG: strip_animations keys = {list(strip_animations.keys())}")
        print(
            f"Regenerating animations for {len(strips_to_process)} strips: {[s.name for s in strips_to_process]}"
        )

        # Apply animations to each strip
        for strip in strips_to_process:
            strip_name = strip.name
            animations = strip_animations.get(strip_name, [])

            print(
                f"DEBUG: Processing strip '{strip_name}' with {len(animations)} animations"
            )

            if animations:
                print(f"Applying {len(animations)} animations to strip '{strip_name}'")
                apply_animation_to_strip(strip, animations, audio_events, fps)
            else:
                print(
                    f"No animations for strip '{strip_name}', clearing existing keyframes"
                )
                clear_strip_animations(strip)

    except Exception as e:
        print(f"Error regenerating animations: {e}")
        traceback.print_exc()


# Old CINEMON_OT_apply_changes removed - unified into apply_all_changes in __init__.py


class CINEMON_OT_discard_changes(Operator):
    """Discard buffered animation changes."""

    bl_idname = "cinemon.discard_changes"
    bl_label = "Discard Changes"
    bl_description = "Discard pending animation changes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Execute discard operation."""
        try:
            manager = get_strip_context_manager()

            if not manager.has_pending_changes():
                self.report({"INFO"}, "No pending changes to discard")
                return {"FINISHED"}

            changed_strips = manager.get_changed_strips()
            manager.discard_changes()

            self.report({"INFO"}, f"Discarded changes for {len(changed_strips)} strips")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to discard changes: {e}")
            return {"CANCELLED"}


class ApplyUIManager:
    """UI manager for Apply system status and controls."""

    def __init__(self):
        """Initialize apply UI manager."""
        pass

    def has_pending_changes(self) -> bool:
        """Check if there are pending changes."""
        manager = get_strip_context_manager()
        return manager.has_pending_changes()

    def get_changed_strips(self) -> List[str]:
        """Get list of strips with pending changes."""
        manager = get_strip_context_manager()
        return manager.get_changed_strips()

    def draw_apply_status(self, layout) -> None:
        """Draw apply status in UI."""
        try:
            if self.has_pending_changes():
                changed_strips = self.get_changed_strips()

                # Show pending changes warning
                box = layout.box()
                box.alert = True
                box.label(
                    text=f"Pending changes: {len(changed_strips)} strips", icon="ERROR"
                )

                # Show changed strip names
                for strip_name in changed_strips:
                    box.label(text=f"  • {strip_name}")

                # Old Apply button removed - unified into apply_all_changes in __init__.py
                # Only keep Discard for now
                box.operator(
                    "cinemon.discard_changes", text="Discard Changes", icon="X"
                )
            else:
                # No pending changes
                layout.label(text="No pending changes", icon="CHECKMARK")

        except Exception as e:
            layout.label(text=f"Error: {e}", icon="ERROR")


# Registration
classes = [CINEMON_OT_discard_changes]


def register():
    """Register VSE operator classes."""
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
        print("VSE operators registered successfully")
    except Exception as e:
        print(f"VSE operators registration error: {e}")


def unregister():
    """Unregister VSE operator classes."""
    try:
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)
        print("VSE operators unregistered")
    except Exception as e:
        print(f"VSE operators unregistration error: {e}")


if __name__ == "__main__":
    register()
