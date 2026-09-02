from __future__ import annotations

from src.diff_utils import (
    count_changed_lines,
    extract_affected_files,
    generate_unified_diff,
    patches_to_full_diff,
)


ORIGINAL = "def add(a, b):\n    return a + b\n"
MODIFIED = "def add(a, b):\n    result = a + b\n    return result\n"


def test_generate_unified_diff_produces_output():
    diff = generate_unified_diff(ORIGINAL, MODIFIED, "calc.py")
    assert "--- a/calc.py" in diff
    assert "+++ b/calc.py" in diff


def test_generate_unified_diff_shows_added_lines():
    diff = generate_unified_diff(ORIGINAL, MODIFIED, "calc.py")
    assert "+    result = a + b" in diff
    assert "+    return result" in diff


def test_generate_unified_diff_shows_removed_lines():
    diff = generate_unified_diff(ORIGINAL, MODIFIED, "calc.py")
    assert "-    return a + b" in diff


def test_generate_unified_diff_identical_files():
    diff = generate_unified_diff(ORIGINAL, ORIGINAL, "calc.py")
    assert diff == ""


def test_count_changed_lines_additions():
    diff = generate_unified_diff(ORIGINAL, MODIFIED, "calc.py")
    added, removed = count_changed_lines(diff)
    assert added >= 1
    assert removed >= 1


def test_count_changed_lines_no_change():
    added, removed = count_changed_lines("")
    assert added == 0
    assert removed == 0


def test_extract_affected_files():
    diff = (
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1 +1 @@\n"
        "+x = 1\n"
    )
    files = extract_affected_files(diff)
    assert "src/foo.py" in files


def test_extract_affected_files_dev_null_excluded():
    diff = (
        "--- /dev/null\n"
        "+++ b/new_file.py\n"
        "@@ -0,0 +1 @@\n"
        "+x = 1\n"
    )
    files = extract_affected_files(diff)
    assert "new_file.py" in files


def test_extract_affected_files_multiple():
    diff = (
        "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n+x=1\n"
        "--- a/bar.py\n+++ b/bar.py\n@@ -1 +1 @@\n+y=2\n"
    )
    files = extract_affected_files(diff)
    assert len(files) == 2


def test_patches_to_full_diff():
    patches = [
        {"file_path": "src/a.py", "iteration": 0, "unified_diff": "--- a\n+++ b\n"},
        {"file_path": "src/b.py", "iteration": 1, "unified_diff": "--- c\n+++ d\n"},
    ]
    result = patches_to_full_diff(patches)
    assert "src/a.py" in result
    assert "src/b.py" in result
    assert "iteration 0" in result
    assert "iteration 1" in result


def test_patches_to_full_diff_empty():
    result = patches_to_full_diff([])
    assert result == ""
