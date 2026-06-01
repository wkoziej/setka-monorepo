# ABOUTME: Shared dependencies for Paternologia FastAPI application.
# ABOUTME: Provides storage and templates instances for dependency injection.

import os
from pathlib import Path

from fastapi.templating import Jinja2Templates

from paternologia.storage import Storage

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"

_DATA_DIR_ENV = "PATERNOLOGIA_DATA_DIR"

_storage: Storage | None = None
_templates: Jinja2Templates | None = None


def _resolve_data_dir() -> Path:
    """Resolve the data directory, honoring the PATERNOLOGIA_DATA_DIR override."""
    override = os.environ.get(_DATA_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return DATA_DIR


def get_storage() -> Storage:
    """Get or create storage instance."""
    global _storage
    if _storage is None:
        data_dir = _resolve_data_dir()
        storage = Storage(data_dir=data_dir)
        try:
            storage._ensure_dirs()
        except OSError as exc:
            raise RuntimeError(
                f"Nie można utworzyć katalogu danych paternologii: {data_dir}. "
                f"Ustaw {_DATA_DIR_ENV} na zapisywalną ścieżkę. Przyczyna: {exc}"
            ) from exc
        _storage = storage
    return _storage


def get_templates() -> Jinja2Templates:
    """Get or create templates instance."""
    global _templates
    if _templates is None:
        _templates = Jinja2Templates(directory=TEMPLATES_DIR)
    return _templates
