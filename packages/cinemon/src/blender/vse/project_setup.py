"""
ABOUTME: BlenderProjectSetup class - handles Blender VSE project creation and configuration.
ABOUTME: Extracted from BlenderVSEConfigurator to centralize project setup logic.
"""

from typing import Dict
from pathlib import Path

try:
    import bpy
except ImportError:
    # Running outside Blender - provide mock for testing
    bpy = None


class BlenderProjectSetup:
    """Handles Blender VSE project setup including scene, sequencer, and render configuration."""

    def __init__(self, config: Dict):
        """
        Initialize BlenderProjectSetup with configuration.

        Args:
            config: Dictionary with project configuration

        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config
        self._validate_config()

    def _validate_config(self):
        """Validate configuration parameters."""
        fps = self.config.get("fps", 30)
        resolution_x = self.config.get("resolution_x", 1280)
        resolution_y = self.config.get("resolution_y", 720)

        if fps <= 0:
            raise ValueError("FPS must be positive")

        if resolution_x <= 0 or resolution_y <= 0:
            raise ValueError("Resolution must be positive")

    def setup_scene(self) -> bool:
        """
        Setup basic scene configuration.

        Returns:
            bool: True if successful
        """
        try:
            # DON'T use Video_Editing template - it causes problems with strip saving in background mode
            # Load default scene instead
            print("🎬 Loading default scene (avoiding Video_Editing template issues)...")
            bpy.ops.wm.read_factory_settings()
            print("🎬 Default scene loaded")

            # Configure basic scene settings
            scene = bpy.context.scene
            print(f"🎬 Scene: {scene.name}, has sequence_editor: {scene.sequence_editor is not None}")
            scene.render.fps = self.config.get("fps", 30)
            scene.render.resolution_x = self.config.get("resolution_x", 1280)
            scene.render.resolution_y = self.config.get("resolution_y", 720)
            scene.frame_start = 1

            print("✓ Loaded default scene - will manually create sequence editor")

            return True

        except Exception as e:
            print(f"Error setting up scene: {e}")
            return False

    def setup_sequence_editor(self) -> bool:
        """
        Setup sequence editor.

        Returns:
            bool: True if successful
        """
        try:
            # Create sequence editor if it doesn't exist
            if not bpy.context.scene.sequence_editor:
                bpy.context.scene.sequence_editor_create()

            return True

        except Exception as e:
            print(f"Error setting up sequence editor: {e}")
            return False

    def setup_render_settings(self) -> bool:
        """
        Configure render settings for MP4/H.264 output.

        Returns:
            bool: True if successful
        """
        try:
            render = bpy.context.scene.render
            render.image_settings.file_format = "FFMPEG"
            render.ffmpeg.format = "MPEG4"
            render.ffmpeg.codec = "H264"
            render.ffmpeg.constant_rate_factor = "HIGH"

            # Configure audio settings
            render.ffmpeg.audio_codec = "AAC"
            render.ffmpeg.audio_bitrate = 192
            render.ffmpeg.audio_mixrate = 48000

            # Set output path if provided
            render_output = self.config.get("render_output")
            if render_output:
                render.filepath = str(render_output)

            return True

        except Exception as e:
            print(f"Error setting up render settings: {e}")
            return False

    def add_main_audio(self) -> bool:
        """
        Add main audio file to sequence editor.

        Returns:
            bool: True if successful
        """
        main_audio = self.config.get("main_audio")
        if not main_audio:
            return True  # No audio to add is not an error

        try:
            sequencer = bpy.context.scene.sequence_editor
            sequencer.sequences.new_sound(
                name="Main_Audio",
                filepath=str(main_audio),
                channel=1,  # Audio channel 1
                frame_start=1,
            )

            return True

        except Exception as e:
            print(f"Error adding main audio: {e}")
            return False

    def add_video_strips(self) -> bool:
        """
        Add video files to sequence editor.

        Returns:
            bool: True if successful
        """
        video_files = self.config.get("video_files", [])
        if not video_files:
            return True  # No videos to add is not an error

        try:
            sequencer = bpy.context.scene.sequence_editor

            for i, video_file in enumerate(video_files):
                channel = i + 2  # Start from channel 2 (audio is channel 1)
                
                # Use filename (without extension) for clear identification
                strip_name = Path(video_file).stem
                
                print(f"🎬 Adding video strip: {strip_name} from {video_file} to channel {channel}")
                new_strip = sequencer.sequences.new_movie(
                    name=strip_name,
                    filepath=str(video_file),
                    channel=channel,
                    frame_start=1,
                )
                print(f"🎬 Added strip: {new_strip.name if new_strip else 'FAILED'}")

            return True

        except Exception as e:
            print(f"Error adding video strips: {e}")
            return False

    def calculate_timeline_length(self) -> bool:
        """
        Calculate and set timeline length based on longest sequence.

        Returns:
            bool: True if successful
        """
        try:
            sequencer = bpy.context.scene.sequence_editor

            if sequencer.sequences:
                # Find longest sequence
                max_frame_end = max(seq.frame_final_end for seq in sequencer.sequences)
                bpy.context.scene.frame_end = max_frame_end

            return True

        except Exception as e:
            print(f"Error calculating timeline length: {e}")
            return False

    def save_project(self) -> bool:
        """
        Save project to .blend file.

        Returns:
            bool: True if successful
        """
        output_blend = self.config.get("output_blend")
        if not output_blend:
            print("🎬 No output_blend specified - skipping save in project_setup")
            return True  # No save path is not an error

        try:
            # Ensure directory exists
            output_blend.parent.mkdir(parents=True, exist_ok=True)

            # Debug: Check strips before save
            sequencer = bpy.context.scene.sequence_editor
            if sequencer:
                strips_count = len(sequencer.sequences)
                video_strips_count = len([s for s in sequencer.sequences if s.type == 'MOVIE'])
                print(f"🎬 Before save: {strips_count} total sequences, {video_strips_count} video strips")
            else:
                print("🎬 Before save: No sequence editor found")

            # Save project
            bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))

            # Verify file was created
            if not output_blend.exists():
                print(f"Project file was not created: {output_blend}")
                return False

            return True

        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    def setup_project(self) -> bool:
        """
        Run complete project setup process.

        Returns:
            bool: True if all steps successful
        """
        print("=== Setting up Blender VSE project ===")

        steps = [
            ("Scene setup", self.setup_scene),
            ("Sequence editor", self.setup_sequence_editor),
            ("Render settings", self.setup_render_settings),
            ("Main audio", self.add_main_audio),
            ("Video strips", self.add_video_strips),
            ("Timeline length", self.calculate_timeline_length),
            ("Save project", self.save_project),
        ]

        for step_name, step_method in steps:
            print(f"  Running: {step_name}")

            if not step_method():
                print(f"✗ Failed: {step_name}")
                return False

            print(f"✓ Completed: {step_name}")

        print("=== Project setup completed successfully ===")
        return True
