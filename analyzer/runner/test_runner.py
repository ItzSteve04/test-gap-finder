"""Runs a generated pytest module against the sample repository.

Writes the module text to a temporary file inside sample_repo/tests/,
executes pytest as a subprocess, captures the output, then removes the
temporary file regardless of outcome.

Coverage is measured in two passes:
  1. Original tests only  → coverage_before
  2. Original + generated → coverage_after
"""

import re
import subprocess
import sys
from pathlib import Path


def run_tests(module_text: str, repo_path: str) -> dict:
    """Write *module_text* to a temp file, run pytest with coverage, return results.

    Coverage is measured twice:
      - *before*: original test suite only
      - *after*:  original suite + generated temp file

    Args:
        module_text: Full pytest module source (from ``generate_test_module()``).
        repo_path:   Root of the repository to test (e.g. ``"sample_repo"``).

    Returns:
        A dict with::

            {
                "passed":           int,
                "failed":           int,
                "exit_code":        int,
                "coverage_before":  float,   # % covered by original tests
                "coverage_after":   float,   # % covered after adding generated tests
                "stdout":           str,
                "stderr":           str,
            }

        The temporary test file is always removed before returning.
    """
    repo = Path(repo_path)
    tests_dir = repo / "tests"
    original_test = str(tests_dir / "test_cart.py")
    tmp_path = tests_dir / "_generated_tests_tmp.py"
    cov_source = str(repo / "src")

    # Pass 1 — original tests only
    before_result = _pytest_with_cov([original_test], cov_source)
    coverage_before = _parse_coverage(before_result.stdout)

    # Pass 2 — original + generated tests
    try:
        tmp_path.write_text(module_text, encoding="utf-8")
        after_result = _pytest_with_cov([original_test, str(tmp_path)], cov_source)
        coverage_after = _parse_coverage(after_result.stdout)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    passed = _parse_count(after_result.stdout, "passed")
    failed = _parse_count(after_result.stdout, "failed")

    return {
        "passed":          passed,
        "failed":          failed,
        "exit_code":       after_result.returncode,
        "coverage_before": coverage_before,
        "coverage_after":  coverage_after,
        "stdout":          after_result.stdout,
        "stderr":          after_result.stderr,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pytest_with_cov(test_paths: list[str], cov_source: str):
    """Run pytest with coverage over *cov_source* for the given *test_paths*."""
    return subprocess.run(
        [
            sys.executable, "-m", "pytest",
            *test_paths,
            "-v", "--tb=short",
            f"--cov={cov_source}",
            "--cov-report=term-missing",
        ],
        capture_output=True,
        text=True,
    )


def _parse_count(stdout: str, word: str) -> int:
    """Extract the integer before *word* from pytest's summary line.

    Example: ``6 passed, 0 warnings in 0.06s``
    """
    m = re.search(rf"(\d+) {word}", stdout)
    return int(m.group(1)) if m else 0


def _parse_coverage(stdout: str) -> float:
    """Extract the total coverage percentage from pytest-cov's TOTAL line.

    Example: ``TOTAL   26   9   65%``  →  65.0
    """
    m = re.search(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout, re.MULTILINE)
    return float(m.group(1)) if m else 0.0
