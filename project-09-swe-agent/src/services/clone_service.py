from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def clone_repo(clone_url: str, target_dir: str, depth: int = 1) -> str:
    """Shallow-clone a repo into target_dir. Returns the path to the clone."""
    result = subprocess.run(
        ["git", "clone", "--depth", str(depth), clone_url, target_dir],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr}")
    return target_dir


def get_head_sha(repo_dir: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=repo_dir,
    )
    return result.stdout.strip()


def create_branch(repo_dir: str, branch_name: str) -> None:
    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        capture_output=True,
        cwd=repo_dir,
        check=True,
    )


def stage_all(repo_dir: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)


def commit_changes(repo_dir: str, message: str) -> None:
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )


def push_branch(repo_dir: str, remote: str = "origin") -> None:
    subprocess.run(
        ["git", "push", remote, "HEAD"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )


def list_changed_files(repo_dir: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_current_branch(repo_dir: str) -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
