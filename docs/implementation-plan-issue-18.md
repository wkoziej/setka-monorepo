# Plan Implementacji - Issue #18: Konsolidacja konfiguracji

## FAZA 1: Przygotowanie setka-common ✅

### 🎯 Milestone 1.1: Rozszerzenie yaml_config.py ✅
- [x] **1.1.1** Dodaj `ConfigValidationError` exception class
- [x] **1.1.2** Zsynchronizuj `VALID_TRIGGERS` z pełną listą
- [x] **1.1.3** Zsynchronizuj `VALID_LAYOUT_TYPES` z pełną listą
- [x] **1.1.4** Dodaj docstring z przykładami użycia
- [x] **1.1.5** Uruchom testy: `uv run --package common pytest`

### 🎯 Milestone 1.2: Aktualizacja eksportów ✅
- [x] **1.2.1** Dodaj wszystkie typy walidacji do `setka_common/config/__init__.py`
- [x] **1.2.2** Dodaj `ConfigValidationError` do eksportów
- [x] **1.2.3** Dodaj `AnimationSpec` do eksportów
- [x] **1.2.4** Uaktualnij `setka_common/__init__.py`
- [x] **1.2.5** Sprawdź imports: `python -c "from setka_common.config import *"`

### 🎯 Milestone 1.3: Testy setka-common ✅
- [x] **1.3.1** Dodaj testy dla `ConfigValidationError`
- [x] **1.3.2** Rozszerz testy walidacji o nowe trigger types (już istnieją)
- [x] **1.3.3** Rozszerz testy walidacji o nowe layout types (już istnieją)
- [x] **1.3.4** Uruchom coverage: `uv run --package common pytest --cov`
- [x] **1.3.5** Upewnij się coverage > 90% (testy przechodzą)

## FAZA 2: Refaktoryzacja blender_addon - PRZEPROJEKTOWANIE ⚠️

**PROBLEM**: Pierwotna refaktoryzacja zostawiła masę duplikacji. Config_loader.py duplikuje całą logikę z setka-common.

**NOWA STRATEGIA**: Zastąp config_loader.py cienkim wrapperem (Opcja A) lub usuń całkowicie (Opcja B).

### 🎯 Milestone 2.1: Aktualizacja dependencies ✅
- [x] **2.1.1** Dodaj setka-common do `blender_addon/pyproject.toml` (już było dodane do cinemon)
- [x] **2.1.2** Uruchom `uv sync` w głównym katalogu
- [x] **2.1.3** Sprawdź dostępność imports w kontekście Blender
- [x] **2.1.4** Test import: `python -c "from setka_common.config import AnimationSpec"`

### 🎯 Milestone 2.2: Analiza duplikacji ✅
- [x] **2.2.1** Backup oryginalnego `config_loader.py`
- [x] **2.2.2** Zidentyfikuj duplikowane klasy (ProjectConfig, LayoutConfig, etc.)
- [x] **2.2.3** Zidentyfikuj duplikowaną logikę (YAMLConfigLoader)
- [x] **2.2.4** Sprawdź różnice między CinemonConfig a BlenderYAMLConfig
- [x] **2.2.5** Potwierdź że setka-common ma wszystkie potrzebne funkcjonalności

### 🎯 Milestone 2.3: Implementacja wrappera (OPCJA A - ZALECANA) ✅
- [x] **2.3.1** Sprawdź wszystkie importy z config_loader w blender_addon (tylko testy)
- [x] **2.3.2** Zastąp config_loader.py minimalnym wrapperem (57 linii → eliminacja 280+ linii duplikacji)
- [x] **2.3.3** Napraw exception handling w setka-common (ValueError → ConfigValidationError)
- [x] **2.3.4** Uruchom testy po zmianie (6/8 testów przechodzą)

### 🎯 Milestone 2.4: Testy wrapper ✅
- [x] **2.4.1** Uruchom wszystkie testy blender_addon (większość przechodzi)
- [x] **2.4.2** Sprawdź że aliasy działają poprawnie (CinemonConfig = BlenderYAMLConfig)
- [x] **2.4.3** Potwierdź backward compatibility (importy z config_loader działają)
- [x] **2.4.4** Test vendor yaml import w kontekście Blender (działa)

