# Specyfikacja Blender Add-on dla Cinemon

## Minimalne Kompletne Rozwiązanie (MVP)

### 1. Podstawowe założenia

- **Pure Python/YAML**: Rezygnacja z konwersji YAML→JSON, bezpośrednie ładowanie YAML w Blenderze
- **Blender Add-on**: Panel UI w Video Sequence Editor do modyfikacji i testowania presetów
- **Szybka wizualizacja**: Natychmiastowy preview zmian bez konieczności renderowania
- **Prostota implementacji**: Wykorzystanie istniejących klas z cinemon (PresetManager, animatorów)

### 2. Struktura plików

```
cinemon/
├── blender_addon/
│   ├── __init__.py           # Rejestracja add-onu
│   ├── operators.py          # Operatory Blendera
│   ├── panels.py             # UI Panel w VSE
│   ├── preset_handler.py     # Obsługa presetów (wykorzystuje PresetManager)
│   └── vendor/
│       └── yaml/             # Vendorowany PyYAML
├── src/
│   └── blender/
│       ├── vse_script.py     # Zmodyfikowany do obsługi pure YAML
│       └── config/
│           └── preset_manager.py  # Istniejący manager presetów
```

### 3. Nowy format YAML (niekompatybilny z poprzednimi wersjami)

```yaml
# Nowy format grupujący animacje per-strip
project:
  video_files: [Camera1.mp4, Camera2.mp4]
  main_audio: "main_audio.m4a"
  fps: 30
  resolution: {width: 1920, height: 1080}

layout:
  type: "random"
  config:
    seed: 42
    margin: 0.1
    overlap_allowed: false

strip_animations:
  Camera1:
    - type: "scale"
      trigger: "beat"
      intensity: 0.3
    - type: "shake"
      trigger: "energy_peaks"
      intensity: 2.0
      return_frames: 2
  
  Camera2:
    - type: "vintage_color"
      trigger: "one_time"
      sepia_amount: 0.4
      contrast_boost: 0.3
    - type: "rotation"
      trigger: "beat"
      degrees: 5.0

audio_analysis:
  file: "./analysis/main_audio_analysis.json"
```

### 4. Panel UI w Blenderze

#### 4.1 Lokalizacja
- **N-Panel** w Video Sequence Editor (boczny panel po prawej, klawisz N)
- Nazwa: "Cinemon Animation"

#### 4.2 Struktura UI (kontekstowa)

```
┌─ Cinemon Animation ─────────────────┐
│                                     │
│ Preset: [my-preset    ▼] [Save]    │
│                                     │
│ ─── Layout (Global) ─────────────   │
│ Type: [Random        ▼]             │
│ Seed: [42        ]                  │
│ Margin: [0.10    ]                  │
│ Overlap: [ ] Allow                  │
│                                     │
│ ─── Active Strip: Camera1 ─────     │
│ ☑ Scale (beat)     Intensity: 0.3   │
│ ☑ Shake (energy)   Intensity: 2.0   │
│ ☐ Rotation         Degrees: 5.0     │
│ [+ Add Animation]                   │
│                                     │
│ [Apply]         [Export YAML]       │
└─────────────────────────────────────┘
```

**Uwaga**: Sekcja "Active Strip" zmienia się dynamicznie w zależności od tego, który strip jest wybrany w timeline VSE.

### 5. Workflow użytkownika

1. **Otwieranie projektu**:
   ```bash
   # CLI nadal działa, ale ładuje pure YAML
   cinemon-blend-setup ./recording --preset vintage --open-blender
   ```

2. **Modyfikacja w Blenderze**:
   - Otwiera się Blender z załadowanym projektem
   - Panel Cinemon w VSE pokazuje aktualną konfigurację
   - Zmiany w UI są buforowane, użytkownik klika "Apply" aby zastosować
   - Po kliknięciu "Apply" animacje są regenerowane dla zmienionych stripów

3. **Zapisywanie**:
   - "Save" - zapisuje zmiany do aktualnego presetu w `~/.cinemon/presets/`

### 6. API dla Blender Add-on

```python
class CinemonAddon:
    """Główna klasa add-onu."""
    
    def load_preset(self, preset_name: str):
        """Ładuje preset z ~/.cinemon/presets/."""
        
    def apply_changes(self):
        """Aplikuje wszystkie zmiany z UI do projektu."""
        
    def get_active_strip_animations(self) -> List[dict]:
        """Zwraca animacje dla aktualnie wybranego strip."""
        
    def add_animation_to_strip(self, strip_name: str, animation: dict):
        """Dodaje animację do strip."""
        
    def export_current_config(self, path: Path) -> None:
        """Eksportuje konfigurację do pliku YAML."""
```

### 7. Zmiany w strukturze monorepo

