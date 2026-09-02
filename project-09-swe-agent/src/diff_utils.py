from __future__ import annotations

import difflib
from pathlib import Path


def generate_unified_diff(original: str, modified: str, filename: str = "file") -> str:
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff)


def diff_from_file(original_path: str, modified_path: str) -> str:
    orig = Path(original_path).read_text(encoding="utf-8", errors="replace")
    mod = Path(modified_path).read_text(encoding="utf-8", errors="replace")
    filename = Path(original_path).name
    return generate_unified_diff(orig, mod, filename)


def count_changed_lines(diff: str) -> tuple[int, int]:
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    return added, removed


def extract_affected_files(diff: str) -> list[str]:
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ ") and line[4:] != "/dev/null":
            path = line[4:].lstrip("b/")
            if path not in files:
                files.append(path)
    return files


def patches_to_full_diff(patches: list[dict]) -> str:
    sections: list[str] = []
    for patch in patches:
        header = f"# {patch.get('file_path', 'unknown')} (iteration {patch.get('iteration', 0)})"
        sections.append(f"{header}\n{patch.get('unified_diff', '')}")
    return "\n\n".join(sections)


def diff_summary(diff: str) -> str:
    added, removed = count_changed_lines(diff)
    files = extract_affected_files(diff)
    return f"+{added}/-{removed} across {len(files)} file(s)"
