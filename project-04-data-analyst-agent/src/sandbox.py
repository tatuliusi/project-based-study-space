import ast
import subprocess
import sys
import tempfile
from pathlib import Path

_TIMEOUT = 30
_BLOCKED_IMPORTS = {
    "subprocess", "socket", "ftplib", "smtplib", "http", "urllib",
    "importlib", "ctypes", "mmap", "signal", "resource",
    "multiprocessing", "threading", "concurrent",
}

_PREAMBLE = """\
import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import math, statistics, json, re, datetime
from collections import Counter, defaultdict
from itertools import groupby

import os
DATA_FILE = {data_file!r}
CHART_DIR = {chart_dir!r}
os.makedirs(CHART_DIR, exist_ok=True)


def save_chart(name):
    path = os.path.join(CHART_DIR, name)
    plt.savefig(path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"CHART_SAVED:{{path}}")


"""


def _check_imports(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _BLOCKED_IMPORTS:
                    return f"Blocked import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in _BLOCKED_IMPORTS:
                    return f"Blocked import: {node.module}"
    return None


def run_code(code: str, data_file: str, chart_dir: str) -> tuple[str, str, bool]:
    """Run code in a subprocess sandbox. Returns (stdout, stderr, success)."""
    err = _check_imports(code)
    if err:
        return "", err, False

    preamble = _PREAMBLE.format(data_file=data_file, chart_dir=chart_dir)
    full_code = preamble + "\n" + code

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(full_code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        return proc.stdout, proc.stderr, proc.returncode == 0
    except subprocess.TimeoutExpired:
        return "", f"Execution timed out after {_TIMEOUT}s", False
    finally:
        Path(tmp_path).unlink(missing_ok=True)
