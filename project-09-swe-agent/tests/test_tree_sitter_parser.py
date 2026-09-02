from __future__ import annotations

from pathlib import Path

import pytest

from src.tools.tree_sitter_parser import _ast_fallback, parse_file, safe_parse_python


SIMPLE_SOURCE = "def hello():\n    pass\n\nclass Greeter:\n    pass\n"
SYNTAX_ERROR_SOURCE = "def (broken:"


def test_safe_parse_python_functions():
    names = safe_parse_python(SIMPLE_SOURCE)
    assert "hello" in names


def test_safe_parse_python_classes():
    names = safe_parse_python(SIMPLE_SOURCE)
    assert "Greeter" in names


def test_safe_parse_python_syntax_error():
    names = safe_parse_python(SYNTAX_ERROR_SOURCE)
    assert isinstance(names, list)


def test_ast_fallback_extracts_functions():
    names = _ast_fallback(SIMPLE_SOURCE)
    assert "hello" in names
    assert "Greeter" in names


def test_ast_fallback_empty_source():
    names = _ast_fallback("")
    assert names == []


def test_ast_fallback_syntax_error():
    names = _ast_fallback("def (broken:")
    assert names == []


def test_parse_file_existing(tmp_path):
    src = tmp_path / "module.py"
    src.write_text("def compute(x):\n    return x * 2\n\nclass Engine:\n    pass\n")
    names = parse_file(str(src))
    assert "compute" in names
    assert "Engine" in names


def test_parse_file_missing(tmp_path):
    names = parse_file(str(tmp_path / "does_not_exist.py"))
    assert names == []


def test_parse_file_empty(tmp_path):
    empty = tmp_path / "empty.py"
    empty.write_text("")
    names = parse_file(str(empty))
    assert names == []
