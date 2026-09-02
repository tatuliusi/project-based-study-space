from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

from langchain_core.tools import tool

from ..config import settings
from ..models import CommandResult, SWETestRun

if TYPE_CHECKING:
    from ..sandbox import Sandbox

_sandbox: Sandbox | None = None


def set_sandbox(sandbox: "Sandbox") -> None:
    global _sandbox
    _sandbox = sandbox


def clear_sandbox() -> None:
    global _sandbox
    _sandbox = None


def _require_sandbox() -> "Sandbox":
    if _sandbox is None:
        raise RuntimeError("Sandbox not initialised. Call set_sandbox() first.")
    return _sandbox


def _is_allowed(cmd: str) -> bool:
    first_token = cmd.strip().split()[0] if cmd.strip() else ""
    return first_token in settings.allowed_commands


@tool
def run_command(cmd: str) -> CommandResult:
    """Run a whitelisted command inside the Docker sandbox."""
    if not _is_allowed(cmd):
        return CommandResult(
            exit_code=1,
            stdout="",
            stderr=f"Command '{cmd.split()[0]}' is not in the allowed list.",
        )
    box = _require_sandbox()
    exit_code, output = box.exec(cmd)
    return CommandResult(exit_code=exit_code, stdout=output, stderr="")


@tool
def run_tests(test_path: str = "tests/", iteration: int = 0) -> SWETestRun:
    """Run pytest inside the Docker sandbox and return structured results."""
    box = _require_sandbox()
    start = time.monotonic()
    exit_code, output = box.exec(f"pytest {test_path} -v --tb=short --no-header -q")
    duration_ms = int((time.monotonic() - start) * 1000)

    passed, failed, errors = _parse_pytest_output(output)
    return SWETestRun(
        iteration=iteration,
        exit_code=exit_code,
        passed=passed,
        failed=failed,
        errors=errors,
        duration_ms=duration_ms,
        raw_output=output,
    )


def _parse_pytest_output(output: str) -> tuple[int, int, list[str]]:
    passed = 0
    failed = 0
    errors: list[str] = []

    summary_match = re.search(
        r"(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) error)?",
        output,
    )
    if summary_match:
        passed = int(summary_match.group(1) or 0)
        failed = int(summary_match.group(2) or 0)

    for match in re.finditer(r"FAILED (.+?) - (.+)", output):
        errors.append(f"{match.group(1)}: {match.group(2)}")

    for match in re.finditer(r"ERROR (.+?) - (.+)", output):
        errors.append(f"ERROR {match.group(1)}: {match.group(2)}")

    if not summary_match and exit_code_in_output(output):
        failed = 1

    return passed, failed, errors


def exit_code_in_output(output: str) -> bool:
    return "error" in output.lower() or "exception" in output.lower()
