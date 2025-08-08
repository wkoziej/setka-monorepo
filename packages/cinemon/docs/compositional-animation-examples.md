# Compositional Animation Examples

## Overview

The new compositional animation system allows you to combine different layouts with multiple independent animations. This document shows practical examples of how to use this system.

## Basic Usage

### Example 1: Random Layout with Scale Animation

```bash
export BLENDER_VSE_ANIMATION_MODE="compositional"
export BLENDER_VSE_LAYOUT_TYPE="random"
export BLENDER_VSE_LAYOUT_CONFIG="seed=42"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.3:2"

cinemon-blend-setup ./my_recording
```

**Result**: Videos positioned randomly on canvas, scaling up on bass events.

### Example 2: No Overlap Layout with Multiple Animations

```bash
export BLENDER_VSE_LAYOUT_TYPE="random"
export BLENDER_VSE_LAYOUT_CONFIG="overlap_allowed=false,seed=123,margin=0.1"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.4:3,shake:beat:8.0:2"

cinemon-blend-setup ./my_recording --animation-mode compositional
```

**Result**: Videos positioned randomly without overlapping, with 10% margin from edges. Videos scale on bass and shake on beats.

### Example 3: Complex Multi-Animation Setup

```bash
export BLENDER_VSE_LAYOUT_CONFIG="min_scale=0.5,max_scale=0.8,margin=0.05"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.2:2,shake:beat:5.0:3,rotation:beat:1.5:4"

cinemon-blend-setup ./my_recording --animation-mode compositional
```

**Result**: Videos sized between 50%-80% of original, with three simultaneous animations: scale on bass, shake on beats, and rotation wobble on beats.

## Advanced Configuration

### Layout Parameters

#### Random Layout
```bash
export BLENDER_VSE_LAYOUT_CONFIG="overlap_allowed=false,margin=0.1,min_scale=0.3,max_scale=0.7,seed=42"
```

- `overlap_allowed`: Whether videos can overlap (true/false)
- `margin`: Distance from screen edges (0.0-1.0, percentage)
- `min_scale`: Minimum video scale (0.0-1.0)
- `max_scale`: Maximum video scale (0.0-1.0)
- `seed`: Random seed for reproducible layouts

### Animation Parameters

#### Scale Animation
```bash
"scale:trigger:intensity:duration"
```

- `trigger`: "bass", "beat", "energy_peaks"
- `intensity`: Scale increase factor (0.1 = 10% larger)
- `duration`: Animation duration in frames

#### Shake Animation
```bash
"shake:trigger:intensity:frames"
```

- `trigger`: "beat", "bass", "energy_peaks"
- `intensity`: Shake distance in pixels
- `frames`: Frames until return to original position

#### Rotation Animation
```bash
"rotation:trigger:degrees:frames"
```

- `trigger`: "beat", "bass", "energy_peaks"
- `degrees`: Maximum rotation in degrees
- `frames`: Frames until return to 0 rotation

#### Jitter Animation (Vintage Film Effect)
```bash
"jitter:continuous:intensity:min_interval:max_interval"
```

- `trigger`: "continuous" (ignored, applies throughout)
- `intensity`: Jitter distance in pixels
- `min_interval`: Minimum frames between jitter changes
- `max_interval`: Maximum frames between jitter changes

#### Brightness Flicker Animation (Vintage Film Effect)
```bash
"brightness_flicker:trigger:intensity:frames"
```

- `trigger`: "beat", "bass", "energy_peaks"
- `intensity`: Brightness reduction amount (0.0 to 1.0)
- `frames`: Frames until return to normal brightness

#### Black & White Effect
```bash
"black_white:one_time:intensity"
```

- `trigger`: "one_time" (ignored, applies to entire strip)
- `intensity`: Desaturation intensity (0.0 = color, 1.0 = full B&W)

#### Film Grain Effect
```bash
"film_grain:one_time:intensity"
```

- `trigger`: "one_time" (ignored, applies to entire strip)
- `intensity`: Grain intensity (0.0 to 1.0)

#### Vintage Color Grading
```bash
"vintage_color:one_time:sepia_amount:contrast_boost"
```

- `trigger`: "one_time" (ignored, applies to entire strip)
- `sepia_amount`: Sepia tint intensity (0.0 to 1.0)
- `contrast_boost`: Contrast increase amount (0.0 to 1.0)

## Real-World Examples

### Music Video Style

For a music video with dramatic effects:

