# Complete YAML-Based Animation System - Specification

## Requirements Analysis

### Wymaganie 1: CLI generuje config + blend z widocznymi animacjami w addon
- CLI tworzy YAML config i .blend file
- Po otwarciu .blend animacje są widoczne w addon panel
- Działa bezpośrednio po CLI bez dodatkowych kroków

### Wymaganie 2: Niezależne otwieranie .blend
- .blend file można otworzyć bezpośrednio (bez CLI)
- Animacje nadal widoczne w addon panel
- Wszystkie dane zachowane i dostępne

### Wymaganie 3: Edycja i zapis animacji/layout do YAML
- Możliwość edycji parametrów animacji w addon UI
- Zapis zmian z powrotem do pliku YAML
- Synchronizacja między UI a plikiem konfiguracyjnym

## Solution Architecture

### Core Concept
Plik YAML jako **jedyne źródło prawdy** z dwukierunkową synchronizacją:
- **READ**: Panel odczytuje animacje z YAML file
- **WRITE**: Panel zapisuje zmiany z powrotem do YAML file

### Data Flow
```
CLI/Manual → YAML file ←→ Blender Addon Panel
                ↓
            .blend file (stores only path to YAML)
```

## Implementation Strategy

### 1. Critical Fix: VSE Script Must Store Config Path

#### A. Update `vse_script.py` - Store YAML Path in .blend
```python
# In blender_addon/vse_script.py
def setup_vse_project(self) -> bool:
    """Set up VSE project with YAML configuration."""

    # ... existing setup code ...

    # CRITICAL: Store config path in scene before saving
    import bpy
    bpy.context.scene.cinemon_config_path = str(self.config_path)

    # Save blend file with stored config path
    if self.output_blend:
        try:
            bpy.ops.wm.save_as_mainfile(filepath=str(self.output_blend))
            print(f"✓ Saved project with config path: {self.config_path}")
        except Exception as e:
            print(f"✗ Error saving project: {e}")
            return False

    return True
```

### 2. Panel Implementation: Read and Write YAML

