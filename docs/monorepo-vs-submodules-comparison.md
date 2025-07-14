# Monorepo vs Submoduły - Porównanie dla projektu Setka

## 1. Czym jest Monorepo?

**Monorepo** to jedno repozytorium Git zawierające wiele projektów/pakietów, które są rozwijane, wersjonowane i deployowane razem.

```
setka/                    # Jedno repo Git
├── .git/                 # Jedna historia Git
├── packages/
│   ├── common/          # Pakiet 1
│   ├── obsession/       # Pakiet 2
│   └── medusa/          # Pakiet 3
└── pyproject.toml       # Workspace root
```

### Przykłady monorepo:
- Google (całe źródło w jednym repo)
- Facebook/Meta
- Babel, React, Angular
- Microsoft (Windows, Office)

## 2. Jak działa uv workspace?

UV workspace to funkcja `uv` (od wersji 0.3.0) pozwalająca zarządzać wieloma pakietami Python w jednym repozytorium.

### Konfiguracja workspace

```toml
# /setka/pyproject.toml (root)
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv]
package = false  # Root nie jest pakietem
```

```toml
# /setka/packages/common/pyproject.toml
[project]
name = "setka-common"
version = "0.1.0"
dependencies = []

# /setka/packages/obsession/pyproject.toml
[project]
name = "obsession"
version = "1.0.0"
dependencies = [
    "setka-common",  # uv automatycznie linkuje lokalny pakiet!
]
```

### Komendy uv workspace

```bash
# W root directory
uv sync                    # Instaluje wszystkie pakiety
uv run pytest             # Uruchamia testy we wszystkich pakietach
uv add numpy              # Dodaje do root
uv add --package obsession numpy  # Dodaje do konkretnego pakietu

# Workspace-aware commands
uv workspace list         # Lista pakietów
uv workspace tree         # Drzewo zależności
```

### Jak uv linkuje pakiety lokalnie

UV tworzy symlinki w `.venv`:
```
.venv/lib/python3.11/site-packages/
├── setka_common -> /setka/packages/common/src/setka_common
├── obsession -> /setka/packages/obsession/src/obsession
└── medusa -> /setka/packages/medusa/src/medusa
```

## 3. Porównanie: Monorepo vs Submoduły

### A. Struktura

**Submoduły:**
```bash
setka/                    # Główne repo
├── .git/
├── .gitmodules          # Konfiguracja submodułów
├── setka-common/        # Submoduł (własne repo)
│   └── .git            # Wskaźnik do innego repo
├── obsession/           # Submoduł (własne repo)
│   └── .git
└── medusa/              # Submoduł (własne repo)
    └── .git
```

**Monorepo:**
```bash
setka/                    # Jedno repo
├── .git/                # Jedna historia
├── packages/
│   ├── common/
│   ├── obsession/
│   └── medusa/
└── pyproject.toml       # Workspace config
```

### B. Workflow developerski

**Submoduły:**
```bash
# Klonowanie
git clone --recursive https://github.com/user/setka
# lub
git clone https://github.com/user/setka
git submodule update --init --recursive

# Praca na submodule
cd obsession
git checkout -b feature/new-thing
# ... zmiany ...
git commit && git push

# Update w głównym repo
cd ..
git add obsession
git commit -m "Update obsession submodule"
```

**Monorepo z uv workspace:**
```bash
# Klonowanie
git clone https://github.com/user/setka

# Setup
uv sync  # Instaluje wszystko

# Praca
# Edytujesz dowolny plik w dowolnym pakiecie
git add .
git commit -m "feat: update common and obsession"
git push
```

### C. Zarządzanie zależnościami

**Submoduły:**
```toml
# obsession/pyproject.toml
dependencies = [
    # Opcja 1: GitHub
    "setka-common @ git+https://github.com/user/setka-common.git@v0.1.0",
    # Opcja 2: Lokalna ścieżka (development)
    "setka-common @ file:///../setka-common",
]
```

**Monorepo:**
```toml
# packages/obsession/pyproject.toml
dependencies = [
    "setka-common",  # uv automatycznie wie że to lokalny pakiet!
]
```

### D. Wersjonowanie

