from __future__ import annotations

import ast
import os
from pathlib import Path

from langchain_core.tools import tool

from ..models import SearchResult


@tool
def read_file(path: str) -> str:
    """Read the full contents of a file inside the workspace."""
    target = Path(path)
    if not target.exists():
        return f"ERROR: {path} does not exist"
    if not target.is_file():
        return f"ERROR: {path} is not a file"
    try:
        return target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"ERROR: {exc}"


@tool
def list_directory(path: str = ".", depth: int = 2) -> list[str]:
    """List files in a directory up to the given depth."""
    root = Path(path)
    if not root.exists():
        return [f"ERROR: {path} does not exist"]
    results: list[str] = []
    _walk(root, root, depth, results)
    return results


def _walk(root: Path, current: Path, remaining: int, out: list[str]) -> None:
    try:
        entries = sorted(current.iterdir())
    except PermissionError:
        return
    for entry in entries:
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue
        rel = str(entry.relative_to(root))
        if entry.is_dir():
            out.append(rel + "/")
            if remaining > 0:
                _walk(root, entry, remaining - 1, out)
        else:
            out.append(rel)


@tool
def search_code(pattern: str, file_glob: str = "**/*.py", root: str = ".") -> list[SearchResult]:
    """Search for a regex pattern across files matching file_glob."""
    import re

    root_path = Path(root)
    results: list[SearchResult] = []
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return [SearchResult(file_path="", line_number=0, line_content=f"Invalid pattern: {exc}")]

    for file_path in root_path.glob(file_glob):
        if not file_path.is_file():
            continue
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            if regex.search(line):
                context_lines = lines[max(0, i - 2) : i + 1]
                results.append(
                    SearchResult(
                        file_path=str(file_path),
                        line_number=i,
                        line_content=line,
                        context="\n".join(context_lines),
                    )
                )
    return results


def extract_python_symbols(path: str) -> list[str]:
    """Extract top-level class and function names from a Python file."""
    try:
        source = Path(path).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return []
    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if isinstance(node, ast.ClassDef) or node.col_offset == 0:
                symbols.append(node.name)
    return symbols
