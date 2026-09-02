from __future__ import annotations

from pathlib import Path

import pytest

from src.repo_map import build_repo_map, repo_map_to_context


def _make_workspace(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "src" / "utils.py").write_text("import os\n\ndef env(key):\n    return os.environ.get(key)\n")
    (tmp_path / "tests" / "test_calc.py").write_text("def test_add():\n    assert True\n")
    (tmp_path / "README.md").write_text("# Project\n")
    return tmp_path


def test_build_repo_map_collects_files(tmp_path):
    ws = _make_workspace(tmp_path)
    repo_map = build_repo_map(str(ws))
    assert "src/calc.py" in repo_map
    assert "src/utils.py" in repo_map
    assert "tests/test_calc.py" in repo_map


def test_build_repo_map_extracts_symbols(tmp_path):
    ws = _make_workspace(tmp_path)
    repo_map = build_repo_map(str(ws))
    assert "add" in repo_map["src/calc.py"].symbols


def test_build_repo_map_language_detection(tmp_path):
    ws = _make_workspace(tmp_path)
    repo_map = build_repo_map(str(ws))
    assert repo_map["src/calc.py"].language == "python"
    assert repo_map["README.md"].language == "markdown"


def test_build_repo_map_skips_hidden(tmp_path):
    ws = _make_workspace(tmp_path)
    (ws / ".env").write_text("SECRET=x")
    (ws / ".venv").mkdir()
    (ws / ".venv" / "lib.py").write_text("pass")
    repo_map = build_repo_map(str(ws))
    assert ".env" not in repo_map
    assert not any(".venv" in k for k in repo_map)


def test_build_repo_map_skips_pycache(tmp_path):
    ws = _make_workspace(tmp_path)
    pycache = ws / "__pycache__"
    pycache.mkdir()
    (pycache / "calc.cpython-311.pyc").write_bytes(b"")
    repo_map = build_repo_map(str(ws))
    assert not any("__pycache__" in k for k in repo_map)


def test_build_repo_map_records_size(tmp_path):
    ws = _make_workspace(tmp_path)
    repo_map = build_repo_map(str(ws))
    assert repo_map["src/calc.py"].size_bytes > 0


def test_repo_map_to_context_all_files(tmp_path):
    ws = _make_workspace(tmp_path)
    repo_map = build_repo_map(str(ws))
    context = repo_map_to_context(repo_map)
    assert "src/calc.py" in context
    assert "python" in context


def test_repo_map_to_context_focus(tmp_path):
    ws = _make_workspace(tmp_path)
    repo_map = build_repo_map(str(ws))
    context = repo_map_to_context(repo_map, focus_paths=["src/"])
    assert "src/calc.py" in context
    assert "tests/" not in context


def test_repo_map_with_summarizer(tmp_path):
    ws = _make_workspace(tmp_path)
    big_file = ws / "src" / "big.py"
    big_file.write_text("x = 1\n" * 3000)

    call_count = [0]

    def fake_summarizer(content: str) -> str:
        call_count[0] += 1
        return "A large module."

    repo_map = build_repo_map(str(ws), summarizer=fake_summarizer)
    assert call_count[0] >= 1
    assert repo_map["src/big.py"].summary == "A large module."
