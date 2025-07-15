# Blender Package Migration Specification

## Overview
Create a new package `blender-prep` for all Blender project preparation operations, separating them from the obsession package.

## Package Structure
```
packages/blender-prep/
├── pyproject.toml
├── src/
│   └── blender_prep/
│       ├── __init__.py
│       ├── project_manager.py      # from blender_project.py
│       ├── vse_script.py          # from blender_vse_script.py
│       ├── vse/
│       │   ├── __init__.py
│       │   ├── animation_engine.py
│       │   ├── config.py
│       │   ├── constants.py
│       │   ├── keyframe_helper.py
│       │   ├── layout_manager.py
│       │   ├── project_setup.py
│       │   ├── animators/
│       │   │   ├── __init__.py
│       │   │   ├── beat_switch_animator.py
│       │   │   ├── energy_pulse_animator.py
│       │   │   └── multi_pip_animator.py
│       │   └── effects/
│       │       ├── __init__.py
│       │       └── vintage_film_effects.py
│       └── cli/
│           └── blend_setup.py
└── tests/
    ├── test_project_manager.py
    ├── test_vse_script.py
    ├── test_animation_engine.py
    ├── test_animators.py
    └── test_effects.py
```

## Files to Migrate

### Core Module Files
1. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_project.py` → `packages/blender-prep/src/blender_prep/project_manager.py`
2. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse_script.py` → `packages/blender-prep/src/blender_prep/vse_script.py`

### VSE Submodule Files
3. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/__init__.py` → `packages/blender-prep/src/blender_prep/vse/__init__.py`
4. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/blender_animation_engine.py` → `packages/blender-prep/src/blender_prep/vse/animation_engine.py`
5. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/config.py` → `packages/blender-prep/src/blender_prep/vse/config.py`
6. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/constants.py` → `packages/blender-prep/src/blender_prep/vse/constants.py`
7. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/keyframe_helper.py` → `packages/blender-prep/src/blender_prep/vse/keyframe_helper.py`
8. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/layout_manager.py` → `packages/blender-prep/src/blender_prep/vse/layout_manager.py`
9. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/project_setup.py` → `packages/blender-prep/src/blender_prep/vse/project_setup.py`

### Animator Submodule Files
10. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/animators/__init__.py` → `packages/blender-prep/src/blender_prep/vse/animators/__init__.py`
11. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/animators/beat_switch_animator.py` → `packages/blender-prep/src/blender_prep/vse/animators/beat_switch_animator.py`
12. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/animators/energy_pulse_animator.py` → `packages/blender-prep/src/blender_prep/vse/animators/energy_pulse_animator.py`
13. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/animators/multi_pip_animator.py` → `packages/blender-prep/src/blender_prep/vse/animators/multi_pip_animator.py`

### Effects Submodule Files
14. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/effects/__init__.py` → `packages/blender-prep/src/blender_prep/vse/effects/__init__.py`
15. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/core/blender_vse/effects/vintage_film_effects.py` → `packages/blender-prep/src/blender_prep/vse/effects/vintage_film_effects.py`

### CLI Files
16. `/home/wojtas/dev/setka-monorepo/packages/obsession/src/cli/blend_setup.py` → `packages/blender-prep/src/blender_prep/cli/blend_setup.py`

### Test Files
17. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_blender_project.py` → `packages/blender-prep/tests/test_project_manager.py`
18. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_blend_setup_cli.py` → `packages/blender-prep/tests/test_blend_setup_cli.py`
19. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_blender_animation_engine.py` → `packages/blender-prep/tests/test_animation_engine.py`
20. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_blender_project_setup.py` → `packages/blender-prep/tests/test_project_setup.py`
21. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_blender_vse_config.py` → `packages/blender-prep/tests/test_vse_config.py`
22. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_blender_vse_constants.py` → `packages/blender-prep/tests/test_vse_constants.py`
23. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_blender_vse_keyframe_helper.py` → `packages/blender-prep/tests/test_keyframe_helper.py`
24. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_blender_vse_layout_manager.py` → `packages/blender-prep/tests/test_layout_manager.py`
25. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_beat_switch_animator.py` → `packages/blender-prep/tests/test_beat_switch_animator.py`
26. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_energy_pulse_animator.py` → `packages/blender-prep/tests/test_energy_pulse_animator.py`
27. `/home/wojtas/dev/setka-monorepo/packages/obsession/tests/test_multi_pip_animator.py` → `packages/blender-prep/tests/test_multi_pip_animator.py`

### Documentation Files
28. `/home/wojtas/dev/setka-monorepo/packages/obsession/docs/blender-session-import-example.py` → `packages/blender-prep/docs/blender-session-import-example.py`

## Dependencies to Extract
The new package will depend on:
- `setka-common` (for file structure management and utilities)
- External: `numpy`, `scipy` (for animation calculations)

## Import Updates Required
After migration, update imports in:
- `obsession` package that uses Blender functionality
- Any scripts or notebooks that reference Blender modules

## Migration Steps
1. Create new package structure
2. Move files using prepared mv commands
3. Update imports in moved files
4. Update imports in obsession package
5. Update pyproject.toml dependencies
6. Run tests to ensure everything works