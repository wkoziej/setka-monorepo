#!/usr/bin/env python3
"""Debug import context detection"""

import subprocess
from pathlib import Path

blender_script = '''
import sys
import inspect

def debug_import_context():
    """Debuguj kontekst importu w Blenderze."""
    print("=== DEBUG IMPORT CONTEXT ===")

    # Sprawdź sys.path
    print(f"\\nSys.path (pierwsze 5):")
    for i, path in enumerate(sys.path[:5]):
        print(f"  {i}: {path}")

    # Test funkcji is_running_as_addon()
    def is_running_as_addon():
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_name = frame.f_back.f_globals.get('__name__', '')
            print(f"  caller_name: {caller_name}")
            result = caller_name != "__main__" and "." in caller_name
            print(f"  is_addon: {result}")
            return result
        return False

    print(f"\\n__name__: {__name__}")
    is_addon_result = is_running_as_addon()
    print(f"is_running_as_addon(): {is_addon_result}")

    # Sprawdź czy addon jest załadowany
    try:
        import bpy
        addons = list(bpy.context.preferences.addons.keys())
        print(f"\\nZaładowane addony ({len(addons)}):")
        for addon in addons[:5]:
            print(f"  - {addon}")

        cinemon_loaded = "cinemon_addon" in addons
        print(f"\\ncinemon_addon załadowany: {cinemon_loaded}")

        # Sprawdź bezpośrednio import
        try:
            print("\\nPróba importu animation_panel...")
            import animation_panel
            print("✅ Import animation_panel sukces")
        except ImportError as e:
            print(f"❌ Import animation_panel błąd: {e}")

        # Sprawdź względny import
        try:
            print("\\nPróba importu z addon...")
            from cinemon_addon import animation_panel
            print("✅ Import z cinemon_addon sukces")
        except ImportError as e:
            print(f"❌ Import z cinemon_addon błąd: {e}")

    except Exception as e:
        print(f"Błąd: {e}")
        import traceback
        traceback.print_exc()

debug_import_context()
'''


def debug_import():
    """Debug import context w Blenderze."""
    temp_script = Path("/tmp/debug_import.py")
    temp_script.write_text(blender_script)

    cmd = ["snap", "run", "blender", "--background", "--python", str(temp_script)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(result.stdout)
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)


if __name__ == "__main__":
    debug_import()