```bash
export BLENDER_VSE_LAYOUT_TYPE="random"
export BLENDER_VSE_LAYOUT_CONFIG="overlap_allowed=false,margin=0.05,min_scale=0.4,max_scale=0.9,seed=100"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.5:3,shake:beat:12.0:2,rotation:energy_peaks:2.0:5"

cinemon-blend-setup ./music_video_recording --animation-mode compositional
```

### Podcast/Interview Style

For a calmer interview setup:

```bash
export BLENDER_VSE_LAYOUT_CONFIG="margin=0.15,min_scale=0.6,max_scale=0.8,seed=200"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.1:4,shake:beat:3.0:3"

cinemon-blend-setup ./interview_recording --animation-mode compositional
```

### Gaming/Streaming Style

For energetic gaming content:

```bash
export BLENDER_VSE_LAYOUT_CONFIG="overlap_allowed=true,margin=0.02,min_scale=0.3,max_scale=0.6"
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.4:2,shake:beat:8.0:2,rotation:bass:1.0:3"

cinemon-blend-setup ./gaming_recording --animation-mode compositional
```

### Vintage Film Style

For authentic vintage film effects:

```bash
export BLENDER_VSE_LAYOUT_CONFIG="overlap_allowed=false,margin=0.1,min_scale=0.5,max_scale=0.8,seed=1950"
export BLENDER_VSE_ANIMATION_CONFIG="shake:beat:2.0:2,jitter:continuous:1.0:3:8,brightness_flicker:beat:0.1:1,black_white:one_time:0.6,film_grain:one_time:0.15,vintage_color:one_time:0.4:0.3"

cinemon-blend-setup ./vintage_recording --animation-mode compositional
```

**Result**: Creates authentic vintage film look with camera shake on beats, continuous film jitter, brightness flicker, black & white conversion, film grain, and sepia color grading.

## Troubleshooting

### No Animation Effects

If animations aren't showing:

1. **Check audio analysis**: Make sure beatrix generated analysis data
2. **Verify triggers**: Ensure your animation triggers match available events
3. **Check intensity**: Low intensity values might not be visible

```bash
# Force new audio analysis
cinemon-blend-setup ./recording --analyze-audio --animation-mode compositional
```

### Videos Overlapping When They Shouldn't

If `overlap_allowed=false` isn't working:

1. **Reduce video scales**: Lower `max_scale` to give more space
2. **Increase margins**: Higher `margin` value gives more edge space
3. **Fewer videos**: Algorithm might not find space for all videos

```bash
export BLENDER_VSE_LAYOUT_CONFIG="overlap_allowed=false,margin=0.15,max_scale=0.5"
```

### Animations Too Subtle

If effects are barely visible:

1. **Increase intensity**: Higher values for more dramatic effects
2. **Increase duration**: Longer animations are more noticeable
3. **Combine animations**: Multiple effects can be more impactful

```bash
export BLENDER_VSE_ANIMATION_CONFIG="scale:bass:0.8:4,shake:beat:20.0:4"
```

## Performance Considerations

### Large Number of Videos

For recordings with many video sources:

- Use `overlap_allowed=true` to avoid collision detection overhead
- Consider lower animation intensities to reduce keyframe count
- Test different seed values to find good layouts

### High FPS Recordings

For 60fps recordings:

- Double the `duration` and `frames` parameters
- Consider reducing animation frequency by using less sensitive triggers

## Python API Usage

You can also use the compositional system directly in Python:

```python
from blender.vse.animation_compositor import AnimationCompositor
from blender.vse.layouts import RandomLayout
from blender.vse.animations import ScaleAnimation, ShakeAnimation

# Create layout
layout = RandomLayout(overlap_allowed=False, seed=42, margin=0.1)

# Create animations
animations = [
    ScaleAnimation(trigger="bass", intensity=0.3, duration_frames=2),
    ShakeAnimation(trigger="beat", intensity=10.0, duration_frames=2)
]

# Create compositor
compositor = AnimationCompositor(layout, animations)

# Apply to strips
success = compositor.apply(video_strips, audio_analysis, fps=30)
```

## Next Steps

The compositional system is designed to be extensible. You can:

1. **Add new layouts**: Implement `BaseLayout` for custom positioning
2. **Add new animations**: Implement `BaseEffectAnimation` for custom effects
3. **Combine systems**: Use compositional animations with legacy modes

For development details, see the main specification document.
