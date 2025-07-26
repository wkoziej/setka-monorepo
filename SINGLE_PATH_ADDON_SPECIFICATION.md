# Specyfikacja: Unifikacja do Pojedynczej Ścieżki Addon

**Data:** 2025-07-21
**Autor:** Claude Code + Wojtas
**Priority:** HIGH
**Component:** Cinemon Animation System Unification
**Status:** SPECIFICATION

## Problem

Obecnie mamy dwa systemy które robią to samo:
1. **VSE Script System** - tworzy layout + animacje + naming
2. **Addon System** - tworzy layout + animacje + naming

To prowadzi do:
- Duplikacji kodu
- Konfliktów w naming (VSE używa nazw plików, addon używa `Video_X`)
- Różnych sposobów keyframe insertion
- Niekonsystentnego zachowania między ścieżkami

## Proponowane Rozwiązanie

**Pojedyncza ścieżka wykonania:** Wszystkie operacje (layout + animacje + naming) wykonuje **tylko addon system**.

### VSE Script → Minimal Setup
VSE script robi **tylko podstawowe setup**:
```python
class BlenderVSEConfigurator:
    def setup_vse_project(self):
        # 1. Create basic sequence editor
        # 2. Add video strips with simple naming (Video_1, Video_2, etc.)
        # 3. Add audio strip
        # 4. Set timeline length
        # 5. Save auto-preset trigger: bpy.context.scene['cinemon_auto_preset'] = preset_name
        # 6. Save project
        # ❌ NO layout application
        # ❌ NO animations
        # ❌ NO complex naming
```

### Addon → Full Control
Addon przejmuje pełną kontrolę:
```python
def register():
    # Auto-detect preset trigger on addon startup
    if bpy.context.scene.get('cinemon_auto_preset'):
        preset_name = bpy.context.scene['cinemon_auto_preset']
        auto_load_preset(preset_name)

def auto_load_preset(preset_name):
    # 1. Load preset configuration (multi-pip.yaml)
    # 2. Apply layout (positions strips correctly)
    # 3. Apply animations (create keyframes)
    # 4. Clear auto-preset flag
    # Result: Identical to manual preset selection
```

## Szczegółowe Zmiany

### 1. VSE Script Changes (`vse_script.py`)

**Remove:**
```python
# ❌ Remove these methods:
def _apply_yaml_layout_and_animations()
def _apply_compositional_animations()
def _create_animations_from_yaml()
# ❌ Remove all animation classes imports
# ❌ Remove layout application logic
```

**Simplify:**
```python
class BlenderVSEConfigurator:
    def setup_vse_project(self):
        """Create basic VSE project - strips + audio only."""

        # Basic project setup
        success = self._setup_basic_project()
        if not success:
            return False

        # Add video strips with simple naming
        success = self._add_video_strips_basic()
        if not success:
            return False

        # Add audio
        success = self._add_audio_track()
        if not success:
            return False

        # Save auto-preset trigger for addon
        preset_name = self._extract_preset_name_from_config()
        if preset_name:
            bpy.context.scene['cinemon_auto_preset'] = preset_name
            print(f"🎯 Set auto-preset for addon: {preset_name}")

        # Save project
        success = self.save_project()
        return success

    def _add_video_strips_basic(self):
        """Add video strips with Video_1, Video_2 naming."""
        video_files = self.config_data['project']['video_files']
        sequencer = bpy.context.scene.sequence_editor

        for i, video_file in enumerate(video_files):
            channel = i + 2
            strip_name = f"Video_{i + 1}"  # Simple naming

            new_strip = sequencer.sequences.new_movie(
                name=strip_name,
                filepath=str(video_file),
                channel=channel,
                frame_start=1,
            )
            # ❌ NO layout positioning
            # ❌ NO animations

        return True
```

### 2. Addon Changes (`__init__.py`)

**Add Auto-Preset Detection:**
```python
def register():
    """Register addon with auto-preset detection."""

    # Register existing components
    register_operators()
    register_panels()
    register_vse_operators()
    register_apply_system()
    register_animation_panel()

    # NEW: Auto-detect and load preset
    auto_load_preset_if_needed()

def auto_load_preset_if_needed():
    """Check for auto-preset trigger and load if present."""
    try:
        import bpy
        scene = bpy.context.scene

        if 'cinemon_auto_preset' in scene:
            preset_name = scene['cinemon_auto_preset']
            print(f"🎯 Auto-loading preset: {preset_name}")

            # Load preset configuration
            load_and_apply_preset(preset_name)

            # Clear trigger to prevent re-loading
            del scene['cinemon_auto_preset']
            print(f"✅ Auto-preset {preset_name} loaded successfully")

    except Exception as e:
        print(f"❌ Auto-preset loading failed: {e}")

def load_and_apply_preset(preset_name: str):
    """Load preset and apply both layout and animations."""

    # Load preset file
    preset_path = get_addon_preset_path(preset_name)  # e.g. multi-pip.yaml
    with open(preset_path, 'r') as f:
        config_data = yaml.safe_load(f)

    # Apply layout
    apply_layout_to_strips(config_data['layout'])

    # Load animations to strip context manager
    manager = get_strip_context_manager()
    manager.load_preset_for_apply(config_data)

    # Apply animations to all strips
    regenerate_animations_for_all_strips()

    print(f"Applied preset {preset_name}: layout + animations")
```

