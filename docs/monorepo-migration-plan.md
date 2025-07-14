# Plan migracji Setka do Monorepo

## 1. Przegląd migracji

Migracja z obecnej struktury (meta-projekt z submodułami) do monorepo z uv workspace, zachowując historię Git.

### Obecna struktura:
```
setka/                    # Meta-projekt
├── obsession/           # Submoduł
└── medusa/              # Submoduł
```

### Docelowa struktura:
```
setka/                    # Monorepo
├── packages/
│   ├── common/          # Nowy pakiet (wydzielony z obsession)
│   ├── obsession/       # Zmigrowany z submodułu
│   └── medusa/          # Zmigrowany z submodułu
└── pyproject.toml       # Workspace root
```

## 2. Plan krok po kroku

### Faza 1: Przygotowanie (30 min)

#### 1.1 Backup
```bash
# Zrób backup wszystkiego
cd ~/dev
tar -czf setka-backup-$(date +%Y%m%d).tar.gz setka/
```

#### 1.2 Utworzenie nowego repo
```bash
# Utwórz nowe monorepo
mkdir setka-monorepo
cd setka-monorepo
git init
```

### Faza 2: Migracja historii Git (1-2h)

#### 2.1 Import obsession z historią
```bash
# Użyj git subtree aby zachować historię
git subtree add --prefix=packages/obsession \
  https://github.com/USER/obsession.git main \
  --squash
```

#### 2.2 Import medusa z historią
```bash
git subtree add --prefix=packages/medusa \
  https://github.com/USER/medusa.git main \
  --squash
```

#### 2.3 Kopiuj pozostałe pliki z meta-projektu
```bash
# Kopiuj dokumentację i pliki konfiguracyjne
cp -r ../setka/docs ./
cp ../setka/README.md ./
cp ../setka/.gitignore ./
```

### Faza 3: Konfiguracja workspace (30 min)

#### 3.1 Utworzenie root pyproject.toml
```bash
cat > pyproject.toml << 'EOF'
[tool.uv]
package = false

[tool.uv.workspace]
members = ["packages/*"]

[project]
name = "setka-workspace"
version = "1.0.0"
description = "Setka media processing and automation workspace"
requires-python = ">=3.10"

[tool.uv.sources]
setka-common = { workspace = true }
obsession = { workspace = true }
medusa = { workspace = true }
EOF
```

#### 3.2 Dostosowanie pyproject.toml w pakietach

**packages/obsession/pyproject.toml:**
```toml
[project]
name = "obsession"
# ... existing config ...
dependencies = [
    "setka-common",  # Lokalny pakiet
    # ... other deps ...
]
```

**packages/medusa/pyproject.toml:**
```toml
[project]
name = "medusa"
# ... existing config ...
dependencies = [
    "setka-common",  # Przyszła zależność
    # ... other deps ...
]
```

### Faza 4: Utworzenie setka-common (2-3h)

#### 4.1 Struktura pakietu
```bash
mkdir -p packages/common/{src/setka_common,tests}
cd packages/common
```

#### 4.2 pyproject.toml dla common
```bash
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "setka-common"
version = "0.1.0"
description = "Common utilities for Setka media processing"
requires-python = ">=3.10"
dependencies = [
    "pathlib-extensions>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]
EOF
```

#### 4.3 Migracja kodu z obsession
```bash
# To będzie ręczna praca - wydzielenie file_structure.py
# Szczegóły w sekcji "Wydzielenie kodu"
```

### Faza 5: Refaktoryzacja obsession (2-3h)

#### 5.1 Usunięcie zduplikowanego kodu
- Usuń `file_structure.py` z obsession
- Zastąp importy na `from setka_common.file_structure import ...`

#### 5.2 Update testów
- Dostosuj testy do nowych importów
- Usuń testy dla przeniesionych funkcji

### Faza 6: Setup i weryfikacja (1h)

#### 6.1 Instalacja workspace
```bash
cd ~/dev/setka-monorepo
uv sync
```

#### 6.2 Uruchomienie testów
```bash
# Test wszystkich pakietów
uv run pytest

# Test pojedynczego pakietu
uv run --package obsession pytest
uv run --package medusa pytest
uv run --package setka-common pytest
```

#### 6.3 Weryfikacja CLI
```bash
# Sprawdź czy CLI działa
uv run --package obsession python -m cli.extract --help
```

### Faza 7: Migracja CI/CD (30 min)

#### 7.1 GitHub Actions
```yaml
# .github/workflows/test.yml
name: Test All Packages
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run pytest --cov
```

### Faza 8: Cleanup i finalizacja (30 min)

#### 8.1 Update README
- Opisz nową strukturę monorepo
- Dodaj instrukcje dla developmentu

#### 8.2 Archiwizacja starych repo
```bash
# Dodaj note do README w starych repo
echo "# ARCHIVED - Moved to monorepo" > README.md
echo "This project has been moved to: https://github.com/USER/setka" >> README.md
```

