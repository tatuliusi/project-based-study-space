from __future__ import annotations

from pathlib import Path

import pytest

from src.tools.filesystem import (
    extract_python_symbols,
    list_directory,
    read_file,
    search_code,
)


def test_read_file_existing(sample_python_file):
    result = read_file.invoke({"path": str(sample_python_file)})
    assert "def add" in result
    assert "def divide" in result


def test_read_file_missing(tmp_path):
    result = read_file.invoke({"path": str(tmp_path / "nonexistent.py")})
    assert "ERROR" in result


def test_read_file_directory(tmp_workspace):
    result = read_file.invoke({"path": str(tmp_workspace / "src")})
    assert "ERROR" in result


def test_list_directory(tmp_workspace, sample_python_file):
    entries = list_directory.invoke({"path": str(tmp_workspace), "depth": 2})
    assert any("calculator.py" in e for e in entries)
    assert any(e.endswith("/") for e in entries)


def test_list_directory_skips_hidden(tmp_workspace):
    (tmp_workspace / ".hidden_dir").mkdir()
    (tmp_workspace / ".env").write_text("SECRET=x")
    entries = list_directory.invoke({"path": str(tmp_workspace), "depth": 1})
    assert not any(".hidden" in e for e in entries)
    assert not any(".env" in e for e in entries)


def test_list_directory_skips_pycache(tmp_workspace):
    pycache = tmp_workspace / "__pycache__"
    pycache.mkdir()
    (pycache / "foo.pyc").write_bytes(b"")
    entries = list_directory.invoke({"path": str(tmp_workspace), "depth": 2})
    assert not any("__pycache__" in e for e in entries)


def test_search_code_finds_match(tmp_workspace, sample_python_file):
    results = search_code.invoke({
        "pattern": r"def \w+",
        "file_glob": "**/*.py",
        "root": str(tmp_workspace),
    })
    assert len(results) >= 2
    paths = {r.file_path for r in results}
    assert str(sample_python_file) in paths


def test_search_code_no_match(tmp_workspace, sample_python_file):
    results = search_code.invoke({
        "pattern": "XYZNOTFOUND",
        "file_glob": "**/*.py",
        "root": str(tmp_workspace),
    })
    assert results == []


def test_search_code_invalid_pattern(tmp_workspace):
    results = search_code.invoke({
        "pattern": "[invalid(",
        "file_glob": "**/*.py",
        "root": str(tmp_workspace),
    })
    assert len(results) == 1
    assert "Invalid pattern" in results[0].line_content


def test_extract_python_symbols(sample_python_file):
    symbols = extract_python_symbols(str(sample_python_file))
    assert "add" in symbols
    assert "divide" in symbols


def test_extract_python_symbols_missing_file(tmp_path):
    symbols = extract_python_symbols(str(tmp_path / "nope.py"))
    assert symbols == []


def test_extract_python_symbols_syntax_error(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("def (:(")
    symbols = extract_python_symbols(str(bad))
    assert symbols == []