```bash
# Struktura plików:
cinemon/
├── blender_addon/
│   ├── __init__.py
│   ├── operators.py
│   ├── panels.py
│   ├── preset_handler.py
│   └── vendor/
│       └── yaml/  # Vendorowany PyYAML
├── src/
│   └── blender/
│       ├── vse_script.py  # Obsługa nowego formatu YAML
│       └── config/
│           └── preset_manager.py  # Rozszerzony o metody add-onu

# Lokalne presety użytkownika:
~/.cinemon/
└── presets/
    ├── simple.yaml  # Przykładowy preset startowy
    └── my-preset.yaml
```

### 8. Zalety tego rozwiązania

- **Szybka wizualizacja**: Zmiany widoczne po kliknięciu Apply
- **Intuicyjny UI**: Wszystko w jednym miejscu w Blenderze
- **Zachowanie kompatybilności**: CLI nadal działa dla batch processing
- **Minimalna implementacja**: Wykorzystuje istniejący kod
- **Elastyczność**: Per-strip animations + global effects

### 9. Implementacja TDD krok po kroku

1. **Faza 1: Vendorowanie PyYAML**
   - Test: Sprawdzenie importu yaml w środowisku Blendera
   - Implementacja: Skopiowanie PyYAML do `vendor/yaml/`
   - Test integracyjny: Ładowanie przykładowego YAML

2. **Faza 2: Nowy format YAML**
   - Test: Parser nowego formatu z grupowaniem per-strip
   - Implementacja: Modyfikacja `YAMLConfigLoader` dla nowego formatu
   - Test: Walidacja schematu i konwersja do struktur danych

3. **Faza 3: Modyfikacja vse_script.py**
   - Test: Mock Blendera ładujący nowy format
   - Implementacja: Obsługa `strip_animations`
   - Test: Aplikowanie animacji per-strip

4. **Faza 4: Podstawowa struktura add-onu**
   - Test: Rejestracja add-onu w Blenderze
   - Implementacja: `__init__.py` z klasami operatorów
   - Test: Sprawdzenie widoczności panelu w VSE

5. **Faza 5: UI Panel - Layout**
   - Test: Tworzenie property group dla layout
   - Implementacja: Panel z kontrolkami layout (type, seed, margin)
   - Test: Zmiana wartości i przechowywanie w pamięci

6. **Faza 6: UI Panel - Kontekstowe animacje**
   - Test: Detekcja aktywnego strip w VSE
   - Implementacja: Dynamiczny panel pokazujący animacje aktywnego strip
   - Test: Dodawanie/usuwanie animacji dla strip

7. **Faza 7: System Apply**
   - Test: Buforowanie zmian przed aplikacją
   - Implementacja: Operator Apply regenerujący animacje
   - Test: Aplikacja tylko dla zmienionych stripów

8. **Faza 8: Preset Manager Integration**
   - Test: Ładowanie presetów z `~/.cinemon/presets/`
   - Implementacja: Dropdown z presetami, Save, Export
   - Test: Zapis i odczyt presetów w nowym formacie

9. **Faza 9: Integracja i przykład**
   - Test E2E: Pełny workflow od załadowania do eksportu
   - Implementacja: Przykładowy preset `simple.yaml`
   - Dokumentacja: Instrukcja instalacji add-onu

### 10. Przykład użycia

```python
# W Blenderze po załadowaniu projektu:

# 1. Użytkownik wybiera strip "Camera1" w timeline VSE
# 2. Panel automatycznie pokazuje animacje dla Camera1
# 3. Użytkownik zmienia intensity dla Scale na 0.5
# 4. Dodaje nową animację Rotation
# 5. Klika "Apply" - animacje są regenerowane
# 6. Klika "Save" aby nadpisać preset lub tworzy nowy
# 7. "Export YAML" zapisuje do katalogu projektu
```

### 11. Przykładowy preset startowy

```yaml
# ~/.cinemon/presets/simple.yaml
project:
  video_files: []  # Auto-detected
  main_audio: null  # Auto-detected
  fps: 30
  resolution: {width: 1920, height: 1080}

layout:
  type: "random"
  config:
    seed: 42
    margin: 0.1
    overlap_allowed: false

strip_animations: {}  # Puste - użytkownik dodaje w UI

audio_analysis:
  file: null  # Auto-detected
```

### 12. Vendorowanie PyYAML

```bash
# Proces vendorowania:
1. Pobierz PyYAML 6.0.1 (kompatybilny z Pythonem w Blenderze 4.3)
2. Skopiuj tylko pure-Python część do vendor/yaml/
3. Dodaj __init__.py z importem relatywnym
4. Test w Blenderze: from .vendor import yaml
```

### 13. Konwencje testowe

- Używamy pytest (jak w reszcie projektu)
- Mockujemy bpy używając istniejącego systemu z conftest.py
- Każda faza ma testy jednostkowe przed implementacją
- Testy integracyjne po każdej fazie

### 14. Rozszerzenia na przyszłość

- Wizualizacja beat/energy events na timeline
- Undo/Redo dla zmian w UI
