from __future__ import annotations

from pathlib import Path

from .config import settings
from .models import FileInfo
from .tools.filesystem import extract_python_symbols

_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".rb": "ruby",
    ".sh": "shell",
    ".bash": "shell",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".css": "css",
    ".html": "html",
    ".sql": "sql",
}

_SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".mypy_cache", ".pytest_cache", "dist", "build",
}


def build_repo_map(repo_path: str, summarizer=None) -> dict[str, FileInfo]:
    root = Path(repo_path)
    file_infos: dict[str, FileInfo] = {}
    _collect(root, root, settings.repo_map_depth, file_infos, summarizer)
    return file_infos


def _collect(
    root: Path,
    current: Path,
    remaining: int,
    out: dict[str, FileInfo],
    summarizer,
) -> None:
    try:
        entries = sorted(current.iterdir())
    except PermissionError:
        return

    for entry in entries:
        if entry.name in _SKIP_DIRS or entry.name.startswith("."):
            continue
        if entry.is_dir():
            if remaining > 0:
                _collect(root, entry, remaining - 1, out, summarizer)
        elif entry.is_file():
            rel = str(entry.relative_to(root))
            lang = _LANGUAGE_MAP.get(entry.suffix.lower(), "text")
            size = entry.stat().st_size
            symbols: list[str] = []
            summary = ""

            if lang == "python":
                symbols = extract_python_symbols(str(entry))

            if summarizer and size > settings.large_file_threshold_bytes:
                try:
                    content = entry.read_text(encoding="utf-8", errors="replace")[:3000]
                    summary = summarizer(content)
                except Exception:
                    summary = ""

            out[rel] = FileInfo(
                path=rel,
                size_bytes=size,
                language=lang,
                symbols=symbols,
                summary=summary,
            )


def repo_map_to_context(repo_map: dict[str, FileInfo], focus_paths: list[str] | None = None) -> str:
    lines: list[str] = []
    for rel, info in sorted(repo_map.items()):
        is_focus = focus_paths is None or any(rel.startswith(fp) for fp in focus_paths)
        if not is_focus:
            continue
        symbol_str = ", ".join(info.symbols[:10]) if info.symbols else ""
        summary_str = f" -- {info.summary}" if info.summary else ""
        lines.append(f"{rel} ({info.language}, {info.size_bytes}B){': ' + symbol_str if symbol_str else ''}{summary_str}")
    return "\n".join(lines)
