# Multi-PiP Layout Issue - Critical Bug Report

**Date:** 2025-07-20  
**Reporter:** Claude Code + Wojtas  
**Priority:** HIGH  
**Component:** Cinemon Blender VSE Integration  
**Status:** UNRESOLVED

## Problem Summary

Multi-PiP layout is not working in any system (VSE script, addon, or CLI). Video strips are positioned at (0,0) with scale (1.0) instead of the expected main-pip layout with 2 fullscreen cameras and corner PiPs.

## Expected Behavior

When using multi-pip preset or main-pip layout:
- **Video_1, Video_2**: Position (0,0), Scale (1.0) - fullscreen main cameras
- **Video_3**: Position (644, 362), Scale (0.25) - top-right PiP  
- **Video_4**: Position (-644, 362), Scale (0.25) - top-left PiP
- **Video_5**: Position (644, -362), Scale (0.25) - bottom-right PiP

## Actual Behavior

All video strips remain at:
- **Position**: (0, 0)  
- **Scale**: (1.0, 1.0)  
- All strips appear in center, overlapping

## Systems Tested

### 1. VSE Script (Direct Blender Execution)
```bash
cd "/home/wojtas/Wideo/obs/2025-07-10 19-39-29"
blender --background --python "/path/to/vse_script.py" -- --config animation_config_multi-pip.yaml
```

**Result**: 
- ✅ Layout calculated correctly during execution
- ✅ Positions applied to strips during execution  
- ❌ Strips not saved to blend file (0 sequences after reload)

### 2. Addon System (Post-Load Application)
```bash
# Load blend file and apply layout via addon
```

**Result**:
- ❌ Layout not applied at all
- Strips remain at default positions

### 3. CLI Tool (Project Manager + VSE Script)
```bash
cinemon-blend-setup ./recording_dir --preset multi-pip
```

**Result**:
- ❌ Same as VSE script - layout not persisted

## Technical Analysis

### Debug Evidence

#### VSE Script Execution (Working During Runtime)
```
🎬 AnimationCompositor._apply_layout: 5 strips, 5 positions
🎬 Strip 0 (Video_1): pos=(0, 0), scale=1.0
🎬 Applied to Video_1: offset=(0.0, 0.0), scale=(1.0, 1.0)
🎬 Strip 1 (Video_2): pos=(0, 0), scale=1.0  
🎬 Applied to Video_2: offset=(0.0, 0.0), scale=(1.0, 1.0)
🎬 Strip 2 (Video_3): pos=(644, 362), scale=0.25
🎬 Applied to Video_3: offset=(644.0, 362.0), scale=(0.25, 0.25)
🎬 Strip 3 (Video_4): pos=(-644, 362), scale=0.25
🎬 Applied to Video_4: offset=(-644.0, 362.0), scale=(0.25, 0.25)
🎬 Strip 4 (Video_5): pos=(644, -362), scale=0.25
🎬 Applied to Video_5: offset=(644.0, -362.0), scale=(0.25, 0.25)
🎭 Compositor apply result: True
```

#### Blend File Inspection (Broken After Save/Load)
```
=== STRIP POSITIONS INSPECTION ===
Found 0 total sequences:
Found 0 video strips:
```

#### Path Resolution (Working)
```
🎬 VSE script resolved video_files: [
  '/home/wojtas/Wideo/obs/2025-07-10 19-39-29/extracted/RPI_FRONT.mp4 (absolute: True, exists: True)',
  '/home/wojtas/Wideo/obs/2025-07-10 19-39-29/extracted/RPI_RIGHT.mp4 (absolute: True, exists: True)',
  ...
]
```

#### Save Operations (Reporting Success)
```
🎬 Before save: 6 total sequences, 5 video strips
🎬 Before final save: 6 total sequences, 5 video strips
✓ Zapisano projekt z animacjami: blender/multi-pip.blend
```

### Root Cause Analysis

#### Primary Issue: VSE Script Save/Load Failure
**Problem**: Video strips are correctly created and positioned during VSE script execution, but completely disappear after blend file save/load cycle.

**Evidence**:
- Strips exist during execution (6 sequences reported)
- Blend file size is reasonable (781KB)  
- Blend file is valid Blender format
- After reload: 0 sequences found
- Issue occurs with both Video_Editing template and default scene

**Suspected Causes**:
1. **Blender Background Mode Bug**: VSE strips may not serialize correctly in headless mode
2. **File Path Issues**: Despite absolute paths, strips may not link correctly after reload
3. **Addon Interference**: Cinemon addon auto-loads and may interfere with strip persistence

#### Secondary Issue: Addon System Layout Application
**Problem**: Addon system fails to apply layout even when blend file loads correctly.

**Evidence**:
- `apply_layout_to_strips()` method exists but not triggered
- Multi-pip layout support was added but may have bugs
- No debug output from addon layout application

### Configuration Details