#### A. Update `animation_panel.py` - Complete YAML Integration
```python
from pathlib import Path
import sys
from typing import Any, Dict, List

# Add vendor path for YAML
vendor_path = Path(__file__).parent / "vendor"
if str(vendor_path) not in sys.path:
    sys.path.insert(0, str(vendor_path))

import vendor.yaml as yaml

try:
    import bpy
    from bpy.types import Panel, Operator
    from bpy.props import FloatProperty, StringProperty, IntProperty
except ImportError:
    # Testing without Blender
    pass

class AnimationYAMLManager:
    """Manager for reading and writing animation data to/from YAML."""

    def __init__(self):
        self._cache = {}
        self._mtime = {}

    def resolve_config_path(self, context) -> Path:
        """Resolve config path, handling relative paths from .blend location."""
        config_path = getattr(context.scene, "cinemon_config_path", "")
        if not config_path:
            return None

        path = Path(config_path)

        # If absolute path, use directly
        if path.is_absolute():
            return path

        # If relative path, resolve from .blend file directory
        blend_file = bpy.data.filepath
        if blend_file:
            blend_dir = Path(blend_file).parent
            resolved_path = blend_dir / path
            return resolved_path.resolve()

        return path

    def get_strip_animations(self, context, strip_name: str) -> List[Dict[str, Any]]:
        """Read animations for strip from YAML file with caching."""
        config_path = self.resolve_config_path(context)
        if not config_path or not config_path.exists():
            return []

        try:
            # Check cache
            current_mtime = config_path.stat().st_mtime
            cache_key = str(config_path)

            if (cache_key in self._cache and
                self._mtime.get(cache_key) == current_mtime):
                # Cache hit
                strip_animations = self._cache[cache_key]
            else:
                # Cache miss - reload file
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                strip_animations = config.get('strip_animations', {}) if config else {}
                self._cache[cache_key] = strip_animations
                self._mtime[cache_key] = current_mtime

            # Return animations for specific strip or "all"
            if strip_name in strip_animations:
                return strip_animations[strip_name]
            elif "all" in strip_animations:
                return strip_animations["all"]

            return []

        except Exception as e:
            print(f"Error reading YAML config: {e}")
            return []

    def update_animation_parameter(self, context, strip_name: str,
                                 animation_index: int, param_name: str,
                                 new_value: float) -> bool:
        """Update animation parameter in YAML file."""
        config_path = self.resolve_config_path(context)
        if not config_path or not config_path.exists():
            return False

        try:
            # Read current config
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config or 'strip_animations' not in config:
                return False

            # Update parameter
            strip_animations = config['strip_animations']
            if strip_name in strip_animations:
                animations = strip_animations[strip_name]
                if 0 <= animation_index < len(animations):
                    animations[animation_index][param_name] = new_value

                    # Write back to file
                    with open(config_path, 'w', encoding='utf-8') as f:
                        yaml.dump(config, f, default_flow_style=False,
                                allow_unicode=True, sort_keys=False)

                    # Clear cache
                    cache_key = str(config_path)
                    if cache_key in self._cache:
                        del self._cache[cache_key]

                    return True

            return False

        except Exception as e:
            print(f"Error updating YAML config: {e}")
            return False

# Global instance
yaml_manager = AnimationYAMLManager()

class CINEMON_PT_active_strip_animations(Panel):
    """Panel showing and editing animations for currently active strip."""

    bl_label = "Active Strip Animations"
    bl_idname = "CINEMON_PT_active_strip_animations"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Cinemon"
    bl_parent_id = "CINEMON_PT_main_panel"

    def draw(self, context):
        """Draw the active strip animations panel with editing capabilities."""
        layout = self.layout

        try:
            # Get current active strip
            if not context.scene.sequence_editor:
                layout.label(text="No sequence editor", icon="ERROR")
                return

            active_strip = context.scene.sequence_editor.active_strip

            if not active_strip:
                layout.label(text="No strip selected", icon="INFO")
                layout.label(text="Select a strip in timeline to edit animations")
                return

            # Show active strip name and config source
            layout.label(text=f"Strip: {active_strip.name}", icon="SEQUENCE")

            config_path = yaml_manager.resolve_config_path(context)
            if config_path and config_path.exists():
                layout.label(text=f"Config: {config_path.name}", icon="FILE_TEXT")
            else:
                layout.label(text="Config file missing!", icon="ERROR")
                if config_path:
                    layout.label(text=f"Expected: {config_path}")
                return

            layout.separator()

            # Get animations for active strip from YAML file
            animations = yaml_manager.get_strip_animations(context, active_strip.name)

            if not animations:
                layout.label(text="No animations for this strip", icon="INFO")

                # Show add animation button
                layout.separator()
                layout.operator("cinemon.add_animation_to_strip",
                              text="Add Animation", icon="PLUS")
            else:
                # Show existing animations with edit controls
                for i, animation in enumerate(animations):
                    self.draw_editable_animation_item(layout, context,
                                                    active_strip.name, animation, i)

            layout.separator()

        except Exception as e:
            layout.label(text=f"Error: {e}", icon="ERROR")

    def draw_editable_animation_item(self, layout, context, strip_name: str,
                                   animation: Dict[str, Any], index: int):
        """Draw animation item with editable controls."""
        try:
            # Animation box
            box = layout.box()

            # Header row
            header = box.row()
            anim_type = animation.get("type", "unknown")
            trigger = animation.get("trigger", "unknown")
            header.label(text=f"{anim_type.title()} ({trigger})", icon="ANIM")

            # Remove button
            remove_op = header.operator("cinemon.remove_animation",
                                      text="", icon="X")
            remove_op.strip_name = strip_name
            remove_op.animation_index = index

            # Editable parameters
            self.draw_editable_parameters(box, context, strip_name, animation, index)

        except Exception as e:
            layout.label(text=f"Animation error: {e}", icon="ERROR")

    def draw_editable_parameters(self, layout, context, strip_name: str,
                               animation: Dict[str, Any], index: int):
        """Draw editable parameters for animation."""
        try:
            anim_type = animation.get("type", "")

            # Common parameters - Intensity
            if "intensity" in animation:
                row = layout.row()
                row.label(text="Intensity:")
                intensity_op = row.operator("cinemon.edit_animation_param",
                                          text=f"{animation['intensity']:.2f}")
                intensity_op.strip_name = strip_name
                intensity_op.animation_index = index
                intensity_op.param_name = "intensity"
                intensity_op.current_value = animation['intensity']

            # Duration frames for applicable animations
            if (anim_type in ["scale", "rotation", "brightness_flicker"] and
                "duration_frames" in animation):
                row = layout.row()
                row.label(text="Duration:")
                duration_op = row.operator("cinemon.edit_animation_param",
                                         text=f"{animation['duration_frames']:.0f}f")
                duration_op.strip_name = strip_name
                duration_op.animation_index = index
                duration_op.param_name = "duration_frames"
                duration_op.current_value = animation['duration_frames']

            # Type-specific parameters
            if anim_type == "shake" and "return_frames" in animation:
                row = layout.row()
                row.label(text="Return:")
                return_op = row.operator("cinemon.edit_animation_param",
                                       text=f"{animation['return_frames']:.0f}f")
                return_op.strip_name = strip_name
                return_op.animation_index = index
                return_op.param_name = "return_frames"
                return_op.current_value = animation['return_frames']

            elif anim_type == "rotation" and "degrees" in animation:
                row = layout.row()
                row.label(text="Degrees:")
                degrees_op = row.operator("cinemon.edit_animation_param",
                                        text=f"{animation['degrees']:.1f}°")
                degrees_op.strip_name = strip_name
                degrees_op.animation_index = index
                degrees_op.param_name = "degrees"
                degrees_op.current_value = animation['degrees']

            elif anim_type == "vintage_color" and "sepia_amount" in animation:
                row = layout.row()
                row.label(text="Sepia:")
                sepia_op = row.operator("cinemon.edit_animation_param",
                                      text=f"{animation['sepia_amount']:.2f}")
                sepia_op.strip_name = strip_name
                sepia_op.animation_index = index
                sepia_op.param_name = "sepia_amount"
                sepia_op.current_value = animation['sepia_amount']

        except Exception as e:
            layout.label(text=f"Parameter error: {e}", icon="ERROR")

# New operators for editing animations
class CINEMON_OT_edit_animation_param(Operator):
    """Edit animation parameter and save to YAML."""

    bl_idname = "cinemon.edit_animation_param"
    bl_label = "Edit Animation Parameter"
    bl_description = "Edit animation parameter"
    bl_options = {"REGISTER", "UNDO"}

    strip_name: StringProperty(name="Strip Name")
    animation_index: IntProperty(name="Animation Index")
    param_name: StringProperty(name="Parameter Name")
    current_value: FloatProperty(name="Current Value")
    new_value: FloatProperty(name="New Value", description="Enter new value")

    def invoke(self, context, event):
        """Open dialog with current value."""
        self.new_value = self.current_value
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Draw parameter input dialog."""
        layout = self.layout
        layout.label(text=f"Edit {self.param_name} for {self.strip_name}")
        layout.prop(self, "new_value")

    def execute(self, context):
        """Update parameter in YAML file."""
        success = yaml_manager.update_animation_parameter(
            context, self.strip_name, self.animation_index,
            self.param_name, self.new_value)

        if success:
            self.report({"INFO"}, f"Updated {self.param_name} to {self.new_value}")

            # Trigger reapplication of animations
            bpy.ops.cinemon.reapply_animations_from_yaml()
        else:
            self.report({"ERROR"}, "Failed to update parameter")

        return {"FINISHED"}

class CINEMON_OT_remove_animation(Operator):
    """Remove animation from strip and update YAML."""

    bl_idname = "cinemon.remove_animation"
    bl_label = "Remove Animation"
    bl_description = "Remove this animation from the strip"
    bl_options = {"REGISTER", "UNDO"}

    strip_name: StringProperty(name="Strip Name")
    animation_index: IntProperty(name="Animation Index")

    def execute(self, context):
        """Remove animation from YAML file."""
        # TODO: Implement remove animation logic
        self.report({"INFO"}, f"Removed animation {self.animation_index} from {self.strip_name}")
        return {"FINISHED"}

class CINEMON_OT_add_animation_to_strip(Operator):
    """Add new animation to strip."""

    bl_idname = "cinemon.add_animation_to_strip"
    bl_label = "Add Animation"
    bl_description = "Add new animation to this strip"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Add new animation to strip."""
        # TODO: Implement add animation dialog
        self.report({"INFO"}, "Add animation dialog - TODO")
        return {"FINISHED"}

class CINEMON_OT_reapply_animations_from_yaml(Operator):
    """Reapply all animations from YAML to update keyframes."""

    bl_idname = "cinemon.reapply_animations_from_yaml"
    bl_label = "Reapply Animations"
    bl_description = "Reapply animations from YAML config to update keyframes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Reapply animations by calling VSE script logic."""
        try:
            config_path = yaml_manager.resolve_config_path(context)
            if config_path and config_path.exists():
                # TODO: Call animation reapplication logic
                self.report({"INFO"}, "Animations reapplied from YAML")
            else:
                self.report({"ERROR"}, "No config file found")
        except Exception as e:
            self.report({"ERROR"}, f"Failed to reapply animations: {e}")

        return {"FINISHED"}

# Registration
classes = [
    CINEMON_PT_active_strip_animations,
    CINEMON_OT_edit_animation_param,
    CINEMON_OT_remove_animation,
    CINEMON_OT_add_animation_to_strip,
    CINEMON_OT_reapply_animations_from_yaml,
]
```

