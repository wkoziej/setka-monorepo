#!/bin/bash
# Skrypt migracji Setka do monorepo
# Autor: Wojtas
# Data: 2025-01-14

set -euo pipefail

# Kolory dla output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funkcje pomocnicze
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Sprawdzenie zależności
check_dependencies() {
    log "Sprawdzam zależności..."
    
    for cmd in git uv jq; do
        if ! command -v $cmd &> /dev/null; then
            error "$cmd nie jest zainstalowany!"
            exit 1
        fi
    done
    
    log "Wszystkie zależności są dostępne."
}

# Konfiguracja
ORIGINAL_DIR=$(pwd)
BACKUP_DIR="${HOME}/setka-backup-$(date +%Y%m%d-%H%M%S)"
MONOREPO_DIR="${HOME}/dev/setka-monorepo"
GITHUB_USER=${GITHUB_USER:-"USER"}  # Ustaw swoją nazwę użytkownika

# Główna funkcja migracji
main() {
    log "=== Rozpoczynam migrację Setka do monorepo ==="
    
    check_dependencies
    
    # 1. Backup
    log "Tworzę backup w: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    cp -r "$ORIGINAL_DIR" "$BACKUP_DIR/"
    
    # 2. Tworzenie monorepo
    log "Tworzę nowe monorepo w: $MONOREPO_DIR"
    if [ -d "$MONOREPO_DIR" ]; then
        warning "Katalog $MONOREPO_DIR już istnieje!"
        read -p "Czy chcesz go usunąć i kontynuować? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$MONOREPO_DIR"
        else
            error "Przerwano migrację."
            exit 1
        fi
    fi
    
    mkdir -p "$MONOREPO_DIR"
    cd "$MONOREPO_DIR"
    git init
    
    # 3. Import submodułów z historią
    log "Importuję obsession z historią Git..."
    if [ -d "$ORIGINAL_DIR/obsession/.git" ]; then
        # Jeśli to lokalny submoduł
        git subtree add --prefix=packages/obsession "$ORIGINAL_DIR/obsession" main --squash
    else
        # Jeśli to remote
        git subtree add --prefix=packages/obsession "https://github.com/${GITHUB_USER}/obsession.git" main --squash
    fi
    
    log "Importuję medusa z historią Git..."
    if [ -d "$ORIGINAL_DIR/medusa/.git" ]; then
        git subtree add --prefix=packages/medusa "$ORIGINAL_DIR/medusa" main --squash
    else
        git subtree add --prefix=packages/medusa "https://github.com/${GITHUB_USER}/medusa.git" main --squash
    fi
    
    # 4. Kopiowanie plików z meta-projektu
    log "Kopiuję pliki z meta-projektu..."
    for item in docs README.md .gitignore; do
        if [ -e "$ORIGINAL_DIR/$item" ]; then
            cp -r "$ORIGINAL_DIR/$item" .
        fi
    done
    
    # 5. Tworzenie workspace pyproject.toml
    log "Konfiguruję uv workspace..."
    cat > pyproject.toml << 'EOF'
[tool.uv]
package = false

[tool.uv.workspace]
members = ["packages/*"]

[project]
name = "setka-workspace"
version = "1.0.0"
description = "Setka media processing and automation workspace"
readme = "README.md"
requires-python = ">=3.10"

[tool.uv.sources]
setka-common = { workspace = true }
obsession = { workspace = true }
medusa = { workspace = true }
EOF
    
    # 6. Tworzenie struktury setka-common
    log "Tworzę pakiet setka-common..."
    mkdir -p packages/common/{src/setka_common/{file_structure,utils},tests}
    
    cat > packages/common/pyproject.toml << 'EOF'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "setka-common"
version = "0.1.0"
description = "Common utilities for Setka media processing"
readme = "README.md"
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
    
    # 7. Placeholder dla setka-common
    cat > packages/common/src/setka_common/__init__.py << 'EOF'
"""Setka Common - Shared utilities for Setka media processing."""

__version__ = "0.1.0"
EOF
    
    cat > packages/common/README.md << 'EOF'
# Setka Common

Współdzielone komponenty dla projektów Setka.

## Instalacja

```bash
uv add setka-common
```

## Użycie

```python
from setka_common.file_structure import MediaStructure, StructureManager
from setka_common.utils.files import find_files_by_type
```
EOF
    
    # 8. Update zależności w obsession
    log "Aktualizuję zależności w obsession..."
    if [ -f "packages/obsession/pyproject.toml" ]; then
        # Dodaj setka-common do dependencies (wymaga bardziej złożonej logiki)
        warning "Musisz ręcznie dodać 'setka-common' do dependencies w packages/obsession/pyproject.toml"
    fi
    
    # 9. GitHub Actions
    log "Tworzę konfigurację CI/CD..."
    mkdir -p .github/workflows
    cat > .github/workflows/test.yml << 'EOF'
name: Test All Packages

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install uv
      uses: astral-sh/setup-uv@v5
    
    - name: Install dependencies
      run: uv sync
    
    - name: Run tests
      run: uv run pytest --cov
    
    - name: Type checking
      run: uv run mypy packages/*/src
    
    - name: Linting
      run: uv run ruff check packages/*/src
EOF
    
    # 10. Git commit
    log "Tworzę initial commit..."
    git add .
    git commit -m "feat: initial monorepo structure with obsession and medusa

- Migrated from submodules to monorepo structure
- Added uv workspace configuration  
- Created setka-common package structure
- Set up GitHub Actions for CI/CD"
    
    # 11. Podsumowanie
    echo
    log "=== Migracja zakończona pomyślnie! ==="
    echo
    echo "Następne kroki:"
    echo "1. Przejdź do: cd $MONOREPO_DIR"
    echo "2. Zainstaluj zależności: uv sync"
    echo "3. Przenieś kod z obsession/file_structure.py do packages/common/"
    echo "4. Zaktualizuj importy w obsession"
    echo "5. Uruchom testy: uv run pytest"
    echo
    echo "Backup znajduje się w: $BACKUP_DIR"
    
    # Opcjonalnie: otwórz w VS Code
    if command -v code &> /dev/null; then
        read -p "Czy otworzyć projekt w VS Code? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            code "$MONOREPO_DIR"
        fi
    fi
}

# Uruchom migrację
main "$@"