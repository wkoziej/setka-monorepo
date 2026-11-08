# ABOUTME: Tests for the remote-host deploy scripts (sync-data.sh, autoupdate.sh) using real git/rsync.
# ABOUTME: autoupdate.sh runs against a local origin repo whose install.sh is a fixture marker script.

import os
import subprocess
from pathlib import Path

import pytest

REMOTE_DIR = Path(__file__).resolve().parent.parent / "deploy" / "remote"
SYNC_DATA = REMOTE_DIR / "sync-data.sh"
AUTOUPDATE = REMOTE_DIR / "autoupdate.sh"

# Fixture install.sh per package: logs its package name; fails when FAIL_INSTALL exists in $APP.
FIXTURE_INSTALL = """#!/usr/bin/env bash
set -euo pipefail
APP=$HOME/paternologia
if [ -e "$APP/FAIL_INSTALL" ]; then exit 1; fi
echo {pkg} >> "$APP/install-runs"
"""
DEPLOYED_PACKAGES = ("paternologia", "launchpad-rc600")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def clean_env() -> dict[str, str]:
    """os.environ without GIT_* — under a git hook, GIT_INDEX_FILE & co. would
    redirect the fixture repos' git commands to the real repository's index."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def run(
    cmd: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, env=clean_env() if env is None else env
    )


# --- sync-data.sh ---------------------------------------------------------


@pytest.fixture
def data_dirs(tmp_path):
    src = tmp_path / "repo-data"
    dst = tmp_path / "host-data"
    write(src / "songs" / "a.yaml", "repo a\n")
    write(src / "songs_order.yaml", "- a\n")
    write(src / "obs.yaml", "enabled: true\n")
    write(src / "pacer.yaml", "device_name: PACER\n")
    return src, dst


def sync(src: Path, dst: Path) -> None:
    result = run(["bash", str(SYNC_DATA), str(src), str(dst)])
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""


def test_sync_data_seeds_empty_host(data_dirs):
    src, dst = data_dirs
    sync(src, dst)
    assert (dst / "songs" / "a.yaml").read_text() == "repo a\n"
    assert (dst / "obs.yaml").read_text() == "enabled: true\n"
    assert (dst / "pacer.yaml").read_text() == "device_name: PACER\n"


def test_sync_data_repo_overwrites_songs_and_removes_deleted(data_dirs):
    src, dst = data_dirs
    write(dst / "songs" / "a.yaml", "edited on host\n")
    write(dst / "songs" / "gone.yaml", "removed from repo\n")
    sync(src, dst)
    assert (dst / "songs" / "a.yaml").read_text() == "repo a\n"
    assert not (dst / "songs" / "gone.yaml").exists()


def test_sync_data_keeps_host_specific_config(data_dirs):
    src, dst = data_dirs
    write(dst / "obs.yaml", "enabled: false\n")
    write(dst / "pacer.yaml", "device_name: HOST\n")
    sync(src, dst)
    assert (dst / "obs.yaml").read_text() == "enabled: false\n"
    assert (dst / "pacer.yaml").read_text() == "device_name: HOST\n"


# --- autoupdate.sh --------------------------------------------------------


class Origin:
    """Local git repo standing in for GitHub; commits files on master."""

    def __init__(self, path: Path):
        self.path = path
        path.mkdir()
        self.git("init", "-q", "-b", "master")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("config", "uploadpack.allowFilter", "true")
        write(path / "pyproject.toml", "[project]\nname = 'x'\n")
        write(path / "packages" / "common" / "common.txt", "common\n")
        write(path / "packages" / "other" / "other.txt", "not needed on host\n")
        for pkg in DEPLOYED_PACKAGES:
            install = path / "packages" / pkg / "deploy" / "remote" / "install.sh"
            write(install, FIXTURE_INSTALL.format(pkg=pkg))
        self.commit("packages/paternologia/data/songs/a.yaml", "v1\n")

    def git(self, *args: str) -> str:
        result = run(["git", "-C", str(self.path), *args])
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    def commit(self, rel: str, text: str) -> str:
        write(self.path / rel, text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"update {rel}")
        return self.git("rev-parse", "HEAD")


@pytest.fixture
def host(tmp_path):
    home = tmp_path / "home"
    (home / "paternologia").mkdir(parents=True)
    origin = Origin(tmp_path / "origin")
    env = {
        "HOME": str(home),
        "PATH": os.environ["PATH"],
        "PATERNOLOGIA_REPO_URL": f"file://{origin.path}",
    }
    return home / "paternologia", origin, env


def autoupdate(env: dict) -> subprocess.CompletedProcess:
    return run(["bash", str(AUTOUPDATE)], env=env)


def install_runs(app: Path) -> list[str]:
    runs = app / "install-runs"
    return runs.read_text().splitlines() if runs.exists() else []


def test_autoupdate_first_run_clones_sparse_and_installs(host):
    app, origin, env = host
    result = autoupdate(env)
    assert result.returncode == 0, result.stderr
    src = app / "src"
    assert (
        src / "packages" / "paternologia" / "data" / "songs" / "a.yaml"
    ).read_text() == "v1\n"
    assert (src / "packages" / "common" / "common.txt").exists()
    assert (src / "packages" / "launchpad-rc600").is_dir()
    assert not (src / "packages" / "other").exists()
    assert install_runs(app) == list(DEPLOYED_PACKAGES)
    assert (app / "deployed-commit").read_text().strip() == origin.git(
        "rev-parse", "HEAD"
    )


def test_autoupdate_without_changes_does_not_reinstall(host):
    app, _, env = host
    autoupdate(env)
    result = autoupdate(env)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert install_runs(app) == list(DEPLOYED_PACKAGES)


def test_autoupdate_deploys_new_master_commit(host):
    app, origin, env = host
    autoupdate(env)
    head = origin.commit("packages/paternologia/data/songs/a.yaml", "v2\n")
    result = autoupdate(env)
    assert result.returncode == 0, result.stderr
    assert (
        app / "src" / "packages" / "paternologia" / "data" / "songs" / "a.yaml"
    ).read_text() == "v2\n"
    assert install_runs(app) == [*DEPLOYED_PACKAGES, "paternologia"]
    assert (app / "deployed-commit").read_text().strip() == head


def test_autoupdate_retries_after_failed_install(host):
    app, origin, env = host
    autoupdate(env)
    deployed = (app / "deployed-commit").read_text()
    origin.commit("packages/paternologia/data/songs/a.yaml", "v2\n")
    (app / "FAIL_INSTALL").touch()
    failed = autoupdate(env)
    assert failed.returncode != 0
    assert (app / "deployed-commit").read_text() == deployed

    (app / "FAIL_INSTALL").unlink()
    result = autoupdate(env)
    assert result.returncode == 0, result.stderr
    assert install_runs(app) == [*DEPLOYED_PACKAGES, "paternologia"]
    assert (app / "deployed-commit").read_text().strip() == origin.git(
        "rev-parse", "HEAD"
    )


def test_autoupdate_replaces_existing_non_git_src(host):
    app, _, env = host
    write(app / "src" / "packages" / "stale.txt", "rsynced by deploy.sh\n")
    result = autoupdate(env)
    assert result.returncode == 0, result.stderr
    assert (app / "src" / ".git").is_dir()
    assert not (app / "src" / "packages" / "stale.txt").exists()


def test_autoupdate_installs_only_changed_packages(host):
    app, origin, env = host
    autoupdate(env)
    origin.commit("packages/launchpad-rc600/assign.toml", "x = 1\n")
    assert autoupdate(env).returncode == 0
    origin.commit("packages/common/common.txt", "common v2\n")
    assert autoupdate(env).returncode == 0
    origin.commit("packages/other/other.txt", "v2\n")
    result = autoupdate(env)
    assert result.returncode == 0, result.stderr
    assert install_runs(app) == [
        *DEPLOYED_PACKAGES,
        "launchpad-rc600",
        "paternologia",
    ]
    assert (app / "deployed-commit").read_text().strip() == origin.git(
        "rev-parse", "HEAD"
    )


def test_autoupdate_extends_sparse_checkout_of_existing_clone(host):
    app, _, env = host
    autoupdate(env)
    src = app / "src"
    run(["git", "-C", str(src), "sparse-checkout", "set", "packages/paternologia"])
    assert not (src / "packages" / "launchpad-rc600").exists()
    (app / "deployed-commit").unlink()
    result = autoupdate(env)
    assert result.returncode == 0, result.stderr
    assert (src / "packages" / "launchpad-rc600" / "deploy").is_dir()
    assert (src / "packages" / "common" / "common.txt").exists()