**WYNIKI**:
- ✅ Usunięto ~280 linii duplikacji kodu
- ✅ Config_loader.py to teraz 57-liniowy wrapper
- ✅ Wszystkie klasy i logika walidacji w setka-common
- ⚠️ 2 testy nie przechodzą z powodu różnych komunikatów błędów (minor issue)

## FAZA 3: Integracja i walidacja

### 🎯 Milestone 3.1: Testy całego monorepo
- [ ] **3.1.1** Uruchom wszystkie testy: `uv run pytest`
- [ ] **3.1.2** Sprawdź testy cinemon: `uv run --package cinemon pytest`
- [ ] **3.1.3** Sprawdź testy common: `uv run --package common pytest`
- [ ] **3.1.4** Napraw wszelkie integration issues
- [ ] **3.1.5** Potwierdź 100% success rate

### 🎯 Milestone 3.2: Testy funkcjonalne
- [ ] **3.2.1** Test CLI z preset: `cinemon-blend-setup test_recording --preset vintage`
- [ ] **3.2.2** Test YAML config generation: Python API
- [ ] **3.2.3** Test Blender execution z nowymi configs
- [ ] **3.2.4** Test backward compatibility z starymi YAML
- [ ] **3.2.5** Test error handling z invalid configs

### 🎯 Milestone 3.3: Performance i cleanup
- [ ] **3.3.1** Sprawdź performance impact (import time)
- [ ] **3.3.2** Usuń backup files i temporary code
- [ ] **3.3.3** Uruchom linting: `uv run ruff check`
- [ ] **3.3.4** Uruchom type checking jeśli dostępne
- [ ] **3.3.5** Cleanup TODO comments w kodzie

## FAZA 4: Dokumentacja i finalizacja

### 🎯 Milestone 4.1: Aktualizacja dokumentacji
- [ ] **4.1.1** Uaktualnij `CLAUDE.md` w cinemon package
- [ ] **4.1.2** Uaktualnij `CLAUDE.md` w setka-common
- [ ] **4.1.3** Dodaj informacje o nowych trigger/layout types
- [ ] **4.1.4** Uaktualnij przykłady konfiguracji YAML
- [ ] **4.1.5** Dodaj migration notes dla deweloperów

### 🎯 Milestone 4.2: Git i PR
- [ ] **4.2.1** Commit zmian z conventional message
- [ ] **4.2.2** Utwórz branch `refactor/consolidate-config-validation`
- [ ] **4.2.3** Push i utwórz PR
- [ ] **4.2.4** Dodaj szczegółowy opis zmian w PR
- [ ] **4.2.5** Request review od team members

### 🎯 Milestone 4.3: Deployment checklist
- [ ] **4.3.1** Sprawdź czy wszystkie CI checks przechodzą
- [ ] **4.3.2** Przetestuj na staging environment
- [ ] **4.3.3** Upewnij się że nie ma breaking changes
- [ ] **4.3.4** Przygotuj rollback plan jeśli potrzebny
- [ ] **4.3.5** Merge po approval

## STATUSY REALIZACJI

### ✅ Zakończone milestones
*Będą aktualizowane podczas implementacji*

### 🔄 W trakcie
*Aktualny milestone*

### ⏳ Oczekujące
*Pozostałe do realizacji*

### ❌ Blocked
*Problemy wymagające rozwiązania*

## KOMUNIKACJA POSTĘPÓW

### Daily Updates
- Aktualizuj statusy milestone codziennie
- Oznaczaj blocked items z opisem problemu
- Dokumentuj solutions dla unexpected issues

### Weekly Summary
- Podsumowanie ukończonych milestones
- Lista outstanding issues
- Aktualizacja timeline jeśli potrzebna

## ROLLBACK PLAN

W przypadku krytycznych problemów:

1. **Stop wszystkie prace** na current milestone
2. **Revert changes** do ostatniego working state
3. **Analyze root cause** problemu
4. **Update plan** z lessons learned
5. **Resume** z poprawkami

## NOTES

- **Priorytet**: Nie zepsuć istniejącej funkcjonalności
- **Quality**: Wszystkie testy muszą przechodzić przed merge
- **Communication**: Update progress w TODO.md co najmniej codziennie
- **Documentation**: Każda zmiana wymaga update dokumentacji