### 3. Config Generator Changes (`blend_setup.py`)

**Preserve Preset Information:**
```python
def generate_config_from_addon_preset(...):
    # Current logic stays the same
    # BUT: Also save preset name for VSE script

    config_data["cinemon_preset_name"] = preset_name  # NEW

    # Write config file
    return output_path
```

### 4. Project Manager Changes (`project_manager.py`)

**Pass Preset Name to VSE Script:**
```python
def create_vse_project_with_config(self, recording_dir, yaml_config):
    # Create temp config file
    temp_config = self._create_resolved_config(yaml_config)

    # NEW: Include preset name if available
    if hasattr(yaml_config, 'preset_name'):
        temp_config["cinemon_preset_name"] = yaml_config.preset_name

    # Execute VSE script
    success = self._execute_blender_with_json_config(...)
```

## Workflow Porównanie

### Przed (Problematyczny)
```
cinemon-blend-setup --preset multi-pip --open-blender
  ↓
VSE Script: layout + animations + save + naming conflicts
  ↓
Blender opens: Layout OK, animations missing/conflicted
  ↓
User: Must manually reload in addon
```

### Po (Jednolity)
```
cinemon-blend-setup --preset multi-pip --open-blender
  ↓
VSE Script: basic strips + audio + scene['cinemon_auto_preset'] = 'multi-pip'
  ↓
Blender opens → Addon register() detects auto_preset
  ↓
Addon: load multi-pip.yaml → apply layout + animations automatically
  ↓
Result: Perfect layout + working animations (identical to manual workflow)
```

## Korzyści

1. **🎯 Jedna ścieżka wykonania** - tylko addon aplikuje layout + animacje
2. **🧹 Eliminacja duplikacji** - VSE animation system można usunąć
3. **🔄 Konsystentne zachowanie** - identyczne z manualnym workflow
4. **🐛 Brak konfliktów naming** - addon kontroluje naming
5. **✅ Gwarantowane działanie** - addon system już działa poprawnie
6. **🔧 Łatwiejszy maintenance** - jedna implementacja animacji

## Implementacja Plan

### Phase 1: VSE Script Simplification
- Usunąć aplikację animacji z VSE script
- Usunąć aplikację layout z VSE script
- Dodać zapis `cinemon_auto_preset` w scenie
- Uprościć do podstawowego setup (strips + audio)

### Phase 2: Addon Auto-Loading
- Dodać auto-detection presetu w `register()`
- Implementować `load_and_apply_preset()`
- Przetestować auto-loading workflow

### Phase 3: Cleanup
- Usunąć nieużywane VSE animation classes
- Usunąć VSE layout application
- Zaktualizować testy
- Dokumentacja

### Phase 4: Testing
- Test pełnego workflow: `cinemon-blend-setup --preset multi-pip --open-blender`
- Weryfikacja identycznego zachowania z manual preset selection
- Test różnych presetów (vintage, minimal, beat-switch)

## Risk Assessment

**Low Risk:**
- Addon system już działa poprawnie
- Manual preset workflow jest sprawdzony
- Auto-loading to tylko trigger mechanizm

**Medium Risk:**
- Timing addon registration vs scene loading
- Blender API compatibility z auto-loading

## Success Criteria

- ✅ `cinemon-blend-setup --preset multi-pip --open-blender` otwiera Blender z layout + animations
- ✅ Zachowanie identyczne z manual preset selection
- ✅ Brak duplikacji kodu animacji
- ✅ Wszystkie preset typy działają (vintage, minimal, multi-pip, beat-switch)
- ✅ Performance nie jest degraded

## Conclusion

To podejście eliminuje główne źródło problemów - duplikację systemów. Zamiast naprawiać konflikty między dwoma systemami, **używamy tylko jednego sprawdzonego systemu (addon)** i dajemy mu pełną kontrolę.

VSE script staje się "thin wrapper" do podstawowego setup, a addon robi całą "heavy lifting" logic.