**Submoduły:**
- Każdy moduł ma własne tagi/releases
- Główne repo trackuje konkretne commity submodułów
- Możliwa niezależna historia wersji

**Monorepo:**
- Jeden tag/release dla wszystkiego
- Atomic commits (wszystko zmienia się razem)
- Prostsze śledzenie kompatybilności

### E. CI/CD

**Submoduły:**
```yaml
# Osobne workflow dla każdego repo
# setka/.github/workflows/integration.yml
steps:
  - uses: actions/checkout@v4
    with:
      submodules: recursive
  - run: cd setka-common && uv run pytest
  - run: cd obsession && uv run pytest
```

**Monorepo:**
```yaml
# Jeden workflow
# setka/.github/workflows/test.yml
steps:
  - uses: actions/checkout@v4
  - run: uv sync
  - run: uv run pytest  # Testuje wszystko
```

## 4. Zalety i wady

### Monorepo z uv workspace

**Zalety:**
- ✅ Atomic commits (wszystko w jednym commit)
- ✅ Łatwe refaktoryzacje cross-package
- ✅ Jeden PR może dotykać wielu pakietów
- ✅ Automatyczne linkowanie lokalnych pakietów
- ✅ Prostsze CI/CD
- ✅ Łatwiejsze code review
- ✅ Brak problemów z synchronizacją wersji

**Wady:**
- ❌ Większe repo (clone pobiera wszystko)
- ❌ Brak granularnych uprawnień
- ❌ Trudniej wydzielić pakiet później
- ❌ Wszystkie zmiany widoczne dla wszystkich

### Submoduły

**Zalety:**
- ✅ Separacja concerns (różne repo = różne uprawnienia)
- ✅ Możliwość niezależnego rozwoju
- ✅ Mniejsze, focused repos
- ✅ Łatwe udostępnianie pojedynczego modułu
- ✅ Niezależna historia Git

**Wady:**
- ❌ Skomplikowany workflow (`git submodule update`)
- ❌ Łatwo o desynchronizację
- ❌ Trudniejsze cross-module refactoring
- ❌ Więcej konfiguracji CI/CD
- ❌ "Detached HEAD" i inne pułapki Git

## 5. Rekomendacja dla Setka

Dla projektu jednoosobowego **zdecydowanie polecam monorepo z uv workspace**:

1. **Prostota**: Jeden `git push`, wszystko zsynchronizowane
2. **Szybkość**: Refaktoryzacje cross-module w jednym PR
3. **DX**: Edytujesz `common` i od razu widzisz efekt w `obsession`
4. **Mniej ceremonii**: Brak `git submodule update`, tracking commitów

### Przykład struktury dla Setka jako monorepo:

```
setka/
├── .github/workflows/
│   └── test.yml
├── packages/
│   ├── common/
│   │   ├── pyproject.toml
│   │   ├── src/setka_common/
│   │   └── tests/
│   ├── obsession/
│   │   ├── pyproject.toml
│   │   ├── src/obsession/
│   │   └── tests/
│   └── medusa/
│       ├── pyproject.toml
│       ├── src/medusa/
│       └── tests/
├── docs/
├── scripts/              # Wspólne skrypty
├── .gitignore
├── pyproject.toml       # Workspace root
└── README.md
```

### Migracja do monorepo:

```bash
# 1. Stwórz nową strukturę
mkdir -p setka-monorepo/packages
cd setka-monorepo

# 2. Skopiuj projekty (zachowując historię)
git subtree add --prefix=packages/obsession https://github.com/user/obsession main
git subtree add --prefix=packages/medusa https://github.com/user/medusa main

# 3. Setup workspace
uv init
# Edytuj pyproject.toml, dodaj [tool.uv.workspace]

# 4. Test
uv sync
uv run pytest
```

## Podsumowanie

**Użyj monorepo jeśli:**
- Projekty są ściśle powiązane
- Chcesz prostoty w development
- Jesteś jedynym/głównym developerem
- Chcesz atomic changes

**Użyj submodułów jeśli:**
- Potrzebujesz niezależnych releases
- Różne zespoły/uprawnienia
- Projekty mogą żyć osobno
- Chcesz granularnej kontroli