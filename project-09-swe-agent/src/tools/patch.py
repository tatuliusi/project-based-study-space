from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool

from ..models import PatchResult


@tool
def apply_patch(path: str, unified_diff: str) -> PatchResult:
    """Apply a unified diff to a file in the workspace."""
    target = Path(path)

    if not unified_diff.strip():
        return PatchResult(success=False, file_path=path, error="Empty diff provided")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as tmp:
        tmp.write(unified_diff)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["patch", "--forward", "--reject-file=-", str(target), tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return PatchResult(success=True, file_path=path)
        return PatchResult(
            success=False,
            file_path=path,
            error=result.stderr or result.stdout,
        )
    except subprocess.TimeoutExpired:
        return PatchResult(success=False, file_path=path, error="patch timed out")
    except FileNotFoundError:
        return _apply_python_patch(path, unified_diff)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _apply_python_patch(path: str, unified_diff: str) -> PatchResult:
    """Fallback: apply unified diff in pure Python when patch binary is unavailable."""
    import difflib

    target = Path(path)
    original_lines = target.read_text(encoding="utf-8").splitlines(keepends=True) if target.exists() else []

    try:
        diff_lines = unified_diff.splitlines(keepends=True)
        patched = list(difflib.restore(diff_lines, 2))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("".join(patched), encoding="utf-8")
        return PatchResult(success=True, file_path=path)
    except Exception as exc:
        return PatchResult(success=False, file_path=path, error=str(exc))
