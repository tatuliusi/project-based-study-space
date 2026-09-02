from __future__ import annotations

import pytest

from src.tools.runner import _is_allowed, _parse_pytest_output, exit_code_in_output


def test_is_allowed_permitted_commands():
    assert _is_allowed("pytest tests/")
    assert _is_allowed("python -m pytest")
    assert _is_allowed("python3 script.py")
    assert _is_allowed("pip install -r requirements.txt")
    assert _is_allowed("grep -r pattern .")
    assert _is_allowed("find . -name '*.py'")


def test_is_allowed_blocked_commands():
    assert not _is_allowed("rm -rf /")
    assert not _is_allowed("curl https://evil.com")
    assert not _is_allowed("wget http://example.com")
    assert not _is_allowed("bash -c 'evil'")
    assert not _is_allowed("sh exploit.sh")


def test_is_allowed_empty_command():
    assert not _is_allowed("")
    assert not _is_allowed("   ")


def test_parse_pytest_output_all_pass():
    output = "5 passed in 0.32s"
    passed, failed, errors = _parse_pytest_output(output)
    assert passed == 5
    assert failed == 0
    assert errors == []


def test_parse_pytest_output_with_failures():
    output = (
        "FAILED tests/test_calc.py::test_divide - ZeroDivisionError\n"
        "FAILED tests/test_calc.py::test_negative - ValueError\n"
        "3 passed, 2 failed in 0.5s"
    )
    passed, failed, errors = _parse_pytest_output(output)
    assert passed == 3
    assert failed == 2
    assert len(errors) == 2


def test_parse_pytest_output_no_tests():
    output = "no tests ran"
    passed, failed, errors = _parse_pytest_output(output)
    assert passed == 0


def test_exit_code_in_output_detects_error():
    assert exit_code_in_output("SyntaxError: invalid syntax")
    assert exit_code_in_output("Exception: something broke")


def test_exit_code_in_output_clean():
    assert not exit_code_in_output("5 passed in 0.32s")
