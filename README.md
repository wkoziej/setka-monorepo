# Setka - Media Processing and Automation

Monorepo zawierający narzędzia do przetwarzania mediów i automatyzacji publikacji.

## Struktura

- **packages/common/** - Wspólna biblioteka dla zarządzania plikami
- **packages/obsession/** - OBS Canvas Recorder z integracją Blender VSE
- **packages/medusa/** - Media Upload & Social Automation

## Szybki start

```bash
# Instalacja wszystkich zależności
uv sync

# Uruchomienie testów
uv run pytest

# Praca z konkretnym pakietem
uv run --package obsession python -m cli.extract --help
uv run --package medusa python -m medusa.cli --help
```

## Development

Ten projekt używa uv workspace dla zarządzania wieloma pakietami w jednym repozytorium.

### Dodawanie zależności

```bash
# Do konkretnego pakietu
uv add --package obsession numpy

# Do workspace (dev dependencies)
uv add --dev pytest-xdist
```

### Testowanie

```bash
# Wszystkie testy
uv run pytest

# Konkretny pakiet
uv run --package obsession pytest
uv run --package medusa pytest

# Z pokryciem kodu
uv run pytest --cov
```
