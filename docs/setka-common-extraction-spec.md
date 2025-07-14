# Specyfikacja wydzielenia biblioteki setka-common

## 1. Przegląd

### Cel
Wydzielenie współdzielonej biblioteki zarządzania strukturą plików z projektu `obsession` do niezależnego modułu `setka-common`, który będzie używany przez wszystkie submoduły w projekcie setka.

### Zakres
- Generalizacja `RecordingStructure` → `MediaStructure`
- Extrakcja uniwersalnych funkcji zarządzania plikami
- Zachowanie kompatybilności wstecznej dla obsession
- Przygotowanie do integracji z medusa

## 2. Architektura

### 2.1 Struktura repozytoriów

```
setka/                          # Meta-projekt (główne repo)
├── .gitmodules                 # Definicje submodułów
├── setka-common/              # Submoduł - współdzielona biblioteka
├── obsession/                 # Submoduł - OBS Canvas Recorder
├── medusa/                    # Submoduł - Media Upload & Social
└── docs/                      # Dokumentacja meta-projektu
```

### 2.2 Struktura setka-common

```
setka-common/
├── pyproject.toml
├── README.md
├── src/
│   └── setka_common/
│       ├── __init__.py
│       ├── file_structure/
│       │   ├── __init__.py
│       │   ├── base.py              # MediaStructure, StructureManager
│       │   ├── types.py             # MediaType, FileExtensions
│       │   ├── validators.py        # FileValidator, path sanitization
│       │   └── specialized/
│       │       ├── __init__.py
│       │       ├── recording.py     # RecordingStructure (dla obsession)
│       │       └── upload.py        # UploadStructure (dla medusa)
│       └── utils/
│           ├── __init__.py
│           ├── paths.py             # Cross-platform path utilities
│           └── files.py             # File discovery, operations
└── tests/
    ├── test_base_structure.py
    ├── test_file_validators.py
    └── test_specialized/
        ├── test_recording_structure.py
        └── test_upload_structure.py
```

## 3. Plan migracji

### 3.1 Komponenty do wydzielenia z obsession

#### Z `file_structure.py`:

**Do `base.py`:**
- Linie 16-55: `RecordingStructure` → `MediaStructure` (zgeneralizowana)
- Linie 64-110: Podstawowe metody `FileStructureManager` → `StructureManager`
- Linie 196-209: `ensure_extracted_dir` → `ensure_directory`

**Do `types.py`:**
- Definicje rozszerzeń plików (audio_extensions, video_extensions)
- Enum `MediaType` (AUDIO, VIDEO, IMAGE, DOCUMENT)

**Do `files.py`:**
- Linie 232-257: `find_audio_files` (zgeneralizowane)
- Linie 259-283: `find_video_files` (zgeneralizowane)
- Linie 140-151: `create_directory_name` (uniwersalne)

**Do `validators.py`:**
- Walidacja ścieżek i nazw plików
- Sanityzacja nazw dla różnych systemów

**Pozostaje w obsession:**
- Linie 211-230: `ensure_blender_dir` (specyficzne)
- Linie 286-400: Wszystkie funkcje analizy audio
- Specyficzne stałe (METADATA_FILENAME, ANALYSIS_DIRNAME)

### 3.2 Nowe API

```python
# setka_common/file_structure/base.py
from setka_common.file_structure import MediaStructure, StructureManager

# Tworzenie struktury
structure = StructureManager.create_structure(
    media_file="/path/to/video.mp4",
    structure_type="recording",  # lub "upload", "podcast"
    version="2.0"
)

# Uniwersalne operacje
structure.ensure_directory("processed")
audio_files = structure.find_files_by_type(MediaType.AUDIO)
structure.validate()
```

## 4. Zarządzanie branchami

### 4.1 Strategia dla meta-projektu (setka)

```bash
# Główne branche
main          # Stabilna wersja z przypiętymi wersjami submodułów
develop       # Integracja zmian z submodułów
feature/*     # Feature branche dla zmian cross-module

# Workflow
1. Tworzenie feature brancha w setka
2. Aktualizacja .gitmodules jeśli potrzebna
3. Update submodułów do odpowiednich commitów
4. PR do develop → main
```

### 4.2 Strategia dla submodułów

```bash
# Każdy submoduł (obsession, medusa, setka-common)
main          # Stabilna wersja
develop       # Rozwój features
feature/*     # Konkretne funkcjonalności
hotfix/*      # Pilne poprawki

# Workflow dla setka-common
1. feature/extract-file-structure w setka-common
2. feature/use-common-lib w obsession
3. Po merge w obu - update w setka (meta-projekt)
```

### 4.3 Synchronizacja

```bash
# W projekcie setka po zmianach w submodule
git submodule update --remote --merge
git add obsession setka-common
git commit -m "feat: update submodules to use shared library"
```

## 5. Konfiguracja submodułów

### 5.1 Dodanie setka-common jako submodułu

```bash
# W głównym projekcie setka
git submodule add https://github.com/USER/setka-common.git setka-common
git commit -m "feat: add setka-common as submodule"
```

### 5.2 Konfiguracja w obsession

```toml
# obsession/pyproject.toml
[project]
dependencies = [
    "setka-common @ file:///${PROJECT_ROOT}/../setka-common",
    # lub dla development:
    # "setka-common @ git+https://github.com/USER/setka-common.git@develop",
]
```

## 6. Kompatybilność wsteczna

### 6.1 Adapter w obsession

```python
# obsession/src/core/file_structure.py
from setka_common.file_structure.specialized import RecordingStructure as BaseRecordingStructure
from setka_common.file_structure import StructureManager as BaseStructureManager

class RecordingStructure(BaseRecordingStructure):
    """Zachowanie kompatybilności z istniejącym kodem."""
    pass

class FileStructureManager(BaseStructureManager):
    """Rozszerzenie o obsession-specific funkcje."""
    
    METADATA_FILENAME = "metadata.json"
    ANALYSIS_DIRNAME = "analysis"
    
    @staticmethod
    def ensure_blender_dir(recording_dir: Path) -> Path:
        # Implementacja pozostaje w obsession
        ...
```

## 7. Testowanie

### 7.1 Strategia testów

1. **Testy jednostkowe w setka-common**: Pełne pokrycie bazowych funkcji
2. **Testy integracyjne w obsession**: Weryfikacja zachowania po migracji
3. **Testy regresji**: Upewnienie się że istniejące skrypty działają

### 7.2 CI/CD

```yaml
# .github/workflows/test-integration.yml (w setka)
name: Integration Tests
on:
  pull_request:
    branches: [develop, main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - name: Test setka-common
        run: cd setka-common && uv run pytest
      - name: Test obsession with common
        run: cd obsession && uv run pytest
```

## 8. Ryzyka i mitygacja

### Ryzyka
1. **Złamanie kompatybilności**: Istniejące skrypty przestaną działać
2. **Cykliczne zależności**: obsession ↔ setka-common
3. **Wersjonowanie**: Niezgodność wersji między modułami

### Mitygacja
1. **Adapter pattern**: Zachowanie starego API w obsession
2. **Jednokierunkowe zależności**: obsession → setka-common (nie odwrotnie)
3. **Semantic versioning**: Jasne wersjonowanie z pip constraints

## 9. Timeline

- **Tydzień 1**: Utworzenie setka-common, podstawowa struktura
- **Tydzień 2**: Migracja kodu z obsession, testy
- **Tydzień 3**: Integracja, dokumentacja, CI/CD
- **Tydzień 4**: Przygotowanie medusa do użycia biblioteki