#### C. Update `operators.py` - Remove Memory Storage
```python
# Remove all context.scene["cinemon_strip_animations"] assignments
# Keep only cinemon_config_path storage

class LoadConfigOperator(Operator, ImportHelper):
    def execute(self, context):
        """Load and validate YAML configuration file."""
        try:
            # Load configuration using YAMLConfigLoader
            loader = YAMLConfigLoader()
            config = loader.load_from_file(self.filepath)

            # Store configuration in scene for ApplyConfigOperator
            context.scene.cinemon_config = config

            # Store filepath - THIS IS THE KEY FOR PANEL
            context.scene.cinemon_config_path = self.filepath

            # REMOVED: Don't store strip_animations in memory
            # OLD: context.scene["cinemon_strip_animations"] = config.strip_animations

            # Display info (optional)
            if hasattr(config, 'layout') and hasattr(config.layout, 'type'):
                context.scene["cinemon_layout_type"] = config.layout.type

            self.report({"INFO"}, f"Loaded configuration from {Path(self.filepath).name}")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to load configuration: {e}")
            return {"CANCELLED"}
```

## Implementation Steps

### Phase 1: Critical Fix (Enable Basic Functionality)
1. **Update `vse_script.py`**: Add `bpy.context.scene.cinemon_config_path = str(self.config_path)` before save
2. **Test**: Run CLI → Open .blend → Check if config path is stored