#### Test Configuration (animation_config_multi-pip.yaml)
```yaml
project:
  video_files:
  - RPI_FRONT.mp4
  - RPI_RIGHT.mp4  
  - Urządzenie przechwytujące obraz (V4L2) 2.mp4
  - Urządzenie przechwytujące obraz (V4L2) 3.mp4
  - Urządzenie przechwytujące obraz (V4L2).mp4
  fps: 30
  resolution:
    width: 1920
    height: 1080
  main_audio: Przechwytywanie wejścia dźwięku (PulseAudio).m4a

layout:
  type: main-pip
  config:
    pip_scale: 0.25
    margin_percent: 0.08

strip_animations:
  Video_1:
  - type: scale
    trigger: beat
    intensity: 0.2
    duration_frames: 3
  # ... more animations
```

#### MainPipLayout Implementation
```python
def calculate_positions(self, strip_count: int, resolution: Tuple[int, int]) -> List[LayoutPosition]:
    """Calculate main-pip positions: first 2 strips fullscreen, rest as corner PiPs."""
    
    positions = []
    
    # First 2 strips: fullscreen at center
    for i in range(min(2, strip_count)):
        positions.append(LayoutPosition(x=0, y=0, scale=1.0))
    
    # Remaining strips: corner PiPs
    pip_positions = self._calculate_pip_positions(resolution)
    for i in range(2, strip_count):
        pip_index = (i - 2) % len(pip_positions)
        positions.append(pip_positions[pip_index])
    
    return positions
```

## Environment

- **OS**: Linux 6.14.0-24-generic
- **Blender**: 4.5.0 (hash 8cb6b388974a built 2025-07-15 01:36:28)  
- **Python**: Blender embedded Python
- **Working Directory**: `/home/wojtas/Wideo/obs/2025-07-10 19-39-29`
- **Execution Mode**: Background (`--background`)

## Files Involved

### Core Implementation
- `/packages/cinemon/src/blender/vse_script.py` - Main VSE script
- `/packages/cinemon/src/blender/vse/animation_compositor.py` - Layout application
- `/packages/cinemon/src/blender/vse/layouts/main_pip_layout.py` - Main-pip layout logic
- `/packages/cinemon/blender_addon/__init__.py` - Addon layout system

### Test Files
- `/home/wojtas/Wideo/obs/2025-07-10 19-39-29/animation_config_multi-pip.yaml` - Test configuration
- `/home/wojtas/Wideo/obs/2025-07-10 19-39-29/blender/multi-pip.blend` - Generated blend file (broken)
- `/home/wojtas/Wideo/obs/2025-07-10 19-39-29/extracted/*.mp4` - Source video files

## Reproduction Steps

1. **Setup Test Environment**:
   ```bash
   cd "/home/wojtas/Wideo/obs/2025-07-10 19-39-29"
   # Ensure extracted/ directory has video files
   # Ensure animation_config_multi-pip.yaml exists
   ```

2. **Test VSE Script**:
   ```bash
   blender --background --python "/path/to/vse_script.py" -- --config animation_config_multi-pip.yaml
   # Observe: Layout applied during execution
   # Observe: Strips lost after save
   ```

3. **Test Addon System**:
   ```bash
   # Load blend file with addon
   # Observe: Layout not applied at all
   ```

4. **Verify Issue**:
   ```bash
   blender --background --python -c "
   import bpy
   bpy.ops.wm.open_mainfile(filepath='blender/multi-pip.blend')
   seq = bpy.context.scene.sequence_editor
   print(f'Sequences: {len(seq.sequences) if seq else 0}')
   "
   # Expected: > 0 sequences  
   # Actual: 0 sequences
   ```

## Impact

- **Critical**: Multi-pip layout completely non-functional
- **User Experience**: All strips overlap in center, unusable output
- **Workflow Broken**: Cannot create PiP layouts for multi-camera recordings
- **Data Loss**: VSE strips disappear after save, work lost

## Potential Solutions to Investigate

### Short-term Workarounds
1. **Manual Layout**: Users manually position strips in Blender GUI
2. **Single Camera**: Use only one camera until fixed
3. **External Tool**: Use DaVinci Resolve or similar for multi-cam layouts

### Technical Solutions
1. **Fix VSE Script Persistence**:
   - Investigate Blender background mode VSE serialization
   - Test alternative save methods
   - Try GUI mode execution

2. **Fix Addon Layout Application**:
   - Debug addon `apply_layout_to_strips()` call chain
   - Fix multi-pip layout support in addon
   - Ensure layout changes trigger correctly

3. **Hybrid Approach**:
   - VSE script creates project structure
   - Addon applies layout post-load  
   - Manual save after addon layout application

### Investigation Tasks
1. **Minimal Reproduction**: Create smallest possible test case
2. **Blender Version Test**: Try different Blender versions
3. **GUI vs Background**: Compare behavior in GUI mode
4. **Strip Properties**: Investigate which strip properties persist vs disappear

## Related Issues

- Layout positioning system confusion (VSE script vs addon)
- YAML configuration format conversions working correctly
- Path resolution working correctly
- Animation application working correctly

## Next Steps

1. **PRIORITY 1**: Fix VSE script strip persistence issue
2. **PRIORITY 2**: Fix addon layout application as fallback
3. **PRIORITY 3**: Choose unified system architecture  

---

**Note**: This is a complex issue affecting core functionality. Both layout systems (VSE script + addon) are failing in different ways, suggesting fundamental architecture problems rather than simple bugs.