# Dokumentacja Techniczna: Przepływ Preset/Config w Cinemon

## Problem

Obecnie mamy skomplikowany przepływ konfiguracji, który powoduje że animacje nie działają po załadowaniu presetu w addon:

1. **Brak audio events** - addon nie może znaleźć pliku analizy audio
2. **Różne ścieżki** - preset ma hardcoded ścieżki, które nie pasują do rzeczywistych plików
3. **Duplikacja logiki** - VSE script i addon używają różnych metod ładowania

## Obecny Przepływ (Złożony)

### 1. Tworzenie Projektu (cinemon-blend-setup)

```
cinemon-blend-setup /recording --preset minimal
    ↓
CinemonConfigGenerator.generate_preset()
    ↓
Wczytuje preset z: blender_addon/example_presets/minimal.yaml
    ↓
Generuje: /recording/animation_config_minimal.yaml (z prawidłowymi ścieżkami)
    ↓
BlenderProjectManager.create_vse_project_with_config()
    ↓
Uruchamia Blender z vse_script.py
    ↓
vse_script.py używa animation_config_minimal.yaml ✓
```

### 2. Auto-load w Addon

```
Blender otwiera minimal.blend
    ↓
auto_load_handler() znajduje minimal.cinemon.json
    ↓
Czyta preset_name: "minimal"
    ↓
Ładuje preset z: blender_addon/example_presets/minimal.yaml ❌
    ↓
Preset ma hardcoded: "./analysis/main_audio_analysis.json" ❌
    ↓
Ale rzeczywisty plik: "analysis/Przechwytywanie wejścia dźwięku (PulseAudio)_analysis.json"
    ↓
Audio events nie są załadowane → animacje się nie aplikują
```

### 3. Manual Load Preset w Addon

```
User wybiera preset z dropdown
    ↓
CINEMON_OT_load_selected_preset.execute()
    ↓
Ładuje preset z: blender_addon/example_presets/minimal.yaml ❌
    ↓
Ten sam problem co auto-load
```

## Architektura Klas

### VSE (Python Package)

```python
# src/blender/config/
CinemonConfigGenerator      # Generuje YAML config z presetów
├── generate_preset()       # Używa PresetManager + MediaDiscovery
├── generate_config()       # Custom config
└── _build_config_from_preset()  # Podmienia ścieżki na rzeczywiste

PresetManager              # Zarządza presetami
├── get_preset()          # Ładuje preset YAML
└── list_presets()        # Lista dostępnych

MediaDiscovery            # Auto-odkrywa pliki media
├── discover_video_files()
├── discover_audio_files()
├── detect_main_audio()   # Znajduje główny audio
└── validate_structure()

# src/blender/
BlenderProjectManager     # Tworzy projekty Blender
└── create_vse_project_with_config()

vse_script.py            # Skrypt uruchamiany w Blenderze
└── _load_animation_data()  # Ładuje audio analysis
```

### Addon (Blender Package)

```python
# blender_addon/
__init__.py
├── auto_load_handler()              # Auto-ładuje preset przy otwarciu
├── CINEMON_OT_load_selected_preset  # Manual load preset
└── store_config_in_scene()          # Zapisuje config w scene

vse_operators.py
└── regenerate_animations_for_strips()  # Aplikuje animacje
    └── Ładuje audio_analysis z config['audio_analysis']['file']

animation_applicators.py
└── apply_animation_to_strip()       # Aplikuje pojedynczą animację
    └── extract_events_for_trigger() # Wymaga audio_events!

strip_context.py
└── StripContextManager              # Zarządza zmianami
    ├── load_preset_for_apply()      # Oznacza zmiany do Apply
    └── apply_changes()              # Zwraca config ze zmianami
```

## Problemy z Obecną Implementacją

1. **Duplikacja ścieżek konfiguracji**
   - VSE generuje `animation_config_*.yaml` z prawidłowymi ścieżkami
   - Addon ładuje `example_presets/*.yaml` z hardcoded ścieżkami

2. **Brak współdzielenia logiki**
   - VSE ma `CinemonConfigGenerator` który poprawnie generuje config
   - Addon nie używa tej klasy, tylko ładuje raw preset

3. **Różne punkty wejścia**
   - cinemon-blend-setup → generuje config → uruchamia Blender
   - addon → ładuje preset → próbuje użyć hardcoded ścieżek

4. **Metadata JSON wie o właściwym config**
   ```json
   {
     "config": {
       "path": "/recording/animation_config_minimal.yaml"  // Tu jest właściwy config!
     }
   }
   ```
   Ale auto-load go ignoruje i używa preset_name

## Propozycja Uproszczenia

### Rozwiązanie 1: Addon używa CinemonConfigGenerator (Rekomendowane)

