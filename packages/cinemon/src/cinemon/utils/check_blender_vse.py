#!/usr/bin/env python3
"""Test Blender VSE configuration with YAML"""

import subprocess
from pathlib import Path

config_file = (
    "/home/wokoziej/Wideo/obs/2025-07-29 20-29-16/animation_config_minimal.yaml"
)
script_file = (
    "/home/wokoziej/dev/setka-monorepo/packages/cinemon/blender_addon/vse_script.py"
)

cmd = [
    "snap",
    "run",
    "blender",
    "--background",
    "--python",
    script_file,
    "--",
    "--config",
    config_file,
]

print(f"Running command: {' '.join(cmd)}")
print("=" * 60)

result = subprocess.run(cmd, capture_output=True, text=True)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print("\nReturn code:", result.returncode)
