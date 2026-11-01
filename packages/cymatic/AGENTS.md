# AGENTS.md — cymatic

Kanon faktów dla agentów specyficznych dla pakietu `cymatic`. Fakty ogólnomonorepowe
(workspace, komendy `uv`, layout nagrania) żyją w root `../../AGENTS.md`. `CLAUDE.md` to stub.

## 3D Visualization (cymatic)

The cymatic package drives a Blender Geometry Nodes 3D audio visualizer from beatrix analysis. The package is **split in two** because the in-Blender code runs under Blender's bundled Python (numpy yes, no PyYAML):

- **Host-side** `packages/cymatic/src/cymatic/` (pure numpy, no `bpy`): `config.py` (`VisualizerConfig`, `PresetParams`), `analysis_loader.py` (`load_analysis`), `normalization.py` (p99 band normalization, envelope precompute), `runner.py` (`CymaticRunner`), `cli.py` (`cymatic-render`), `sync_verification.py`, `brief.py` (`cymatic-structure-brief`: per-stem activity + master energy → JSON/markdown/ASS brief + heatmap PNG for clip authoring; matplotlib imported lazily).
- **In-Blender** `packages/cymatic/blender_script/` (`import bpy`, NOT shipped in the wheel): `build_scene.py` (entry executed by Blender), `data_object.py`, `gn_sampler.py`, `presets/` (`hybrid_v1.py`).

Key patterns:

- **Audio data bridge ("most B")**: `data_object.build_data_object(name, dt, channels)` bakes audio into a hidden mesh where **X = time** (`arange(N)*dt`) and each channel is a FLOAT/POINT attribute (`bass_n`, `mid_n`, `high_n`, `beat_env`, `peak_env`). Geometry Nodes sample it via `Scene Time → DIVIDE by dt → FLOOR → Sample Index` against that object. `gn_sampler.build_sampler_group(name, dt, data_obj, channels)` builds a reusable sampler group exposing those channels.
- **`dt` is per-track, never hardcode**: `dt = times[1] - times[0]` from the analysis JSON (host-side in `load_analysis`). It must reach every `DIVIDE` node in the GN graphs, or audio desyncs.
- **Preset pattern**: a preset is a module exposing `build_preset_scene(analysis, data_obj, sampler_group, preset_params, fps, resolution, ...)` (see `presets/hybrid_v1.py`); the in-package preset is dispatched by `build_scene.py`. `PresetParams` is the only surface authoring should manipulate to keep builds deterministic.
- **Headless render**: `runner.py` invokes `snap run blender --background --python build_scene.py -- --config <json>`, renders PNG frames, then `ffmpeg`-muxes them (this Blender 5.1 build has no internal video encoder). Drivers require `--enable-autoexec`. Post-fx (bloom/vignette/grade) is done in the ffmpeg `-filter_complex` pass, NOT in the Blender compositor (`format=rgb24` MUST come after `blend`).
- **Per-track manifest**: per-stem analyses are discovered via `setka_common.load_analysis_index(recording_dir)` (`.master()`, `.stems()`, `entry.resolved_analysis_path()`); select by the `analysis` field, never by deriving `<stem>_analysis.json`. The package CLI/`build_scene.py` currently consumes a single analysis; multi-stem orchestration (one data-object per stem) is done ad-hoc during MCP authoring, not yet wired into the CLI.
- **Bespoke looks live in the recording's `.blend`, not the repo**: rich scenes (grove, mosaic, multistem, rest-in-peace) are authored live via the Blender MCP bridge (`ahujasid/blender-mcp`, socket `localhost:9876`, "Connect to Claude" in the N panel) and saved to `<recording>/blender/*.blend`. They reuse the host-side helpers (`load_analysis`, `build_data_object`, `gn_sampler`) inside the MCP session. The MCP bridge is for authoring/design; production rendering is headless. Freezing a bespoke look into a parametric in-package preset is separate, planned work.

Key files:
- `cymatic/blender_script/build_scene.py` - Main Blender script (executed by Blender)
- `cymatic/blender_script/data_object.py` - Audio data bridge (mesh with time-indexed channel attributes)
- `cymatic/blender_script/gn_sampler.py` - Reusable Geometry Nodes sampler group
- `cymatic/blender_script/presets/hybrid_v1.py` - Reference preset (`build_preset_scene`)
- `cymatic/src/cymatic/{analysis_loader,config,runner,cli}.py` - Host-side load/config/render/CLI

> Blender 5.1 GN gotchas (sockets named `"Geometry"` not `"Mesh"`, manual Group Input/Output after `node_groups.new`, Action 2.0 has no `action.fcurves`, `interface.new_socket` over `inputs/outputs`) are documented in the cymatic plans and agent memory.