```python
# W addon __init__.py
def load_preset(self, context, preset_name):
    # Znajdź recording directory
    recording_dir = self.get_recording_directory(context)

    # Użyj CinemonConfigGenerator jak cinemon-blend-setup
    from blender.config import CinemonConfigGenerator
    generator = CinemonConfigGenerator()

    # Generuj config z prawidłowymi ścieżkami
    config_path = generator.generate_preset(recording_dir, preset_name)

    # Załaduj wygenerowany config
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    # Teraz config_data ma prawidłowe ścieżki!
    self.store_config_in_scene(context, config_data, config_path, preset_name)
```

### Rozwiązanie 2: Auto-load używa config path z metadata

```python
def auto_load_handler(dummy):
    metadata = load_metadata()

    # Użyj config path zamiast preset name
    config_path = metadata.get('config', {}).get('path')
    if config_path and Path(config_path).exists():
        # Załaduj config bezpośrednio
        config_data = load_yaml(config_path)
        store_config_in_scene(config_data)
    else:
        # Fallback to preset
        load_preset(metadata.get('preset_name'))
```

### Rozwiązanie 3: Presety używają placeholderów

```yaml
# example_presets/minimal.yaml
audio_analysis:
  file: "${AUDIO_ANALYSIS_PATH}"  # Placeholder

# Addon podmienia podczas ładowania
def load_preset(preset_path, recording_dir):
    config = load_yaml(preset_path)

    # Podmień placeholdery
    main_audio = discover_main_audio(recording_dir)
    analysis_path = f"analysis/{main_audio.stem}_analysis.json"

    config['audio_analysis']['file'] = analysis_path
    return config
```

## Rekomendacja

**Użyj Rozwiązania 1** - niech addon używa `CinemonConfigGenerator`:

1. **DRY** - jedna logika generowania config
2. **Spójność** - addon i CLI działają identycznie
3. **Poprawność** - automatyczne wykrywanie ścieżek
4. **Prostota** - nie trzeba duplikować logiki discovery

## Szczegółowy Plan Implementacji Rozwiązania 1

### Krok 1: Dodanie importów i pomocniczych funkcji

W `blender_addon/__init__.py` dodać:

```python
# Na początku pliku, po innych importach
import sys
from pathlib import Path

# Dodaj ścieżki do sys.path dla importu CinemonConfigGenerator
def setup_cinemon_paths():
    """Setup paths for importing cinemon modules."""
    addon_path = Path(__file__).parent
    cinemon_src_path = addon_path.parent / "src"

    # Add paths if not already present
    paths_to_add = [
        str(cinemon_src_path),
        str(addon_path.parent.parent.parent / "common" / "src")  # For setka_common
    ]

    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)

def get_recording_directory(context) -> Optional[Path]:
    """Get recording directory from current Blender file path."""
    blend_path = bpy.data.filepath
    if not blend_path:
        return None

    # Assume structure: recording_dir/blender/project.blend
    blend_path = Path(blend_path)
    if blend_path.parent.name == "blender":
        return blend_path.parent.parent

    return None
```

### Krok 2: Modyfikacja CINEMON_OT_load_selected_preset

Zmienić metodę `execute()`:

```python
def execute(self, context):
    """Load the selected preset."""
    selected_preset = context.scene.cinemon_selected_preset
    if not selected_preset or selected_preset == 'NONE':
        self.report({'WARNING'}, "No preset selected")
        return {'CANCELLED'}

    # Remove .yaml extension if present
    preset_name = selected_preset.replace('.yaml', '')

    print(f"DEBUG: Loading selected preset: {preset_name}")
    try:
        # Get recording directory
        recording_dir = get_recording_directory(context)
        if not recording_dir:
            self.report({'ERROR'}, "Cannot determine recording directory from Blender file")
            return {'CANCELLED'}

        # Setup paths for import
        setup_cinemon_paths()

        # Import and use CinemonConfigGenerator
        from blender.config import CinemonConfigGenerator
        generator = CinemonConfigGenerator()

        # Generate config with proper paths (like cinemon-blend-setup does)
        try:
            config_path = generator.generate_preset(recording_dir, preset_name)
            print(f"DEBUG: Generated config at: {config_path}")
        except ValueError as e:
            # If generation fails, try to use existing generated config
            config_path = recording_dir / f"animation_config_{preset_name}.yaml"
            if not config_path.exists():
                self.report({'ERROR'}, f"Failed to generate config: {e}")
                return {'CANCELLED'}
            print(f"DEBUG: Using existing config: {config_path}")

        # Load generated config
        config_data = self.load_preset_yaml(config_path)
        if not config_data:
            return {'CANCELLED'}

        # Store configuration in scene
        self.store_config_in_scene(context, config_data, config_path, preset_name)

        preset_display = preset_name.replace('-', ' ').replace('_', ' ').title()
        self.report({'INFO'}, f"Loaded {preset_display} preset")
        return {'FINISHED'}

    except Exception as e:
        print(f"DEBUG: Preset loading exception: {e}")
        import traceback
        traceback.print_exc()
        self.report({'ERROR'}, f"Failed to load preset: {e}")
        return {'CANCELLED'}
```

