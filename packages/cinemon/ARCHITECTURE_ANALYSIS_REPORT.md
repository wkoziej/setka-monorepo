# Raport Analizy Architektury Cinemon

## Podsumowanie wykonawcze

Analiza architektury pakietu Cinemon wykazała znaczące słabości strukturalne związane z zarządzaniem zależnościami między środowiskiem VSE script (CLI) a addon (GUI), obsługą konfiguracji YAML oraz integracją systemu presetów. Główne problemy wynikają z ograniczeń środowiska Python w Blenderze oraz nadmiernej złożoności przepływu danych między komponentami.

## 1. Architektura systemu

### 1.1 Komponenty główne

- **CLI (blend_setup.py)**: Punkt wejścia dla użytkownika, generuje konfiguracje YAML
- **ProjectManager**: Zarządza tworzeniem projektów Blender, uruchamia VSE script
- **VSE Script (vse_script.py)**: Wykonywany w tle przez Blender, stosuje konfiguracje
- **Addon (blender_addon/)**: Interfejs GUI w Blenderze, duplikuje część funkcjonalności
- **Unified API**: Próba zunifikowania logiki animacji między VSE a addon

### 1.2 Przepływ danych

```
Użytkownik → CLI → ProjectManager → Blender (background) → VSE Script
                                                         ↓
                                                    Unified API
                                                         ↑
                                    Addon (GUI) ←────────┘
```

## 2. Słabe punkty architektury

### 2.1 Zarządzanie środowiskiem Python

**Problem**: Blender używa izolowanego środowiska Python, ignorując PYTHONPATH i instalacje systemowe.

**Objawy**:
- Konieczność vendorowania PyYAML w addon (duplikacja kodu)
- Skomplikowane importy z fallbackami (relative vs absolute)
- Problemy z odnajdywaniem modułów setka_common

**Przykład kodu** (unified_api.py:40-47):
```python
try:
    from .strip_context import get_strip_context_manager
except ImportError:
    # Fallback to absolute imports (background mode)
    from strip_context import get_strip_context_manager
```

### 2.2 Duplikacja logiki preset/konfiguracja

