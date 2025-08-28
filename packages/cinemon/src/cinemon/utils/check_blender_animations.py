#!/usr/bin/env python3
# ABOUTME: Utility script to verify animations in Blender VSE projects
# ABOUTME: Checks FCurves, keyframes, and strip transforms in .blend files

"""Sprawdza animacje w pliku .blend - FCurves są przechowywane w Scene.animation_data"""

import argparse
import json
import subprocess
from pathlib import Path

BLENDER_CHECK_SCRIPT = '''
import bpy
import json

def check_vse_animations():
    """Sprawdza animacje VSE w pliku Blender."""
    result = {
        "has_animations": False,
        "total_keyframes": 0,
        "animated_strips": [],
        "strip_count": 0,
        "layout_applied": False,
        "config_path": None,
        "config_exists": False
    }

    # Sprawdź cinemon_config_path w scenie
    scene = bpy.context.scene
    config_path = getattr(scene, "cinemon_config_path", "")
    if config_path:
        result["config_path"] = config_path
        # Sprawdź czy plik istnieje
        from pathlib import Path
        result["config_exists"] = Path(config_path).exists()
    else:
        result["config_path"] = "NOT_SET"

    # Sprawdź czy są jakieś akcje
    if bpy.data.actions:
        for action in bpy.data.actions:
            if action.fcurves:
                result["has_animations"] = True
                break

    # Sprawdź animacje na poziomie sceny (tu są animacje VSE!)
    if bpy.context.scene.animation_data and bpy.context.scene.animation_data.action:
        action = bpy.context.scene.animation_data.action

        # Znajdź FCurves dla VSE
        vse_fcurves = [fc for fc in action.fcurves if 'sequence_editor' in fc.data_path]

        for fc in vse_fcurves:
            result["total_keyframes"] += len(fc.keyframe_points)

            # Wyciągnij nazwę paska z data_path
            # Format: sequence_editor.strips_all["NazwaPaska"].property
            if 'strips_all["' in fc.data_path:
                start = fc.data_path.index('strips_all["') + len('strips_all["')
                end = fc.data_path.index('"]', start)
                strip_name = fc.data_path[start:end]

                # Znajdź lub dodaj strip do listy
                strip_entry = next((s for s in result["animated_strips"] if s["name"] == strip_name), None)
                if not strip_entry:
                    strip_entry = {"name": strip_name, "properties": [], "keyframe_count": 0}
                    result["animated_strips"].append(strip_entry)

                # Wyciągnij nazwę właściwości
                prop_start = fc.data_path.rfind('.') + 1
                property_name = fc.data_path[prop_start:]

                if property_name not in strip_entry["properties"]:
                    strip_entry["properties"].append(property_name)
                strip_entry["keyframe_count"] += len(fc.keyframe_points)

    # Sprawdź layout (pozycje i skale pasków)
    if bpy.context.scene.sequence_editor:
        strips = bpy.context.scene.sequence_editor.sequences_all
        result["strip_count"] = len([s for s in strips if s.type in ['MOVIE', 'IMAGE']])

        # Sprawdź czy layout został zastosowany (różne pozycje/skale)
        transforms = []
        for strip in strips:
            if hasattr(strip, 'transform'):
                transforms.append({
                    "scale_x": strip.transform.scale_x,
                    "scale_y": strip.transform.scale_y,
                    "offset_x": strip.transform.offset_x,
                    "offset_y": strip.transform.offset_y
                })

        # Jeśli są różne transformacje, layout został zastosowany
        if transforms and len(set(str(t) for t in transforms)) > 1:
            result["layout_applied"] = True

    print("CHECK_RESULT_START")
    print(json.dumps(result, indent=2))
    print("CHECK_RESULT_END")

check_vse_animations()
'''


def check_blender_file(blend_file: Path) -> dict:
    """
    Sprawdza animacje w pliku .blend.

    Args:
        blend_file: Ścieżka do pliku .blend

    Returns:
        dict: Informacje o animacjach
    """
    # Zapisz skrypt tymczasowy
    temp_script = Path("/tmp/check_vse_animations.py")
    temp_script.write_text(BLENDER_CHECK_SCRIPT)

    # Uruchom Blender
    cmd = [
        "snap",
        "run",
        "blender",
        str(blend_file),
        "--background",
        "--python",
        str(temp_script),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        # Parsuj wynik
        output = result.stdout
        if "CHECK_RESULT_START" in output and "CHECK_RESULT_END" in output:
            start = output.index("CHECK_RESULT_START") + len("CHECK_RESULT_START")
            end = output.index("CHECK_RESULT_END")
            json_str = output[start:end].strip()
            return json.loads(json_str)
        else:
            print("Nie znaleziono danych w outputcie Blendera")
            return None

    except subprocess.TimeoutExpired:
        print("Timeout podczas sprawdzania")
        return None
    except Exception as e:
        print(f"Błąd: {e}")
        return None


def print_animation_report(data: dict, blend_file: Path):
    """Wyświetla raport o animacjach."""
    print(f"\n{'=' * 60}")
    print("📊 ANALIZA ANIMACJI VSE")
    print(f"{'=' * 60}")
    print(f"📁 Plik: {blend_file.name}")
    print(f"📦 Liczba pasków wideo: {data['strip_count']}")
    print(f"🎨 Layout zastosowany: {'TAK' if data['layout_applied'] else 'NIE'}")
    print(f"🎬 Całkowita liczba klatek kluczowych: {data['total_keyframes']}")
    print(f"✅ Animacje obecne: {'TAK' if data['has_animations'] else 'NIE'}")

    # Config path info
    config_status = "NIE USTAWIONA"
    if data.get("config_path") and data["config_path"] != "NOT_SET":
        if data.get("config_exists"):
            config_status = f"✅ {data['config_path']}"
        else:
            config_status = f"❌ {data['config_path']} (nie istnieje)"

    print(f"⚙️  Ścieżka konfiguracji: {config_status}")

    if data["animated_strips"]:
        print(f"\n🎭 Animowane paski ({len(data['animated_strips'])}):")
        for strip in data["animated_strips"]:
            print(f"\n  📹 {strip['name']}")
            print(f"     Klatki kluczowe: {strip['keyframe_count']}")
            print(f"     Animowane właściwości: {', '.join(strip['properties'])}")
    else:
        print("\n⚠️  Brak animowanych pasków")

    print(f"\n{'=' * 60}\n")


def main():
    """Główna funkcja."""
    parser = argparse.ArgumentParser(description="Sprawdź animacje w pliku Blender VSE")
    parser.add_argument(
        "blend_file",
        nargs="?",
        default="/home/wokoziej/Wideo/obs/2025-07-29 20-29-16/blender/2025-07-29 20-29-16.blend",
        help="Ścieżka do pliku .blend (domyślnie: przykładowy plik)",
    )

    args = parser.parse_args()
    blend_file = Path(args.blend_file)

    if not blend_file.exists():
        print(f"❌ Plik nie istnieje: {blend_file}")
        return 1

    # Sprawdź animacje
    data = check_blender_file(blend_file)

    if data:
        print_animation_report(data, blend_file)
        return 0
    else:
        print("❌ Nie udało się sprawdzić animacji")
        return 1


if __name__ == "__main__":
    exit(main())