### Krok 3: Modyfikacja auto_load_handler

Zmienić obsługę auto-load:

```python
@bpy.app.handlers.persistent
def auto_load_handler(dummy):
    """Auto-load preset based on metadata JSON file."""
    try:
        blend_path = bpy.data.filepath
        if not blend_path:
            return

        # Look for metadata file
        metadata_file = Path(blend_path).with_suffix('.cinemon.json')
        if not metadata_file.exists():
            return

        print(f"🔍 Found Cinemon metadata: {metadata_file}")

        # Load metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        if not metadata.get('auto_load', False):
            print("ℹ Auto-loading disabled in metadata")
            return

        # PRIORITY 1: Use config path from metadata (if exists)
        config_path = metadata.get('config', {}).get('path')
        if config_path and Path(config_path).exists():
            print(f"🎯 Auto-loading from config path: {config_path}")

            # Load config directly
            config_data = None
            with open(config_path, 'r', encoding='utf-8') as f:
                vendor_path = Path(__file__).parent / "vendor"
                if str(vendor_path) not in sys.path:
                    sys.path.insert(0, str(vendor_path))

                import yaml
                config_data = yaml.safe_load(f)

            if config_data:
                # Store in scene
                bpy.context.scene.cinemon_config_path = str(config_path)
                bpy.context.scene.cinemon_current_preset = metadata.get('preset_name', 'custom')

                # Use load operator's methods
                operator = CINEMON_OT_load_selected_preset()
                config_data = operator.map_video_names_to_strips(bpy.context, config_data)
                operator.store_config_in_scene(bpy.context, config_data, Path(config_path), metadata.get('preset_name', 'custom'))

                print(f"✅ Auto-loaded config from: {config_path}")
                return

        # PRIORITY 2: Generate from preset name (fallback)
        preset_name = metadata.get('preset_name')
        if preset_name:
            print(f"🎯 Auto-loading preset (generating config): {preset_name}")

            # Get recording directory
            recording_dir = get_recording_directory(bpy.context)
            if recording_dir:
                # Setup paths and generate config
                setup_cinemon_paths()

                try:
                    from blender.config import CinemonConfigGenerator
                    generator = CinemonConfigGenerator()

                    # Generate config
                    config_path = generator.generate_preset(recording_dir, preset_name)

                    # Load generated config
                    with open(config_path, 'r', encoding='utf-8') as f:
                        import yaml
                        config_data = yaml.safe_load(f)

                    # Store in scene
                    operator = CINEMON_OT_load_selected_preset()
                    config_data = operator.map_video_names_to_strips(bpy.context, config_data)
                    operator.store_config_in_scene(bpy.context, config_data, config_path, preset_name)

                    print(f"✅ Auto-loaded preset: {preset_name}")
                except Exception as e:
                    print(f"⚠ Failed to generate/load preset: {e}")

    except Exception as e:
        print(f"⚠ Auto-load handler error: {e}")
        import traceback
        traceback.print_exc()
```

### Krok 4: Usunięcie niepotrzebnych metod

Można usunąć lub uprościć:
- `get_preset_path()` - nie potrzebna, bo generujemy config
- Część kodu w `load_preset_yaml()` związana z szukaniem presetów

### Rezultat

Po implementacji:
1. **Load Preset** będzie generował config z prawidłowymi ścieżkami (jak cinemon-blend-setup)
2. **Auto-load** będzie używał wygenerowanego config lub generował go na żądanie
3. **Audio analysis** będzie zawsze miał prawidłową ścieżkę
4. **Animacje będą działać** bo będą miały audio events

## Podsumowanie Problemów

1. **Animacje nie działają bo:**
   - Addon ładuje preset z hardcoded ścieżkami
   - Audio analysis file nie jest znaleziony
   - Bez audio events, animacje są pomijane

2. **Apply button pokazuje zmiany ale:**
   - Keyframes się nie tworzą (brak events)
   - Tylko czyszczenie działa (`clear_strip_animations`)

3. **Auto-load nie działa bo:**
   - Używa preset_name zamiast config path
   - Ignoruje metadata z właściwą ścieżką

Uproszczenie przez użycie `CinemonConfigGenerator` rozwiąże wszystkie te problemy.