### Phase 2: Read-Only Panel
1. **Update `animation_panel.py`**: Replace with YAML reading implementation
2. **Update `operators.py`**: Remove memory storage
3. **Test**: CLI → Open .blend → Panel shows animations

### Phase 3: Editing Capabilities
1. **Add animation editing operators** to `animation_panel.py`
2. **Implement parameter update functionality**
3. **Add animation reapplication system**
4. **Test**: Edit parameter → Save to YAML → Keyframes update

## Testing Scenarios

### Scenario 1: CLI Workflow (Requirement 1)
```bash
# Generate project
cd /home/wokoziej/Wideo/obs/2025-07-29 20-29-16/
cinemon-blend-setup . --preset minimal

# Test 1: Open .blend directly
blender blender/2025-07-29\ 20-29-16.blend

# Expected Result:
# - Panel shows: "Config: animation_config_minimal.yaml"
# - Select RPI_FRONT.mp4 → Shows "Scale (beat) - Intensity: 2.00"
# - All animations visible for all configured strips
```

### Scenario 2: Independent .blend Opening (Requirement 2)
```bash
# Without running CLI, open existing .blend
blender /home/wokoziej/Wideo/obs/2025-07-29\ 20-29-16/blender/2025-07-29\ 20-29-16.blend

# Expected Result:
# - Panel automatically finds ../animation_config_minimal.yaml
# - All animations visible
# - No need to reload configuration
```

### Scenario 3: Animation Editing (Requirement 3)
```bash
# In Blender addon panel:
# 1. Select strip with animation
# 2. Click "Intensity: 2.00" button
# 3. Change to 3.50 in dialog
# 4. Click OK

# Expected Result:
# - YAML file updated with new intensity value
# - Keyframes automatically updated in timeline
# - Panel shows new value immediately
```

## Success Criteria

### ✅ Requirement 1: CLI → .blend with visible animations
- CLI generates YAML + .blend
- Opening .blend shows animations in panel
- No additional steps required

### ✅ Requirement 2: Independent .blend opening
- .blend opens without CLI
- Animations visible immediately
- Config path correctly resolved

