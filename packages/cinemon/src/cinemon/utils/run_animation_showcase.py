# ABOUTME: Complete showcase script that generates test media and runs cinemon
# ABOUTME: Creates colored squares with animations for testing in Blender

import json
import shutil
import subprocess
import sys
from pathlib import Path


def create_showcase_project(base_dir: Path = None):
    """Create complete showcase project with test media and animations."""

    if base_dir is None:
        base_dir = Path.home() / "Wideo" / "obs" / "animation_showcase"

    base_dir = Path(base_dir)
    print(f"Creating showcase project in: {base_dir}")

    # Clean and create directory
    if base_dir.exists():
        print("Directory exists. Remove it? [y/N]: ", end="")
        if input().lower() == "y":
            shutil.rmtree(base_dir)
        else:
            print("Aborting.")
            return

    base_dir.mkdir(parents=True)
    extracted_dir = base_dir / "extracted"
    analysis_dir = base_dir / "analysis"
    extracted_dir.mkdir()
    analysis_dir.mkdir()

    # 1. Generate test videos using FFmpeg
    print("\n1. Generating test videos...")
    colors = [
        "red",
        "green",
        "blue",
        "yellow",
        "magenta",
        "cyan",
        "orange",
        "purple",
        "teal",
    ]

    for i, color in enumerate(colors):
        video_path = extracted_dir / f"strip_{i}.mp4"

        # Create video with colored background and number
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=640x480:d=30:r=30,drawtext=text='{i}':fontsize=200:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            str(video_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ Created {video_path.name}")
        else:
            print(f"  ✗ Failed to create {video_path.name}: {result.stderr}")

    # 2. Generate simple test audio
    print("\n2. Generating test audio...")
    audio_path = extracted_dir / "test_audio.m4a"

    # Create audio with regular beats using FFmpeg
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=100:duration=30:sample_rate=44100",
        "-af",
        "apulsator=hz=2:mode=sine:amount=1",
        "-c:a",
        "aac",
        str(audio_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("  ✓ Created test_audio.m4a")
    else:
        print(f"  ✗ Failed to create audio: {result.stderr}")

    # 3. Create mock analysis file
    print("\n3. Creating analysis file...")
    analysis = {
        "audio_info": {"duration": 30.0, "sample_rate": 44100, "tempo": 120},
        "animation_events": {
            "beats": [
                float(t) for t in range(0, 30, 1)
            ],  # Every second - simple timestamps
            "energy_peaks": [
                float(t) for t in [2, 6, 10, 14, 18, 22, 26]
            ],  # Every ~4 seconds
            "sections": [
                {"start": 0.0, "end": 10.0, "label": "intro"},
                {"start": 10.0, "end": 20.0, "label": "main"},
                {"start": 20.0, "end": 30.0, "label": "outro"},
            ],
        },
    }

    analysis_path = analysis_dir / "test_audio_analysis.json"
    with open(analysis_path, "w") as f:
        json.dump(analysis, f, indent=2)
    print("  ✓ Created analysis file")

    # Create metadata.json for RecordingStructureManager compatibility
    metadata = {
        "recording_name": "test_showcase",
        "sources": [{"name": f"strip_{i}"} for i in range(9)],
        "duration": 30.0,
    }
    metadata_path = base_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print("  ✓ Created metadata.json")

    # Create dummy OBS recording file for RecordingStructureManager compatibility
    dummy_recording_path = base_dir / "test_showcase.mkv"
    # Create empty file
    dummy_recording_path.touch()
    print("  ✓ Created dummy OBS recording file")

    # 4. Create YAML configuration
    print("\n4. Creating YAML configuration...")
    yaml_content = f"""# Animation showcase configuration
project:
  base_directory: {base_dir}
  fps: 30
  resolution:
    width: 1920
    height: 1080
  video_files:
    - strip_0.mp4
    - strip_1.mp4
    - strip_2.mp4
    - strip_3.mp4
    - strip_4.mp4
    - strip_5.mp4
    - strip_6.mp4
    - strip_7.mp4
    - strip_8.mp4
  main_audio: test_audio.m4a
  output_blend: blender/animation_showcase.blend

audio_analysis:
  file: analysis/test_audio_analysis.json

layout:
  type: grid
  config:
    rows: 3
    cols: 3
    margin: 0.02

strip_animations:
  strip_0.mp4:
    - type: scale
      trigger: beat
      intensity: 0.5
      duration_frames: 5

  strip_1.mp4:
    - type: shake
      trigger: beat
      intensity: 8.0

  strip_2.mp4:
    - type: rotation
      trigger: energy_peaks
      degrees: 15.0

  strip_3.mp4:
    - type: brightness_flicker
      trigger: beat
      intensity: 0.3

  strip_4.mp4:
    - type: scale
      trigger: energy_peaks
      intensity: 0.4
      duration_frames: 8

  strip_5.mp4:
    - type: shake
      trigger: energy_peaks
      intensity: 6.0

  strip_6.mp4:
    - type: rotation
      trigger: beat
      degrees: 10.0

  strip_7.mp4:
    - type: scale
      trigger: beat
      intensity: 0.3
      duration_frames: 4

  strip_8.mp4:
    - type: scale
      trigger: bass
      intensity: 0.3
      duration_frames: 3
    - type: shake
      trigger: beat
      intensity: 4.0
"""

    yaml_path = base_dir / "animation_showcase.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)
    print("  ✓ Created YAML configuration")

    # 5. Run cinemon
    print("\n5. Running cinemon-blend-setup...")
    print("\nYou can now run:")
    print(f"  cinemon-blend-setup {base_dir} --config {yaml_path}")

    if sys.stdout.isatty():  # Only ask if running interactively
        print("\nRun it now? [y/N]: ", end="")
        try:
            response = input()
            if response.lower() == "y":
                cmd = ["cinemon-blend-setup", str(base_dir), "--config", str(yaml_path)]
                subprocess.run(cmd)
        except (KeyboardInterrupt, EOFError):
            print("\nSkipped running cinemon")
    else:
        print("\nSkipping cinemon (non-interactive mode)")

    print(f"\n✓ Showcase project ready in: {base_dir}")
    print("  Open blender/project.blend to see the animations!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create animation showcase project")
    parser.add_argument(
        "--dir",
        type=Path,
        help="Output directory (default: ~/Wideo/obs/animation_showcase)",
    )
    args = parser.parse_args()

    create_showcase_project(args.dir)
