"""Runs a generated pytest module against the sample repository.

Writes the module text to a temporary file inside sample_repo/tests/,
executes pytest as a subprocess, captures the output, then removes the
temporary file regardless of outcome.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def run_tests(module_text: str, repo_path: str) -> dict:
    """Write *module_text* to a temp file, run pytest, return structured results.

    Args:
        module_text: Full pytest module source (from ``generate_test_module()``).
        repo_path:   Root of the repository to test (e.g. ``"sample_repo"``).

    Returns:
        A dict with::

            {
                "passed":    int,   # number of passing tests
                "failed":    int,   # number of failing tests
                "exit_code": int,   # raw pytest exit code
                "stdout":    str,
                "stderr":    str,
            }

        The temporary test file is always removed before returning.
    """
    tests_dir = Path(repo_path) / "tests"
    tmp_path = tests_dir / "_generated_tests_tmp.py"

    try:
        tmp_path.write_text(module_text, encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(tmp_path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    passed = _parse_count(result.stdout, "passed")
    failed = _parse_count(result.stdout, "failed")

    return {
        "passed":    passed,
        "failed":    failed,
        "exit_code": result.returncode,
        "stdout":    result.stdout,
        "stderr":    result.stderr,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_count(stdout: str, word: str) -> int:
    """Extract the integer before *word* from pytest's summary line.

    Example line: ``6 passed, 0 warnings in 0.06s``
    """
    m = re.search(rf"(\d+) {word}", stdout)
    return int(m.group(1)) if m else 0