## 3. Wydzielenie kodu do setka-common

### Co przenieść z obsession/src/core/file_structure.py:

```python
# packages/common/src/setka_common/file_structure/base.py
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import json

@dataclass
class MediaStructure:
    """Uniwersalna struktura dla projektów mediów."""
    project_dir: Path
    media_file: Path
    metadata_file: Path
    processed_dir: Path
    
    def exists(self) -> bool:
        """Sprawdza czy struktura istnieje."""
        return all([
            self.project_dir.exists(),
            self.media_file.exists(),
            self.processed_dir.exists()
        ])

class StructureManager:
    """Zarządca struktur mediów."""
    
    METADATA_FILENAME = "metadata.json"
    PROCESSED_DIRNAME = "processed"
    
    @staticmethod
    def create_structure(media_path: Path, structure_type: str = "generic") -> MediaStructure:
        """Tworzy strukturę dla pliku mediów."""
        # ... implementacja ...
```

```python
# packages/common/src/setka_common/file_structure/types.py
from enum import Enum
from typing import List

class MediaType(Enum):
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    
class FileExtensions:
    AUDIO = [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"]
    VIDEO = [".mp4", ".mkv", ".avi", ".mov", ".webm"]
    IMAGE = [".jpg", ".png", ".gif", ".webp"]
```

```python
# packages/common/src/setka_common/utils/files.py
from pathlib import Path
from typing import List
from ..file_structure.types import MediaType, FileExtensions

def find_files_by_type(directory: Path, media_type: MediaType) -> List[Path]:
    """Znajduje pliki danego typu w katalogu."""
    extensions = {
        MediaType.AUDIO: FileExtensions.AUDIO,
        MediaType.VIDEO: FileExtensions.VIDEO,
        MediaType.IMAGE: FileExtensions.IMAGE,
    }[media_type]
    
    files = []
    if directory.exists():
        for ext in extensions:
            files.extend(directory.glob(f"*{ext}"))
    
    return sorted(files)
```

### Co zostaje w obsession:

```python
# packages/obsession/src/core/obsession_structure.py
from setka_common.file_structure import MediaStructure, StructureManager
from pathlib import Path

class ObsessionStructure(MediaStructure):
    """Rozszerzenie dla projektów OBS."""
    extracted_dir: Path
    blender_dir: Path
    analysis_dir: Path

class ObsessionStructureManager(StructureManager):
    """Manager specific dla obsession."""
    
    EXTRACTED_DIRNAME = "extracted"
    BLENDER_DIRNAME = "blender"
    ANALYSIS_DIRNAME = "analysis"
    
    @staticmethod
    def ensure_blender_dir(recording_dir: Path) -> Path:
        """Tworzy katalog blender/ (specific dla obsession)."""
        # ... implementacja ...
```

## 4. Skrypt migracyjny

Utworzę automatyczny skrypt w następnym kroku.

## 5. Timeline

- **Dzień 1 (4-6h)**:
  - Migracja do monorepo
  - Utworzenie setka-common
  - Refaktoryzacja obsession
  
- **Dzień 2 (2-3h)**:
  - Testy i poprawki
  - CI/CD
  - Dokumentacja

## 6. Checklist

- [ ] Backup wszystkich repo
- [ ] Utworzenie monorepo z historią
- [ ] Konfiguracja uv workspace
- [ ] Utworzenie packages/common
- [ ] Migracja kodu do common
- [ ] Refaktoryzacja obsession
- [ ] Wszystkie testy przechodzą
- [ ] CI/CD działa
- [ ] README zaktualizowane
- [ ] Stare repo zarchiwizowane

## 7. Użycie skryptów

### 7.1 Automatyczna migracja:
```bash
cd /home/wojtas/dev/setka
./scripts/migrate-to-monorepo.sh
```

### 7.2 Ekstrakcja kodu do setka-common:
```bash
# Po uruchomieniu migrate-to-monorepo.sh
./scripts/extract-common-code.py
```

### 7.3 Weryfikacja:
```bash
cd ~/dev/setka-monorepo
uv sync
uv run pytest
```

### 7.4 Struktura po migracji:
```
setka-monorepo/
├── packages/
│   ├── common/
│   │   ├── src/setka_common/
│   │   │   ├── file_structure/
│   │   │   │   ├── base.py           # MediaStructure, StructureManager
│   │   │   │   ├── types.py          # MediaType, FileExtensions
│   │   │   │   └── specialized/
│   │   │   │       └── recording.py  # RecordingStructure
│   │   │   └── utils/
│   │   │       └── files.py          # find_files_by_type
│   │   └── tests/
│   ├── obsession/                    # Zmigrowany projekt
│   └── medusa/                       # Zmigrowany projekt  
├── .github/workflows/test.yml        # CI/CD
└── pyproject.toml                    # uv workspace
```