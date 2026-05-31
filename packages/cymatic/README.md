# cymatic

3D audio visualizer for the Setka pipeline. Generates a procedural Geometry
Nodes scene driven by `beatrix` audio analysis and renders it to mp4.

- **Host-side** (`src/cymatic/`): config, analysis loading, normalization, the
  subprocess runner, and the CLI (`cymatic-render`).
- **In-Blender** (`blender_script/`, not installed in the wheel): executed by
  Blender via `--background --python build_scene.py -- --config <file>`.

See `docs/plans/2026-05-30-001-feat-gn-audio-visualizer-plan.md`.