**Problem**: System presetów istnieje w trzech miejscach:
1. Python PresetManager (src/blender/config/preset_manager.py)
2. Addon example_presets (blender_addon/example_presets/*.yaml)
3. Runtime generowane konfiguracje (animation_config_*.yaml)

**Konsekwencje**:
- Rozbieżności w definicjach presetów
- Nadmiarowe mapowanie nazw (Video_X → rzeczywiste nazwy)
- Skomplikowany proces konwersji formatów

### 2.3 Konwersja formatów konfiguracji

**Problem**: Wielokrotne konwersje między formatami:
1. Preset YAML (strip_animations) → Internal format (animations)
2. Internal → Temporary YAML dla VSE script
3. YAML → JSON metadata dla auto-loading

**Kod problematyczny** (vse_script.py:83-106):
```python
if "strip_animations" in raw_config:
    # Convert grouped format to internal
    with tempfile.NamedTemporaryFile(...) as temp_file:
        yaml.dump(raw_config, temp_file)
        config_obj = loader.load_config(Path(temp_path))
        self.config_data = loader.convert_to_internal(config_obj)
```

### 2.4 Rozdzielenie VSE script vs Addon

**Problem**: Dwa różne konteksty wykonania z różnymi ograniczeniami:
- VSE script: Brak GUI, wykonanie w tle, pełny dostęp do sys.path
- Addon: GUI obecne, ograniczone środowisko, vendorowane zależności

**Objawy**:
- Duplikacja kodu animacji (częściowo rozwiązana przez Unified API)
- Różne ścieżki importów
- Problemy z wykrywaniem dostępnych modułów

### 2.5 Zarządzanie stanem i synchronizacja

**Problem**: Brak jednolitego zarządzania stanem między komponentami:
- StripContextManager trzyma stan lokalnie w addon
- VSE script nie ma dostępu do kontekstu addon
- Metadata JSON jako workaround dla przekazywania informacji

### 2.6 Obsługa ścieżek plików

**Problem**: Nadmierna złożoność rozwiązywania ścieżek względnych:
- Różne konteksty (config dir, recording dir, extracted dir)
- Wielokrotne próby odnalezienia plików
- Brak jednolitej abstrakcji

**Przykład** (vse_script.py:386-414):
```python
if not analysis_path.is_absolute():
    # Try relative to config directory first
    # Try relative to recording directory
    # Try relative to video directory
```

## 3. Propozycje rozwiązań

### 3.1 Unifikacja środowiska wykonawczego

**Rozwiązanie**: Stworzenie pojedynczego punktu wykonania z jasnym podziałem odpowiedzialności.

```python
# Proponowana struktura
class CinemonExecutor:
    def __init__(self, mode: Literal['cli', 'gui']):
        self.mode = mode
        self.config_manager = UnifiedConfigManager()
        self.animation_engine = AnimationEngine()
    
    def execute(self, config_path: Path):
        config = self.config_manager.load(config_path)
        if self.mode == 'cli':
            self._execute_background(config)
        else:
            self._execute_gui(config)
```

### 3.2 Jednolity system konfiguracji

**Rozwiązanie**: Użycie pojedynczego formatu konfiguracji bez konwersji.

```yaml
# Uniwersalny format
version: "2.0"
mode: "unified"
strips:  # Zamiast strip_animations
  - name: "Camera1"  # Explicit names zamiast Video_X
    animations:
      - type: "scale"
        trigger: "beat"
```

### 3.3 Abstrakcja zarządzania zależnościami

**Rozwiązanie**: Stworzenie warstwy abstrakcji dla importów.

```python
# dependency_manager.py
class DependencyManager:
    @staticmethod
    def import_module(module_name: str, package: str = None):
        strategies = [
            lambda: importlib.import_module(f".{module_name}", package),
            lambda: importlib.import_module(module_name),
            lambda: __import__(module_name)
        ]
        
        for strategy in strategies:
            try:
                return strategy()
            except ImportError:
                continue
        raise ImportError(f"Cannot import {module_name}")
```

### 3.4 Uproszczenie systemu presetów

**Rozwiązanie**: Centralizacja definicji presetów w jednym miejscu.

```python
# unified_presets.py
PRESET_REGISTRY = PresetRegistry()

@PRESET_REGISTRY.register("vintage")
def vintage_preset():
    return {
        "layout": {...},
        "animations": [...]
    }
```

### 3.5 Eliminacja tymczasowych plików

**Rozwiązanie**: Przekazywanie konfiguracji w pamięci zamiast przez pliki tymczasowe.

```python
# Zamiast tworzenia temp file
class BlenderBridge:
    def execute_with_config(self, config: dict):
        # Serialize to base64 and pass as argument
        config_b64 = base64.b64encode(
            json.dumps(config).encode()
        ).decode()
        
        subprocess.run([
            "blender", "--python", "script.py",
            "--", "--config-b64", config_b64
        ])
```

### 3.6 Vendor management strategy

**Rozwiązanie**: Stworzenie jednolitego systemu zarządzania vendorowanymi zależnościami.

```python
# vendor_manager.py
class VendorManager:
    VENDOR_DEPS = {
        'yaml': '6.0',
        'numpy': '1.24.0'
    }
    
    @classmethod
    def ensure_dependencies(cls):
        vendor_path = Path(__file__).parent / 'vendor'
        sys.path.insert(0, str(vendor_path))
        
        for dep, version in cls.VENDOR_DEPS.items():
            cls._verify_import(dep, version)
```

## 4. Rekomendacje priorytetowe

### Krótkoterminowe (1-2 tygodnie)
1. **Ujednolicenie importów**: Stworzenie DependencyManager dla wszystkich importów
2. **Uproszczenie konwersji**: Eliminacja zbędnych konwersji formatów konfiguracji
3. **Dokumentacja ścieżek**: Jasne określenie kontekstów dla rozwiązywania ścieżek

### Średnioterminowe (1-2 miesiące)
1. **Refaktoryzacja presetów**: Migracja do jednolitego systemu z rejestrem
2. **Eliminacja duplikacji**: Pełne przeniesienie logiki animacji do Unified API
3. **Testy integracyjne**: Pokrycie testami przepływu CLI → VSE → Addon

### Długoterminowe (3-6 miesięcy)
1. **Przeprojektowanie architektury**: Rozważenie architektury plugin-based
2. **Standalone mode**: Możliwość działania bez Blendera dla development/testing
3. **API stabilization**: Stworzenie stabilnego API dla rozszerzeń

## 5. Ryzyka i mitygacje

### Ryzyka
1. **Breaking changes**: Zmiany mogą złamać istniejące workflow
2. **Blender updates**: Zmiany w Blender API mogą wymagać dostosowań
3. **Performance**: Uproszczenia mogą wpłynąć na wydajność

### Mitygacje
1. **Versioning**: Wprowadzenie wersjonowania konfiguracji
2. **Compatibility layer**: Warstwa kompatybilności dla starych formatów
3. **Profiling**: Regularne profilowanie wydajności

## Podsumowanie

Architektura Cinemon cierpi na nadmierną złożoność wynikającą z próby pogodzenia ograniczeń środowiska Blender z wymogami elastycznego systemu konfiguracji. Kluczowe jest uproszczenie przepływu danych, eliminacja duplikacji kodu oraz stworzenie jednolitej abstrakcji dla zarządzania zależnościami. Proponowane rozwiązania powinny być wdrażane iteracyjnie, z zachowaniem kompatybilności wstecznej w okresie przejściowym.