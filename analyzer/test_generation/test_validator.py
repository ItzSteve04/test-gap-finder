"""Validation for generated pytest tests before execution.

This module validates generated test suggestions before they are handed to the
test runner.

Validation stages:
1. Python syntax validation
2. Generated test-name validation
3. Duplicate test-name detection
4. Combined-module syntax validation
5. pytest collection validation

No generated test file is kept permanently. A temporary collection file is
created beside the repository's existing tests and deleted afterwards.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def validate_generated_tests(
    generated_tests: list[dict[str, Any]],
    module_text: str,
    repo_path: str,
    test_files: list[str] | None = None,
) -> dict[str, Any]:
    """Validate generated tests before they are executed.

    Args:
        generated_tests:
            Structured generated tests from ``generate_tests_from_plans()``.

        module_text:
            Full pytest module produced by
            ``generate_test_module_from_plans()``.

        repo_path:
            Root path of the analyzed repository.

        test_files:
            Existing repository test files, when available. These are used to
            choose a suitable temporary tests directory.

    Returns:
        A dictionary containing::

            {
                "validation_results": [...],
                "valid_tests": [...],
                "invalid_tests": [...],
                "validated_module_text": str,
                "collection": {
                    "success": bool,
                    "exit_code": int,
                    "stdout": str,
                    "stderr": str,
                },
            }
    """

    validation_results: list[dict[str, Any]] = []
    valid_tests: list[dict[str, Any]] = []
    invalid_tests: list[dict[str, Any]] = []

    seen_names: set[str] = set()

    # ------------------------------------------------------------------
    # Stage 1: validate each generated test independently
    # ------------------------------------------------------------------

    for test in generated_tests:
        function_name = str(test.get("function", ""))
        gap = str(test.get("gap", ""))
        code = str(test.get("code", ""))

        result = {
            "function": function_name,
            "gap": gap,
            "test_name": None,
            "status": "invalid",
            "reason": "",
        }

        if not code.strip():
            result["reason"] = "Generated test code is empty."
            validation_results.append(result)
            invalid_tests.append(test)
            continue

        # Syntax validation
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            result["reason"] = (
                f"Python syntax error: {exc.msg} "
                f"at line {exc.lineno or 'unknown'}."
            )
            validation_results.append(result)
            invalid_tests.append(test)
            continue

        # Find generated pytest function definitions.
        test_function_names = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ]

        if not test_function_names:
            result["reason"] = "No pytest test function was found in generated code."
            validation_results.append(result)
            invalid_tests.append(test)
            continue

        if len(test_function_names) != 1:
            result["reason"] = (
                "Generated suggestion must contain exactly one pytest test "
                f"function, found {len(test_function_names)}."
            )
            validation_results.append(result)
            invalid_tests.append(test)
            continue

        test_name = test_function_names[0]
        result["test_name"] = test_name

        # Duplicate-name validation
        if test_name in seen_names:
            result["reason"] = f"Duplicate generated test name: {test_name}"
            validation_results.append(result)
            invalid_tests.append(test)
            continue

        seen_names.add(test_name)

        result["status"] = "valid"
        result["reason"] = "Python syntax and generated test name are valid."

        validation_results.append(result)
        valid_tests.append(test)

    # ------------------------------------------------------------------
    # Stage 2: rebuild module with valid tests only
    # ------------------------------------------------------------------

    validated_module_text = _rebuild_module_with_valid_tests(
        module_text,
        valid_tests,
    )

    # Make sure the complete module is syntactically valid too.
    try:
        ast.parse(validated_module_text)
    except SyntaxError as exc:
        reason = (
            f"Combined generated module has invalid Python syntax: "
            f"{exc.msg} at line {exc.lineno or 'unknown'}."
        )

        for result in validation_results:
            if result["status"] == "valid":
                result["status"] = "invalid"
                result["reason"] = reason

        invalid_tests.extend(valid_tests)
        valid_tests = []

        return {
            "validation_results": validation_results,
            "valid_tests": valid_tests,
            "invalid_tests": invalid_tests,
            "validated_module_text": _extract_module_header(module_text),
            "collection": {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": reason,
            },
        }

    # ------------------------------------------------------------------
    # Stage 3: pytest collection validation
    # ------------------------------------------------------------------

    if not valid_tests:
        return {
            "validation_results": validation_results,
            "valid_tests": valid_tests,
            "invalid_tests": invalid_tests,
            "validated_module_text": validated_module_text,
            "collection": {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": "No valid generated tests were available for collection.",
            },
        }

    collection = _collect_with_pytest(
        module_text=validated_module_text,
        repo_path=repo_path,
        test_files=test_files,
    )

    # If pytest cannot collect the generated module, none of these tests
    # should be executed.
    if not collection["success"]:
        reason = "pytest collection failed for the generated test module."

        for result in validation_results:
            if result["status"] == "valid":
                result["status"] = "invalid"
                result["reason"] = reason

        invalid_tests.extend(valid_tests)
        valid_tests = []

    return {
        "validation_results": validation_results,
        "valid_tests": valid_tests,
        "invalid_tests": invalid_tests,
        "validated_module_text": validated_module_text,
        "collection": collection,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_module_header(module_text: str) -> str:
    """Return everything before the first generated pytest function.

    ``generate_test_module_from_plans()`` produces imports/header text followed
    by generated ``def test_...`` functions. This preserves those imports while
    allowing us to rebuild the module using only validated tests.
    """

    match = re.search(
        r"(?m)^def\s+test_[A-Za-z0-9_]+\s*\(",
        module_text,
    )

    if match:
        return module_text[: match.start()].rstrip() + "\n"

    return module_text.rstrip() + "\n"


def _rebuild_module_with_valid_tests(
    original_module_text: str,
    valid_tests: list[dict[str, Any]],
) -> str:
    """Build a pytest module containing only tests that passed local checks."""

    header = _extract_module_header(original_module_text)

    snippets = [
        str(test.get("code", "")).strip()
        for test in valid_tests
        if str(test.get("code", "")).strip()
    ]

    if not snippets:
        return header + "\n# No validated generated tests.\n"

    return header + "\n\n" + "\n\n".join(snippets) + "\n"


def _find_tests_dir(
    repo: Path,
    test_file_paths: list[str] | None,
) -> Path:
    """Find a directory suitable for temporary pytest collection files."""

    if test_file_paths:
        first_test = Path(test_file_paths[0])

        if first_test.parent.is_dir():
            return first_test.parent

    fallback = repo / "tests"
    fallback.mkdir(parents=True, exist_ok=True)

    return fallback


def _collect_with_pytest(
    module_text: str,
    repo_path: str,
    test_files: list[str] | None,
) -> dict[str, Any]:
    """Run pytest --collect-only against a temporary generated module."""

    repo = Path(repo_path)
    tests_dir = _find_tests_dir(repo, test_files)

    temp_path = tests_dir / "_generated_tests_validation_tmp.py"

    try:
        temp_path.write_text(module_text, encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(temp_path),
                "--collect-only",
                "-q",
            ],
            capture_output=True,
            text=True,
        )

        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except Exception as exc:
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": f"Collection validation error: {exc}",
        }

    finally:
        if temp_path.exists():
            temp_path.unlink()