### ✅ Requirement 3: Animation editing
- Parameters editable in panel UI
- Changes saved to YAML file
- Keyframes update automatically
            # Load configuration using YAMLConfigLoader
            loader = YAMLConfigLoader()
            config = loader.load_from_file(self.filepath)

            # Store configuration in scene for later use
            context.scene.cinemon_config = config

            # Store filepath for reference - THIS IS THE KEY
            context.scene.cinemon_config_path = self.filepath

            # REMOVE: Don't store strip_animations in memory anymore
            # OLD CODE TO REMOVE:
            # if hasattr(config, 'strip_animations') and config.strip_animations:
            #     context.scene["cinemon_strip_animations"] = config.strip_animations

            # Store basic info for main panel display
            if hasattr(config, 'layout') and hasattr(config.layout, 'type'):
                context.scene["cinemon_layout_type"] = config.layout.type

            # Count animations by reading from config object (not storing)
            if hasattr(config, 'strip_animations') and config.strip_animations:
                total_animations = sum(len(anims) for anims in config.strip_animations.values())
                context.scene["cinemon_animations_count"] = total_animations

            self.report(
                {"INFO"}, f"Loaded configuration from {Path(self.filepath).name}"
            )
            return {"FINISHED"}

        except ValidationError as e:
            self.report({"ERROR"}, f"Configuration validation error: {e}")
            return {"CANCELLED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to load configuration: {e}")
            return {"CANCELLED"}
```

#### C. Update `__init__.py` - Preset Operator
```python
class CINEMON_OT_load_preset(bpy.types.Operator):
    def execute(self, context):
        """Load the specified preset."""
        try:
            # Get preset path
            addon_dir = Path(__file__).parent
            preset_path = addon_dir / "example_presets" / self.preset_name

            if not preset_path.exists():
                self.report({"ERROR"}, f"Preset not found: {self.preset_name}")
                return {"CANCELLED"}

            # Store filepath for reference - ONLY THIS
            context.scene.cinemon_config_path = str(preset_path)

            # REMOVE: Don't parse and store in memory
            # OLD CODE TO REMOVE:
            # with open(preset_path, "r", encoding="utf-8") as f:
            #     config_data = yaml.safe_load(f)
            # context.scene["cinemon_strip_animations"] = config.strip_animations

            # Basic display info can be read on-demand or stored minimally
            preset_display = (
                self.preset_name.replace(".yaml", "").replace("-", " ").title()
            )
            self.report({"INFO"}, f"Loaded {preset_display} preset")
            return {"FINISHED"}

        except Exception as e:
            print(f"DEBUG: Preset loading exception: {e}")
            self.report({"ERROR"}, f"Failed to load preset: {e}")
            return {"CANCELLED"}
```

### 2. Implementation Steps

1. **Step 1**: Update `animation_panel.py`
   - Add YAML import with vendor path
   - Replace `get_strip_animations()` to read from file
   - Update `draw()` method to show config source and better error handling

2. **Step 2**: Update `operators.py`
   - Remove `context.scene["cinemon_strip_animations"]` assignments
   - Keep only `cinemon_config_path` storage
   - Count animations from config object, not from stored data

3. **Step 3**: Update `__init__.py`
   - Simplify preset loading to store only file path
   - Remove YAML parsing and memory storage in preset operator

4. **Step 4**: Test Implementation
   - Load YAML config → check panel shows animations
   - Save .blend → close Blender → reopen → check panel still works
   - Test with missing/corrupted YAML files

### 3. Integration with CLI and Workflow

#### A. With CLI cinemon-blend-setup (Existing Workflow)

```bash
# Current CLI workflow - generates YAML + applies in one step
cd /home/wokoziej/Wideo/obs/2025-07-29 20-29-16/
cinemon-blend-setup . --preset minimal
```

**What happens:**
1. CLI generates `animation_config_minimal.yaml` in recording directory
2. CLI calls Blender with VSE script that:
   - Creates .blend file in `blender/` subdirectory
   - Loads YAML config via our addon operators
   - **cinemon_config_path gets set to: `../animation_config_minimal.yaml`** (relative path)
   - Applies animations to create keyframes
   - Saves .blend file

**Result:** User can later open .blend and see animations in panel because path is saved.

#### B. Manual Workflow (Future/Alternative)

```bash
# Step 1: Generate YAML config only
cinemon-generate-config /home/wokoziej/Wideo/obs/2025-07-29 20-29-16/ --preset minimal
# Creates: animation_config_minimal.yaml

# Step 2: User opens Blender manually
blender /home/wokoziej/Wideo/obs/2025-07-29 20-29-16/blender/project.blend

