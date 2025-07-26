# Cinemon --open-blender Layout Application Issue

**Date:** 2025-07-20
**Reporter:** Claude Code + Wojtas
**Priority:** MEDIUM
**Component:** Cinemon CLI --open-blender flag
**Status:** OPEN
**Affects:** Multi-PiP and potentially other layout presets

## Problem Summary

The `--open-blender` flag in cinemon-blend-setup does not properly apply layout positioning when creating VSE projects. Video strips are created but remain at default position (0,0) with scale (1.0) instead of the expected layout positions defined by presets like multi-pip.

## Expected Behavior

When using:
```bash
cinemon-blend-setup /path/to/recording --preset multi-pip --open-blender
```

Should create a blend file with:
- **Video_1, Video_2**: Position (0,0), Scale (1.0) - fullscreen main cameras
- **Video_3**: Position (644, 362), Scale (0.25) - top-right PiP
- **Video_4**: Position (-644, 362), Scale (0.25) - top-left PiP
- **Video_5**: Position (644, -362), Scale (0.25) - bottom-right PiP

And then open in Blender GUI for further editing.

## Actual Behavior

All video strips remain at:
- **Position**: (0, 0)
- **Scale**: (1.0, 1.0)
- All strips appear overlapping in center of canvas

## Reproduction Steps

1. **Setup test environment**:
   ```bash
   cd "/home/wojtas/Wideo/obs/OK jeszcze bardziej _ 2025-07-08 19-38-18"
   # Ensure extracted/ directory has video files
   # Ensure analysis/ directory has audio analysis
   ```

2. **Test broken command**:
   ```bash
   cd "/home/wojtas/dev/setka-monorepo"
   uv run --package cinemon cinemon-blend-setup \
     "/home/wojtas/Wideo/obs/OK jeszcze bardziej _ 2025-07-08 19-38-18" \
     --preset multi-pip \
     --main-audio "Przechwytywanie wejścia dźwięku (PulseAudio).m4a" \
     --open-blender
   ```

3. **Verify broken output**:
   ```bash
   blender --background --python -c "
   import bpy
   bpy.ops.wm.open_mainfile(filepath='blender/OK jeszcze bardziej _ 2025-07-08 19-38-18.blend')
   seq = bpy.context.scene.sequence_editor
   strips = [s for s in seq.sequences if s.type == 'MOVIE']
   for strip in strips:
       print(f'{strip.name}: pos=({strip.transform.offset_x}, {strip.transform.offset_y}), scale={strip.transform.scale_x}')
   "
   ```

   **Expected**: Different positions for different strips
   **Actual**: All strips at (0.0, 0.0), scale=1.0

## Working Workaround

Use the VSE script directly instead of `--open-blender` flag:

1. **Generate working blend file**:
   ```bash
   cd "/home/wojtas/Wideo/obs/OK jeszcze bardziej _ 2025-07-08 19-38-18"
   blender --background \
     --python "/home/wojtas/dev/setka-monorepo/packages/cinemon/src/blender/vse_script.py" \
     -- --config animation_config_multi-pip.yaml \
     --output-blend "blender/working_multi-pip.blend"
   ```

2. **Open in Blender GUI**:
   ```bash
   blender blender/working_multi-pip.blend
   ```

3. **Verify working output**:
   ```bash
   # Layout is correctly applied:
   # Video_1: pos=(0.0, 0.0), scale=1.0      -> Main camera
   # Video_2: pos=(0.0, 0.0), scale=1.0      -> Main camera
   # Video_3: pos=(644.0, 362.0), scale=0.25 -> Top-right PiP
   # Video_4: pos=(-644.0, 362.0), scale=0.25 -> Top-left PiP
   # Video_5: pos=(644.0, -362.0), scale=0.25 -> Bottom-right PiP
   ```

## Technical Analysis

### Differences in Execution Paths

#### Working Path (VSE Script Direct)
```
YAML Config → VSE Script → AnimationCompositor → Layout Application → Single Save
```

#### Broken Path (--open-blender Flag)
```
Preset → YAML Generation → Project Manager → VSE Script → ??? → GUI Launch
```

### Root Cause Hypothesis

1. **Project Manager Path Issue**: The `project_manager.py` may not be passing layout configuration correctly to the VSE script when using GUI mode
2. **Template Interference**: `--open-blender` uses Video_Editing template which might reset strip positions
3. **Save Timing**: Layout may be applied but not saved properly when launching GUI mode
4. **Missing Compositor**: AnimationCompositor._apply_layout() may not be called in GUI launch path

