# Refaktoryzacja Issue #18: Konsolidacja konfiguracji blender_addon

## Problem

Blender addon ma duplikowany kod walidacji konfiguracji YAML który konflikuje z `setka-common`. Prowadzi to do:

- Różnych definicji `VALID_ANIMATION_TYPES`, `VALID_TRIGGER_TYPES` i `VALID_LAYOUT_TYPES`
- Różnych implementacji `AnimationSpec` (dict vs TypedDict)
- Różnych mechanizmów exception handling (ValidationError vs ValueError)
- Trudności w utrzymaniu spójności między pakietami
- Błędów testów przy niezgodnych typach

## Cel refaktoryzacji

Utworzenie **jednego punktu prawdy** dla konfiguracji YAML przez:
1. Konsolidację logiki walidacji w `setka-common`
2. Refaktoryzację `blender_addon` do importowania z `setka-common`
3. Usunięcie duplikacji kodu
4. Zapewnienie spójności typów między pakietami

## Architektura docelowa

### Przed refaktoryzacją
```
blender_addon/config_loader.py
├── VALID_ANIMATION_TYPES (duplikat)
├── VALID_TRIGGER_TYPES (duplikat)
├── VALID_LAYOUT_TYPES (duplikat)
├── ValidationError (niestandardowy)
├── AnimationSpec (dict)
├── ProjectConfig (duplikat)
├── LayoutConfig (duplikat)
├── AudioAnalysisConfig (duplikat)
├── CinemonConfig (duplikat)
└── YAMLConfigLoader (duplikuje całą logikę)

setka-common/yaml_config.py
├── VALID_ANIMATION_TYPES (oryginał)
├── VALID_TRIGGERS (oryginał)
├── VALID_LAYOUT_TYPES (oryginał)
├── ConfigValidationError (standard)
├── AnimationSpec (TypedDict)
├── ProjectConfig (oryginał)
├── AudioAnalysisConfig (oryginał)
├── LayoutConfig (oryginał)
├── BlenderYAMLConfig (oryginał)
└── YAMLConfigLoader (oryginał)
```

### Po refaktoryzacji - Opcja A (minimalny wrapper)
```
setka-common/yaml_config.py
└── Wszystkie klasy i logika (jeden punkt prawdy)

blender_addon/config_loader.py
└── Cienki wrapper tylko dla kompatybilności wstecznej:
    ├── from setka_common.config import *
    ├── CinemonConfig = BlenderYAMLConfig (alias)
    └── vendor yaml import dla Blender
```

### Po refaktoryzacji - Opcja B (pełne usunięcie)
```
setka-common/yaml_config.py
└── Wszystkie klasy i logika (jeden punkt prawdy)

blender_addon/config_loader.py - USUNIĘTY
└── Wszystkie importy zmienione na setka_common.config
```

## Różnice do zsynchronizowania

### Trigger Types
- **blender_addon**: `"beat", "energy_peaks", "one_time", "bass", "treble"`
- **setka-common**: `"bass", "beat", "energy_peaks", "one_time", "continuous", "sections", "treble"`
- **Rozwiązanie**: Użyj pełnej listy z setka-common

### Layout Types
- **blender_addon**: `"random", "grid", "cascade", "manual"`
- **setka-common**: `"random", "grid", "center", "fill", "main-pip", "cascade", "manual"`
- **Rozwiązanie**: Użyj pełnej listy z setka-common

### Exception Handling
- **blender_addon**: `ValidationError`
- **setka-common**: `ValueError`
- **Rozwiązanie**: Utwórz wspólny `ConfigValidationError` w setka-common

## Strategia implementacji

### Opcja A - Minimalny wrapper (ZALECANA)
Zachowuje kompatybilność wsteczną, mniej ryzykowna.

#### Faza 1: Przygotowanie setka-common
1. Dodaj `ConfigValidationError` do setka-common
2. Wyeksportuj wszystkie typy walidacji w `__init__.py`
3. Upewnij się że `BlenderYAMLConfig` ma wszystkie potrzebne pola
4. Uaktualnij testy setka-common

#### Faza 2: Refaktoryzacja blender_addon do wrappera
1. Zastąp całą zawartość config_loader.py minimalnym wrapperem
2. Import wszystkiego z setka-common
3. Alias `CinemonConfig = BlenderYAMLConfig`
4. Zachowaj tylko vendor yaml import dla Blender
5. Uaktualnij testy blender_addon

#### Faza 3: Walidacja
1. Uruchom testy całego monorepo
2. Przetestuj integrację Blender+YAML
3. Sprawdź że wszystkie importy działają

### Opcja B - Pełne usunięcie
Bardziej radykalna, wymaga zmian we wszystkich plikach importujących.

#### Faza 1: Przygotowanie setka-common (jak wyżej)

#### Faza 2: Usunięcie config_loader.py
1. Znajdź wszystkie importy z config_loader
2. Zmień na importy z setka_common.config
3. Usuń config_loader.py
4. Uaktualnij wszystkie testy

#### Faza 3: Walidacja (jak wyżej)

## Wpływ na istniejący kod

### Pliki do modyfikacji
- `packages/common/src/setka_common/config/yaml_config.py`
- `packages/common/src/setka_common/config/__init__.py`
- `packages/cinemon/blender_addon/config_loader.py`
- `packages/cinemon/blender_addon/pyproject.toml` (dependencies)
- Testy w obu pakietach

### Backward Compatibility
- API publiczne pozostaną bez zmian
- Istniejące YAML configs będą kompatybilne
- CLI zachowa wszystkie funkcjonalności

## Korzyści

1. **Jednolity kod**: Jeden punkt prawdy dla wszystkich typów animacji
2. **Łatwiejsze utrzymanie**: Zmiany w jednym miejscu
3. **Spójność typów**: Brak konfliktów między pakietami
4. **Lepsza testabilność**: Wspólne testy walidacji
5. **Przyszła rozszerzalność**: Łatwiejsze dodawanie nowych typów

## Ryzyka i mitigation

### Ryzyko: Zepsucie integracji Blender
- **Mitigation**: Obszerne testy przed merge
- **Plan B**: Revert i gradual migration

### Ryzyko: Problemy z zależnościami w Blender
- **Mitigation**: Sprawdź import paths w środowisku Blender
- **Plan B**: Vendor setka-common w blender_addon

### Ryzyko: Backward compatibility
- Nie przejmuj się tym. Brak fallbacków

## Kryteria akceptacji

- [ ] Wszystkie testy przechodzą w obu pakietach
- [ ] Blender addon importuje z setka-common bez błędów
- [ ] Istniejące YAML configs działają bez zmian
- [ ] CLI zachowuje pełną funkcjonalność
- [ ] Dokumentacja zaktualizowana
- [ ] Brak duplikacji kodu walidacji
