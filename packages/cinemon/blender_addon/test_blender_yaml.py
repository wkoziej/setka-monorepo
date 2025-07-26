#!/usr/bin/env python3
# ABOUTME: Test script to verify YAML works in real Blender environment
# ABOUTME: Run this in Blender's Python console to test vendored PyYAML

"""Test vendored YAML in Blender environment.

Usage in Blender:
1. Open Blender
2. Switch to Scripting workspace
3. Open this file and run it (Alt+P)
"""

import sys
from pathlib import Path

# Add addon to path
addon_path = Path(__file__).parent
if str(addon_path) not in sys.path:
    sys.path.insert(0, str(addon_path))

# Test import
try:
    from vendor import yaml
    print("✓ Successfully imported vendored YAML")

    # Test basic functionality
    test_data = """
    preset:
      name: test
    layout:
      type: random
      seed: 42
    """

    parsed = yaml.safe_load(test_data)
    print(f"✓ Parsed YAML: {parsed}")

    # Test dump
    output = yaml.dump(parsed, default_flow_style=False)
    print(f"✓ Dumped YAML:\n{output}")

    print("\n✅ All tests passed! YAML is working in Blender.")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