### Evidence from Logs

**Working VSE Script** shows:
```
🎬 AnimationCompositor._apply_layout: 5 strips, 5 positions
🎬 Strip 0 (Video_1): pos=(0, 0), scale=1.0
🎬 Applied to Video_1: offset=(0.0, 0.0), scale=(1.0, 1.0)
🎬 Strip 2 (Video_3): pos=(644, 362), scale=0.25
🎬 Applied to Video_3: offset=(644.0, 362.0), scale=(0.25, 0.25)
...
🎭 Compositor apply result: True
```

**Broken --open-blender** shows:
```
Animation mode: compositional with 0 animations
```
→ Suggests animations/layout not being processed

## Impact

- **User Experience**: Multi-PiP preset appears non-functional when using recommended `--open-blender` workflow
- **Documentation**: Current docs suggest using `--open-blender` but this doesn't work as expected
- **Workflow Disruption**: Users must use workaround with direct VSE script calls
- **Preset System**: All layout presets potentially affected, not just multi-pip

## Potential Solutions

### Short-term (Workaround Documentation)
1. **Update CLI help text** to recommend VSE script approach for layout presets
2. **Add warning** when using `--open-blender` with layout-heavy presets
3. **Document working workflow** in CLAUDE.md and user docs

### Medium-term (Fix --open-blender)
1. **Debug project_manager.py**: Trace where layout application is lost in GUI launch path
2. **Ensure AnimationCompositor**: Make sure compositor is called even in GUI mode
3. **Fix save timing**: Ensure layout is applied and saved before GUI launch
4. **Add verification**: Check strip positions before launching GUI

### Long-term (Architecture Improvement)
1. **Unify execution paths**: Make --open-blender use the same compositor path as background mode
2. **Layout verification**: Add automatic verification that layout was applied correctly
3. **Error reporting**: Better error messages when layout application fails
4. **Preset validation**: Validate that preset requirements are met before proceeding

## Related Issues

- Previously fixed multi-pip layout issues (MainPipLayout mapping, dual saves)
- Potential similar issues with other layout presets (vintage, music-video, etc.)
- Video Editing workspace not being properly detected in Blender GUI

## Test Cases for Fix

1. **Basic multi-pip**: `--preset multi-pip --open-blender` should apply correct layout
2. **Other presets**: Test vintage, music-video presets with `--open-blender`
3. **Custom config**: Test `--config custom.yaml --open-blender` with layout specified
4. **Verification**: All test cases should have strip positions verifiable in GUI
5. **Backwards compatibility**: Existing workflows without `--open-blender` should continue working

## Files Involved

### Core Implementation
- `/packages/cinemon/src/blender/cli/blend_setup.py` - CLI entry point with --open-blender flag
- `/packages/cinemon/src/blender/project_manager.py` - Project creation and GUI launch
- `/packages/cinemon/src/blender/vse_script.py` - VSE script execution (works correctly)
- `/packages/cinemon/src/blender/vse/animation_compositor.py` - Layout application (works correctly)

### Configuration
- `/packages/cinemon/src/blender/config/preset_manager.py` - Multi-pip preset definition
- Generated YAML configs - Layout configuration parsing

## Recommended Workflow (Current Workaround)

Until this issue is fixed, use this workflow for multi-pip projects:

```bash
# 1. Navigate to recording directory
cd "/path/to/recording"

# 2. Generate YAML config (if not exists)
uv run --package cinemon cinemon-generate-config . --preset multi-pip

# 3. Create blend file with correct layout
blender --background \
  --python "/path/to/setka-monorepo/packages/cinemon/src/blender/vse_script.py" \
  -- --config animation_config_multi-pip.yaml \
  --output-blend "blender/working_multi-pip.blend"

# 4. Open in Blender GUI for editing
blender blender/working_multi-pip.blend

# 5. Switch to Video Editing workspace in Blender GUI
# 6. Use Cinemon addon for further modifications
# 7. Set render output and render final video
```

This workflow guarantees correct multi-pip layout application and full addon functionality.

---

**Note**: This issue affects the user experience but has a reliable workaround. The core layout system works correctly - the issue is specifically with the GUI launch integration in the CLI tool.
