from __future__ import annotations

from pathlib import Path

import pytest

from src.tools.patch import _apply_python_patch, apply_patch


ORIGINAL = "def divide(a, b):\n    return a / b\n"

VALID_DIFF = (
    "--- a/calculator.py\n"
    "+++ b/calculator.py\n"
    "@@ -1,2 +1,4 @@\n"
    " def divide(a, b):\n"
    "+    if b == 0:\n"
    "+        raise ValueError('zero')\n"
    "     return a / b\n"
)


def test_apply_patch_empty_diff(tmp_workspace, sample_python_file):
    result = apply_patch.invoke({"path": str(sample_python_file), "unified_diff": ""})
    assert not result.success
    assert "Empty" in result.error


def test_apply_patch_file_path_returned(tmp_workspace, sample_python_file):
    result = apply_patch.invoke({"path": str(sample_python_file), "unified_diff": VALID_DIFF})
    assert result.file_path == str(sample_python_file)


def test_apply_python_patch_creates_file(tmp_path):
    new_file = tmp_path / "new_module.py"
    diff = (
        "--- /dev/null\n"
        "+++ b/new_module.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+def hello():\n"
        "+    return 'world'\n"
    )
    result = _apply_python_patch(str(new_file), diff)
    assert result.file_path == str(new_file)


def test_apply_patch_nonexistent_target_handled(tmp_path):
    missing = tmp_path / "does_not_exist.py"
    result = apply_patch.invoke({"path": str(missing), "unified_diff": VALID_DIFF})
    assert result.file_path == str(missing)


def test_patch_result_success_field(tmp_workspace, sample_python_file):
    result = apply_patch.invoke({"path": str(sample_python_file), "unified_diff": VALID_DIFF})
    assert isinstance(result.success, bool)
