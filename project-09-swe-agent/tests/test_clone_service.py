from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.services.clone_service import (
    commit_changes,
    create_branch,
    get_head_sha,
    stage_all,
)


def _init_bare_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
    (path / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)


def test_get_head_sha(tmp_path):
    _init_bare_repo(tmp_path)
    sha = get_head_sha(str(tmp_path))
    assert len(sha) == 40
    assert sha.isalnum()


def test_create_branch(tmp_path):
    _init_bare_repo(tmp_path)
    create_branch(str(tmp_path), "feature/test")
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "feature/test"


def test_stage_and_commit(tmp_path):
    _init_bare_repo(tmp_path)
    (tmp_path / "new_file.py").write_text("x = 1\n")
    stage_all(str(tmp_path))
    commit_changes(str(tmp_path), "add new_file")
    log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert "add new_file" in log.stdout


def test_get_head_sha_changes_after_commit(tmp_path):
    _init_bare_repo(tmp_path)
    sha_before = get_head_sha(str(tmp_path))
    (tmp_path / "extra.py").write_text("pass\n")
    stage_all(str(tmp_path))
    commit_changes(str(tmp_path), "extra commit")
    sha_after = get_head_sha(str(tmp_path))
    assert sha_before != sha_after
