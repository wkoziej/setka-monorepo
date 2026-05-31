# ABOUTME: In-Blender entry point — parses --config, builds the full GN scene.
# ABOUTME: config -> load_analysis -> data_object -> sampler -> hybrid_v1 preset.

"""Parametric Blender script for the cymatic 3D audio visualizer (Unit 8).

Executed inside Blender:
    blender --background --python build_scene.py -- --config <config.json>

Orchestration:
  1. parse ``--config`` from ``sys.argv`` (after the ``--`` separator),
  2. load the ``VisualizerConfig``,
  3. load + normalize the beatrix analysis (host-side pure-numpy modules,
     reached by injecting the package ``src/`` onto ``sys.path`` — Blender's
     bundled python ships numpy),
  4. build the data-object mesh (Unit 6),
  5. build the GN time-sampler node group (Unit 7),
  6. assemble the hybrid_v1 visual preset / scene (Unit 8).

Headless rendering to ``blender/render/<name>.mp4`` is wired by the host-side
runner (Unit 9); this script only builds the scene.

``main() -> int`` returns 0 on success. ``bpy`` is guarded so the module can be
imported (and ``main`` reasoned about) outside Blender for tests.
"""

import sys
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None

# --- import path wiring -------------------------------------------------------
# Sibling in-Blender modules (data_object, gn_sampler, presets/) live next to
# this file. The host-side pure-numpy modules (config, analysis_loader,
# normalization) live under the package ``src/`` and are NOT on Blender's path,
# so inject both. Blender's bundled python provides numpy.
_script_dir = Path(__file__).parent
_src_dir = _script_dir.parent / "src"
# Sibling workspace packages cymatic depends on (beatrix, setka-common) are not
# on Blender's bundled-python path either; inject their src/ dirs too so the
# host-side modules import cleanly inside headless Blender.
_packages_dir = _script_dir.parent.parent
_sibling_srcs = [
    str(_packages_dir / "beatrix" / "src"),
    str(_packages_dir / "common" / "src"),
]
for _p in (str(_script_dir), str(_src_dir), *_sibling_srcs):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# In-Blender builders (siblings).
from data_object import build_data_object  # noqa: E402
from gn_sampler import DEFAULT_CHANNELS, build_sampler_group  # noqa: E402
from presets import build_preset_scene  # noqa: E402

# Host-side pure-numpy modules (package src/, numpy-only — no bpy).
from cymatic.analysis_loader import load_analysis  # noqa: E402
from cymatic.config import VisualizerConfig  # noqa: E402


def parse_config_path(argv=None):
    """Find the ``--config <path>`` argument in argv.

    Mirrors cinemon's vse_script.py: scans for the ``--config`` flag and
    returns the following token.

    Args:
        argv: argument list (defaults to ``sys.argv``).

    Returns:
        str: path to the config file.

    Raises:
        ValueError: if no ``--config`` argument is present.
    """
    if argv is None:
        argv = sys.argv

    for i, arg in enumerate(argv):
        if arg == "--config" and i + 1 < len(argv):
            return argv[i + 1]

    raise ValueError("No config file specified. Use --config <path> argument.")


def main(argv=None) -> int:
    """Build the visualizer scene from the config.

    Returns:
        int: exit code (0 on success, non-zero on error).
    """
    try:
        config_path = parse_config_path(argv)
    except ValueError as exc:
        print(f"cymatic build_scene: {exc}")
        return 1

    config = VisualizerConfig.from_json(Path(config_path).read_text())

    # 1. host-side load + normalize (pure numpy, no bpy).
    analysis = load_analysis(config)

    # 2. data-object: numpy channels -> mesh + FLOAT/POINT attributes (Unit 6).
    channels = {
        "bass_n": analysis.bass,
        "mid_n": analysis.mid,
        "high_n": analysis.high,
        "beat_env": analysis.beat_env,
        "peak_env": analysis.peak_env,
    }
    data_obj = build_data_object("audio_data", analysis.dt, channels)

    # 3. GN sampler node group reading the data-object by scene time (Unit 7).
    sampler_group = build_sampler_group(
        "cymatic_sampler", analysis.dt, data_obj, channels=DEFAULT_CHANNELS
    )

    # 4. hybrid_v1 preset: rings + core + camera + sun + world + render (Unit 8).
    build_preset_scene(
        analysis,
        data_obj,
        sampler_group,
        config.preset,
        fps=config.fps,
        resolution=config.resolution,
    )

    # 5. optional headless render of the PNG frame sequence (Unit 9 mux seam).
    # When the runner sets config.frames_dir, render the animation to PNG frames
    # there; the host-side runner then muxes them + audio to mp4 via ffmpeg
    # (this Blender build has no internal FFMPEG encoder).
    if bpy is not None and config.frames_dir:
        scene = bpy.context.scene
        scene.frame_start = config.frame_start
        scene.frame_end = config.frame_end or int(analysis.duration * config.fps)
        scene.render.image_settings.file_format = "PNG"
        frames_dir = Path(config.frames_dir)
        frames_dir.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(frames_dir / "frame_")
        print(
            f"cymatic build_scene: rendering frames "
            f"{scene.frame_start}-{scene.frame_end} -> {frames_dir}"
        )
        bpy.ops.render.render(animation=True)

    print(f"cymatic build_scene: scene built from {config_path}")
    return 0


def is_running_in_blender() -> bool:
    """True when executed inside Blender (bpy importable)."""
    return bpy is not None


if __name__ == "__main__":
    exit_code = main()
    if not is_running_in_blender():
        sys.exit(exit_code)
