# ABOUTME: Tests for cwd-independent resource resolution and data-dir overrides.
# ABOUTME: Covers DATA_DIR/TEMPLATES_DIR anchoring, PATERNOLOGIA_DATA_DIR, and error paths.

import pytest

from paternologia import dependencies


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset cached storage/templates so each test resolves paths freshly."""
    dependencies._storage = None
    dependencies._templates = None
    yield
    dependencies._storage = None
    dependencies._templates = None


def test_data_dir_anchored_to_package():
    """DATA_DIR is an absolute path under the package, independent of cwd."""
    assert dependencies.DATA_DIR.is_absolute()
    assert dependencies.DATA_DIR.name == "data"
    assert dependencies.DATA_DIR.parent.name == "paternologia"


def test_templates_dir_resolves_to_package():
    """TEMPLATES_DIR points at the vendored templates regardless of cwd."""
    assert dependencies.TEMPLATES_DIR.is_absolute()
    assert dependencies.TEMPLATES_DIR.exists()
    assert (dependencies.TEMPLATES_DIR / "live.html").exists()


def test_get_storage_default_uses_package_data(monkeypatch):
    """Without the env override, storage reads from the package data dir."""
    monkeypatch.delenv("PATERNOLOGIA_DATA_DIR", raising=False)
    storage = dependencies.get_storage()
    assert storage.data_dir == dependencies.DATA_DIR


def test_get_storage_reads_config_from_any_cwd(monkeypatch, tmp_path):
    """get_storage() works from an arbitrary working directory."""
    monkeypatch.delenv("PATERNOLOGIA_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    storage = dependencies.get_storage()
    # Package data ships a devices.yaml; reading must not raise.
    assert isinstance(storage.get_devices(), list)


def test_env_overrides_data_dir(monkeypatch, tmp_path):
    """PATERNOLOGIA_DATA_DIR redirects storage to the given location."""
    target = tmp_path / "custom-data"
    monkeypatch.setenv("PATERNOLOGIA_DATA_DIR", str(target))
    storage = dependencies.get_storage()
    assert storage.data_dir == target
    assert target.exists()


def test_unresolvable_data_dir_raises_clear_error(monkeypatch):
    """A non-creatable data dir surfaces a clear error, not a bare OSError."""
    monkeypatch.setenv("PATERNOLOGIA_DATA_DIR", "/proc/nonexistent/cannot/create")
    with pytest.raises(RuntimeError) as exc:
        dependencies.get_storage()
    message = str(exc.value)
    assert "PATERNOLOGIA_DATA_DIR" in message
    assert "/proc/nonexistent/cannot/create" in message
