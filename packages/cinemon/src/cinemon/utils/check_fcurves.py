#!/usr/bin/env python3
"""Sprawdza wszystkie FCurves w pliku .blend"""

import subprocess
from pathlib import Path

blender_script = """
import bpy

print("=== ANALIZA FCURVES ===")

# Sprawdź wszystkie akcje
print(f"\\nWszystkie akcje w pliku:")
for action in bpy.data.actions:
    print(f"  Akcja: {action.name}")
    print(f"    FCurves: {len(action.fcurves)}")
    for fc in action.fcurves[:5]:  # Pierwsze 5
        print(f"      - {fc.data_path} [{fc.array_index}]: {len(fc.keyframe_points)} keyframes")

# Sprawdź animacje w sequence_editor
if bpy.context.scene.sequence_editor:
    print(f"\\nAnimacje w VSE:")

    # Sprawdź animacje na poziomie sequence_editor
    if hasattr(bpy.context.scene.sequence_editor, 'animation_data'):
        if bpy.context.scene.sequence_editor.animation_data:
            print("  Sequence Editor ma animation_data!")
            if bpy.context.scene.sequence_editor.animation_data.action:
                action = bpy.context.scene.sequence_editor.animation_data.action
                print(f"    Akcja: {action.name}")
                print(f"    FCurves: {len(action.fcurves)}")
                for fc in action.fcurves[:10]:
                    print(f"      - {fc.data_path}: {len(fc.keyframe_points)} keyframes")

    # Sprawdź każdy strip
    for strip in bpy.context.scene.sequence_editor.sequences_all:
        if strip.type in ['MOVIE', 'IMAGE']:
            print(f"\\n  Strip: {strip.name}")

            # Sprawdź animation_data na strip
            if hasattr(strip, 'animation_data') and strip.animation_data:
                print(f"    Strip ma animation_data")
                if strip.animation_data.action:
                    print(f"      Akcja: {strip.animation_data.action.name}")

            # Sprawdź transform
            if hasattr(strip, 'transform'):
                print(f"    Transform values: scale=({strip.transform.scale_x:.2f}, {strip.transform.scale_y:.2f})")
                if hasattr(strip.transform, 'animation_data') and strip.transform.animation_data:
                    print(f"    Transform ma animation_data")
                    if strip.transform.animation_data.action:
                        print(f"      Akcja: {strip.transform.animation_data.action.name}")

# Sprawdź Scene animation_data
if bpy.context.scene.animation_data:
    print(f"\\nScene animation_data:")
    if bpy.context.scene.animation_data.action:
        action = bpy.context.scene.animation_data.action
        print(f"  Akcja: {action.name}")
        print(f"  FCurves: {len(action.fcurves)}")

        # Pokaż fcurves związane z VSE
        vse_curves = [fc for fc in action.fcurves if 'sequence_editor' in fc.data_path]
        if vse_curves:
            print(f"  FCurves dla VSE: {len(vse_curves)}")
            for fc in vse_curves[:20]:
                print(f"    - {fc.data_path}: {len(fc.keyframe_points)} keyframes")
"""


def check_fcurves():
    blend_file = (
        "/home/wokoziej/Wideo/obs/2025-07-29 20-29-16/blender/2025-07-29 20-29-16.blend"
    )

    temp_script = Path("/tmp/check_fcurves.py")
    temp_script.write_text(blender_script)

    cmd = [
        "snap",
        "run",
        "blender",
        blend_file,
        "--background",
        "--python",
        str(temp_script),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(result.stdout)
    if result.stderr:
        print("\nBłędy:")
        print(result.stderr)


if __name__ == "__main__":
    check_fcurves()