# Step 3: User loads config in addon UI
# Cinemon VSE Animator > Load YAML Config > select animation_config_minimal.yaml

# Step 4: User applies config in addon UI
# Cinemon VSE Animator > Apply to VSE

# Step 5: User saves .blend file
# cinemon_config_path is saved, animations visible after reopen
```

#### C. Expected Behavior After Implementation

**Scenario 1: CLI-generated project**
```
1. User opens CLI-generated .blend file:
   /home/wokoziej/Wideo/obs/2025-07-29 20-29-16/blender/2025-07-29 20-29-16.blend

2. Blender loads cinemon_config_path = "../animation_config_minimal.yaml"

3. Panel resolves relative path to:
   /home/wokoziej/Wideo/obs/2025-07-29 20-29-16/animation_config_minimal.yaml

4. User selects strip "RPI_FRONT.mp4" in timeline

5. Animation panel reads YAML and shows:
   - Config: animation_config_minimal.yaml ✓
   - Strip: RPI_FRONT.mp4
   - Scale (beat) - Intensity: 2.00 - Easing: EASE_IN_OUT ✓
```

**Scenario 2: Manual workflow**
```
1. User generates YAML: cinemon-generate-config . --preset vintage

2. User opens Blender manually, creates new VSE project

3. User loads YAML via addon: Load YAML Config > animation_config_vintage.yaml

4. cinemon_config_path = "/full/path/to/animation_config_vintage.yaml"

5. Panel immediately shows animations for selected strips ✓
```

#### D. Path Resolution Strategy

```python
def resolve_config_path(self, context) -> Path:
    """Resolve config path, handling relative paths from .blend location."""
    config_path = getattr(context.scene, "cinemon_config_path", "")
    if not config_path:
        return None

    path = Path(config_path)

    # If absolute path, use directly
    if path.is_absolute():
        return path

    # If relative path, resolve from .blend file directory
    blend_file = bpy.data.filepath
    if blend_file:
        blend_dir = Path(blend_file).parent
        resolved_path = blend_dir / path
        return resolved_path.resolve()

    return path
```

### 4. CLI Integration Points

#### A. Update VSE Script (executed by CLI)
The CLI calls `vse_script.py` which needs to save the config path:

```python
# In blender_addon/vse_script.py or wherever config is loaded by CLI
def setup_cinemon_from_cli(config_path: str):
    """Called by CLI to set up project with YAML config."""
    import bpy

    # Store relative path from .blend location to YAML
    # If .blend is in /path/recording/blender/project.blend
    # And YAML is in /path/recording/config.yaml
    # Store as: "../config.yaml"

    blend_path = Path(bpy.data.filepath) if bpy.data.filepath else None
    config_path_obj = Path(config_path)

    if blend_path and blend_path.parent != config_path_obj.parent:
        # Calculate relative path
        try:
            relative_path = os.path.relpath(config_path, blend_path.parent)
            bpy.context.scene.cinemon_config_path = relative_path
        except ValueError:
            # Different drives on Windows, use absolute path
            bpy.context.scene.cinemon_config_path = str(config_path_obj)
    else:
        # Same directory or no blend file yet, use absolute
        bpy.context.scene.cinemon_config_path = str(config_path_obj)

    print(f"Cinemon: Stored config path: {bpy.context.scene.cinemon_config_path}")
```

#### B. CLI Commands Integration

**Current CLI (already working):**
```bash
# Generates YAML + Creates .blend in one step
cinemon-blend-setup /path/to/recording --preset minimal
# What it does:
# 1. Calls CinemonConfigGenerator.generate_config_from_preset()
# 2. Creates: animation_config_minimal.yaml
# 3. Calls BlenderProjectManager.create_vse_project_with_yaml_file()
# 4. Creates: blender/recording.blend with cinemon_config_path saved
```

**Separate config generation (already available):**
```bash
# Generate YAML only
cinemon-generate-config /path/to/recording --preset minimal
# Output: animation_config_minimal.yaml

# Then user can either:
# Option 1: Use generated config with CLI
cinemon-blend-setup /path/to/recording --config animation_config_minimal.yaml

# Option 2: Load manually in Blender addon UI
blender  # then load animation_config_minimal.yaml via addon
```

**The Key Point:** Both CLI commands ALREADY generate YAML files. Our addon just needs to read from these existing YAML files instead of storing data in memory.

### 5. Error Handling

```python
# Panel shows helpful errors based on workflow:

