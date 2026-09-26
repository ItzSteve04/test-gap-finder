"""Runs a generated pytest module against a repository.

Writes the module text to a temporary file inside the repository's tests
directory, executes pytest as a subprocess, captures the output, then removes
the temporary file regardless of outcome.

Coverage is measured in two passes:
  1. Original tests only  → coverage_before
  2. Original + generated → coverage_after
"""

import re
import subprocess
import sys
from pathlib import Path

def _extract_potential_bug_findings(stdout: str) -> list[dict]:
    """Extract failing generated tests as potential bug findings."""

    findings: list[dict] = []

    for line in stdout.splitlines():
        stripped = line.strip()

        if "_generated_tests_tmp.py::" not in stripped:
            continue

        if " FAILED" not in stripped:
            continue

        try:
            test_part = stripped.split("::", 1)[1]
            test_name = test_part.split()[0]
        except (IndexError, ValueError):
            continue

        finding = {
            "test_name": test_name,
            "status": "potential_bug",
            "reason": (
                "A generated test was valid and collected successfully, "
                "but failed against the target implementation."
            ),
        }

        if finding not in findings:
            findings.append(finding)

    return findings


def run_tests(module_text: str, repo_path: str,
              test_files: list[str] | None = None,
              source_dirs: list[str] | None = None) -> dict:
    """Write *module_text* to a temp file, run pytest with coverage, return results.

    Coverage is measured twice:
      - *before*: original test suite only
      - *after*:  original suite + generated temp file

    Args:
        module_text:  Full pytest module source (from ``generate_test_module()``).
        repo_path:    Root of the repository (used to locate a ``tests/``
                      directory for the temporary file).
        test_files:   Explicit list of test-file paths to use.  When *None*,
                      falls back to ``<repo_path>/tests/test_cart.py`` for
                      backwards compatibility.
        source_dirs:  Directories passed to ``--cov``.  When *None*, falls
                      back to ``<repo_path>/src`` for backwards compatibility.

    Returns:
        A dict with::

            {
                "passed":           int,
                "failed":           int,
                "exit_code":        int,
                "coverage_before":  float,   # % covered by original tests
                "coverage_after":   float,   # % covered after adding generated tests
                "potential_bug_findings":  list[dict],
                "stdout":           str,
                "stderr":           str,
            }

        The temporary test file is always removed before returning.
    """
    repo = Path(repo_path)

    # Resolve test files
    if test_files is not None:
        original_tests = [str(p) for p in test_files]
    else:
        original_tests = [str(repo / "tests" / "test_cart.py")]

    # Resolve coverage sources
    if source_dirs is not None:
        cov_sources = [str(p) for p in source_dirs]
    else:
        cov_sources = [str(repo / "src")]

    # Find (or create) a writable tests directory for the temp file
    tests_dir = _find_tests_dir(repo, original_tests)
    tmp_path = tests_dir / "_generated_tests_tmp.py"

    # Pass 1 — original tests only
    before_result = _pytest_with_cov(original_tests, cov_sources)
    coverage_before = _parse_coverage(before_result.stdout)

    # Pass 2 — original + generated tests
    try:
        tmp_path.write_text(module_text, encoding="utf-8")
        after_result = _pytest_with_cov(original_tests + [str(tmp_path)], cov_sources)
        coverage_after = _parse_coverage(after_result.stdout)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    passed = _parse_count(after_result.stdout, "passed")
    failed = _parse_count(after_result.stdout, "failed")

    potential_bug_findings = _extract_potential_bug_findings(
        after_result.stdout
    )

    return {
        "passed":                  passed,
        "failed":                  failed,
        "exit_code":               after_result.returncode,
        "coverage_before":         coverage_before,
        "coverage_after":          coverage_after,
        "potential_bug_findings":  potential_bug_findings,
        "stdout":                  after_result.stdout,
        "stderr":                  after_result.stderr,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_tests_dir(repo: Path, test_file_paths: list[str]) -> Path:
    """Return a directory suitable for writing the temporary test file.

    Prefers the parent directory of the first discovered test file so the
    generated module lives alongside the real tests.  Falls back to
    ``<repo>/tests``, creating it if necessary.
    """
    if test_file_paths:
        candidate = Path(test_file_paths[0]).parent
        if candidate.is_dir():
            return candidate
    fallback = repo / "tests"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _pytest_with_cov(test_paths: list[str], cov_sources: list[str]):
    """Run pytest with coverage over *cov_sources* for the given *test_paths*."""
    cov_args = []
    for src in cov_sources:
        cov_args += [f"--cov={src}"]
    return subprocess.run(
        [
            sys.executable, "-m", "pytest",
            *test_paths,
            "-v", "--tb=short",
            *cov_args,
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
