# TODO: Implementacja biblioteki setka-common

## Faza 1: Przygotowanie infrastruktury (Dzień 1-2)

- [ ] **SETKA-001**: Utworzenie nowego repozytorium `setka-common` na GitHub
- [ ] **SETKA-002**: Inicjalizacja projektu Python z uv (`uv init`)
- [ ] **SETKA-003**: Konfiguracja pyproject.toml (dependencies, dev-dependencies, build)
- [ ] **SETKA-004**: Dodanie setka-common jako submoduł w projekcie setka
- [ ] **SETKA-005**: Konfiguracja pre-commit hooks (black, mypy, ruff)
- [ ] **SETKA-006**: Setup GitHub Actions dla CI/CD
- [ ] **SETKA-007**: Utworzenie podstawowej struktury katalogów

## Faza 2: Ekstrakcja kodu z obsession (Dzień 3-5)

### Podstawowe komponenty
- [ ] **SETKA-008**: Utworzenie `base.py` z klasą `MediaStructure`
- [ ] **SETKA-009**: Implementacja `StructureManager` (podstawowe metody)
- [ ] **SETKA-010**: Utworzenie `types.py` z enum `MediaType` i stałymi rozszerzeń
- [ ] **SETKA-011**: Implementacja `validators.py` dla walidacji ścieżek
- [ ] **SETKA-012**: Utworzenie `files.py` z funkcjami find_files_by_type

### Wyspecjalizowane struktury
- [ ] **SETKA-013**: Implementacja `specialized/recording.py` dla obsession
- [ ] **SETKA-014**: Szkielet `specialized/upload.py` dla medusa (placeholder)
- [ ] **SETKA-015**: Dodanie konfigurowalnych typów struktur

### Utilities
- [ ] **SETKA-016**: Implementacja `utils/paths.py` (cross-platform)
- [ ] **SETKA-017**: Implementacja `utils/files.py` (operacje na plikach)

## Faza 3: Testy jednostkowe (Dzień 6-7)

- [ ] **SETKA-018**: Testy dla `MediaStructure` (test_base_structure.py)
- [ ] **SETKA-019**: Testy dla `StructureManager` 
- [ ] **SETKA-020**: Testy dla `FileValidator` (test_file_validators.py)
- [ ] **SETKA-021**: Testy dla `RecordingStructure` (test_recording_structure.py)
- [ ] **SETKA-022**: Testy dla utilities (paths, files)
- [ ] **SETKA-023**: Fixture'y i pomocnicze funkcje testowe
- [ ] **SETKA-024**: Pokrycie kodu minimum 90%

## Faza 4: Migracja obsession (Dzień 8-10)

### Branch work
- [ ] **SETKA-025**: Utworzenie brancha `feature/use-common-lib` w obsession
- [ ] **SETKA-026**: Update pyproject.toml w obsession (dependency na setka-common)

### Refaktoryzacja
- [ ] **SETKA-027**: Utworzenie adaptera `FileStructureManager` w obsession
- [ ] **SETKA-028**: Zachowanie obsession-specific metod (blender, audio)
- [ ] **SETKA-029**: Update importów we wszystkich modułach obsession
- [ ] **SETKA-030**: Migracja testów do używania setka-common

### Weryfikacja
- [ ] **SETKA-031**: Uruchomienie wszystkich testów obsession
- [ ] **SETKA-032**: Test CLI commands (extract, blend_setup, analyze_audio)
- [ ] **SETKA-033**: Weryfikacja kompatybilności wstecznej
- [ ] **SETKA-034**: Update dokumentacji w obsession

## Faza 5: Integracja w meta-projekcie (Dzień 11-12)

- [ ] **SETKA-035**: Update .gitmodules w setka
- [ ] **SETKA-036**: Utworzenie brancha `feature/common-lib-integration`
- [ ] **SETKA-037**: Update submodułów do właściwych commitów
- [ ] **SETKA-038**: Konfiguracja GitHub Actions dla testów integracyjnych
- [ ] **SETKA-039**: Test pełnego workflow (obsession + setka-common)

## Faza 6: Dokumentacja (Dzień 13-14)

- [ ] **SETKA-040**: README.md dla setka-common
- [ ] **SETKA-041**: Dokumentacja API (docstrings)
- [ ] **SETKA-042**: Przykłady użycia dla obsession
- [ ] **SETKA-043**: Przykłady użycia dla medusa
- [ ] **SETKA-044**: Migration guide dla istniejących projektów
- [ ] **SETKA-045**: Update głównego README w setka

## Faza 7: Release i deployment (Dzień 15)

- [ ] **SETKA-046**: Code review wszystkich zmian
- [ ] **SETKA-047**: Merge feature branches do develop
- [ ] **SETKA-048**: Testing na develop branch
- [ ] **SETKA-049**: Utworzenie release v0.1.0 dla setka-common
- [ ] **SETKA-050**: Update wersji w meta-projekcie setka
- [ ] **SETKA-051**: Merge do main branches
- [ ] **SETKA-052**: Tag releases

## Faza 8: Przygotowanie medusa (Przyszłość)

- [ ] **SETKA-053**: Analiza wymagań medusa dla file structure
- [ ] **SETKA-054**: Implementacja `UploadStructure` w setka-common
- [ ] **SETKA-055**: Integracja medusa z setka-common
- [ ] **SETKA-056**: Testy cross-module (obsession → medusa flow)

## Notatki implementacyjne

### Konwencje nazewnictwa branch'y
- `feature/extract-file-structure` - w setka-common
- `feature/use-common-lib` - w obsession
- `feature/common-lib-integration` - w setka (meta)

### Priorytety
- **Krytyczne**: SETKA-001 do SETKA-024 (podstawowa biblioteka)
- **Wysokie**: SETKA-025 do SETKA-034 (migracja obsession)
- **Średnie**: SETKA-035 do SETKA-045 (integracja i docs)
- **Niskie**: SETKA-046 do SETKA-056 (release i przyszłość)

### Definicja ukończenia (DoD)
- [ ] Kod napisany i przetestowany
- [ ] Testy jednostkowe przechodzą
- [ ] Dokumentacja zaktualizowana
- [ ] Code review wykonany
- [ ] CI/CD przechodzi

### Metryki sukcesu
- Zero breaking changes w obsession
- Pokrycie testów > 90% w setka-common
- Wszystkie istniejące skrypty CLI działają
- Czas migracji < 2 tygodnie