# CLI Workflow errors:
- "Config: animation_config_minimal.yaml" ✓ (file exists, CLI-generated)
- "Config file missing! Expected: animation_config_minimal.yaml" ⚠️ (user moved/deleted YAML)

# Manual Workflow errors:
- "No config loaded - Load YAML Config first" ℹ️ (user hasn't loaded anything)
- "Config file missing! Expected: /full/path/config.yaml" ⚠️ (loaded file was moved)

# General errors:
- "No animations for this strip" + shows available strips ℹ️
- "Error reading YAML config: [parse error]" ❌ (corrupted YAML)
```

### 5. Benefits of This Approach

#### Pros:
- **Niezawodność**: YAML zawsze istnieje obok pliku .blend
- **Synchronizacja**: Zmiany w YAML automatycznie widoczne w panelu
- **Debugowalność**: Łatwo sprawdzić co jest w YAML
- **Edytowalność**: User może ręcznie edytować YAML
- **Versionowanie**: YAML może być w git, .blend nie
- **Prostota**: Brak skomplikowanej logiki persystencji

#### Cons:
- **Performance**: Parsowanie YAML przy każdym odświeżeniu panelu
- **Dependency**: Panel wymaga dostępu do oryginalnego YAML

### 4. Performance Optimizations

```python
class AnimationDataCache:
    def __init__(self):
        self._cache = {}
        self._mtime = {}

    def get_animations(self, yaml_path, strip_name):
        """Get animations with file modification time caching."""
        if not Path(yaml_path).exists():
            return []

        current_mtime = Path(yaml_path).stat().st_mtime

        # Cache hit - file not modified
        if yaml_path in self._cache and self._mtime.get(yaml_path) == current_mtime:
            return self._cache[yaml_path].get(strip_name, [])

        # Cache miss - reload file
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        self._cache[yaml_path] = config.get('strip_animations', {})
        self._mtime[yaml_path] = current_mtime

        return self._cache[yaml_path].get(strip_name,
                                         self._cache[yaml_path].get('all', []))
```

## Enhanced Features

### 1. Future Editability in Panel
Panel może w przyszłości nie tylko wyświetlać, ale też edytować animacje:

```python
def update_animation_in_yaml(self, yaml_path, strip_name, animation_index, new_params):
    """Update animation parameters directly in YAML file."""
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)

    # Update animation
    config['strip_animations'][strip_name][animation_index].update(new_params)

    # Write back to file
    with open(yaml_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
```

### 2. Auto-reload on File Change
```python
def setup_file_watcher(self, yaml_path):
    """Watch YAML file for changes and refresh panel."""
    # Blender timer operator to check file mtime periodically
    pass
```

### 3. Fallback Mechanism
```python
def get_strip_animations(self, context, strip_name):
    """Get animations with fallback priority."""
    # Priority 1: From YAML file
    config_path = getattr(context.scene, "cinemon_config_path", "")
    if config_path:
        animations = self._from_yaml_file(config_path, strip_name)
        if animations:
            return animations

    # Priority 2: From memory (legacy support)
    if "cinemon_strip_animations" in context.scene:
        strip_animations = context.scene["cinemon_strip_animations"]
        return strip_animations.get(strip_name, strip_animations.get('all', []))

    return []
```

## Migration Strategy

### Phase 1: Add YAML Reading
- Update `animation_panel.py` to read from YAML file
- Keep current memory storage as fallback
- Test with existing .blend files

### Phase 2: Remove Memory Storage
- Remove `context.scene["cinemon_strip_animations"]` assignments
- Store only `cinemon_config_path`
- Add caching for performance

### Phase 3: Add Edit Capabilities
- Allow editing animations in panel
- Write changes back to YAML
- Add file watching for external edits

## Testing Plan

1. **Create YAML** → **Load in Blender** → **Check Panel** ✓
2. **Save .blend** → **Close Blender** → **Reopen** → **Check Panel** ✓
3. **Edit YAML externally** → **Refresh Panel** → **See Changes** ✓
4. **Missing YAML file** → **Panel shows error** ✓
5. **Corrupted YAML** → **Panel shows error** ✓

## Implementation Priority

1. **High Priority**: Read animations from YAML file instead of memory
2. **Medium Priority**: Add caching for performance
3. **Low Priority**: Add editing capabilities in panel
4. **Future**: File watching and auto-refresh
