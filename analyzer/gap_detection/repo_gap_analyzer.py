"""Repository-level gap comparison between source functions and their tests.

This module combines :mod:`~analyzer.code_analysis.function_extractor` and
:mod:`~analyzer.code_analysis.test_extractor` to answer, for every source
function in a repository:

- which tests call that function,
- which of the function's branches are not exercised by those tests,
- which of the function's raised exceptions are not covered by those tests.

Public entry point
------------------
:func:`analyze_repository_gaps` — accepts a repo root path and returns a
JSON-serializable list of gap records (one per function that has gaps).

Gap record schema
-----------------
::

    {
        "function":          str,        # function name
        "source_file":       str,        # absolute path to the source module
        "covering_tests":    list[str],  # test function names that call this function
        "missing_branches":  list[str],  # condition strings not covered
        "missing_exceptions": list[str], # "ExcType: message" strings not covered
        "confidence":        str,        # "high" | "medium" | "low"
        "reason":            str,        # human-readable explanation of the confidence rating
    }

Functions with no branches and no raises are omitted entirely — they have
nothing to gap-analyse.  Functions with branches/raises but *zero* covering
tests receive ``confidence = "high"`` (all paths are certainly untested).
"""

import re
from typing import Any

from analyzer.code_analysis.function_extractor import extract_repository_functions
from analyzer.code_analysis.test_extractor import extract_repository_tests


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _function_is_called_by_test(func_name: str, test_meta: dict) -> bool:
    """Return True if *test_meta* contains a direct call to *func_name*.

    A test is considered to cover a function when the function's plain name
    appears in the test's ``calls`` list.  Method-call forms like
    ``obj.func_name`` are also matched so that wrapper patterns are captured.
    """
    for call in test_meta["calls"]:
        callee: str = call["func"]
        # Direct call: "func_name"
        if callee == func_name:
            return True
        # Attribute call: "something.func_name"
        if callee.endswith(f".{func_name}"):
            return True
    return False


def _raise_is_covered(raise_info: dict, covering_tests: list[dict]) -> bool:
    """Return True if any covering test exercises this raise path.

    A raise is considered covered when the exception type *and* (when a
    message is present) a substring of the message appear together in the
    same test's ``expected_exceptions`` list, or when the message text alone
    appears in the test's ``literals``.
    """
    exc_type: str = raise_info["exc_type"].lower()
    message: str = raise_info["message"].lower()

    for test in covering_tests:
        # Strategy 1: explicit pytest.raises(...) block
        for ee in test["expected_exceptions"]:
            if ee["exc_type"].lower() == exc_type:
                if not message:
                    return True  # type match is enough when there's no message
                match_val: str = (ee["match"] or "").lower()
                if message in match_val or match_val in message:
                    return True

        # Strategy 2: the exception message literal appears verbatim in the test
        if message and any(
            message in str(lit).lower() for lit in test["literals"]
        ):
            return True

    return False


def _branch_is_covered(branch_info: dict, covering_tests: list[dict]) -> bool:
    """Return True if any covering test appears to exercise this branch.

    Strategy: extract distinctive string literals from the branch condition
    and check whether they appear in any covering test's ``literals`` list.
    Pure variable/comparator conditions that carry no string literals cannot
    be confirmed covered, so they are flagged as gaps (conservative).
    """
    condition: str = branch_info["condition"]

    # Collect string constants embedded in the condition string itself
    # (they were already parsed — re-extract from the condition text)
    string_literals_in_condition = re.findall(r'"([^"]+)"|\'([^\']+)\'', condition)
    distinctive = [a or b for a, b in string_literals_in_condition]

    if not distinctive:
        # No string literals → cannot confirm coverage, flag as gap
        return False

    for test in covering_tests:
        test_literal_strings = {str(lit).lower() for lit in test["literals"]}
        if all(d.lower() in test_literal_strings for d in distinctive):
            return True

    return False


# ---------------------------------------------------------------------------
# Confidence rating
# ---------------------------------------------------------------------------

def _rate_confidence(
    func_meta: dict,
    covering_tests: list[dict],
    missing_branches: list[str],
    missing_exceptions: list[str],
) -> tuple[str, str]:
    """Return a ``(confidence, reason)`` pair for the gap record.

    Confidence levels:

    high
        The function is never called by any test — all paths are gaps.
    medium
        The function is called by at least one test but still has gaps;
        the covering tests don't exercise every branch/raise.
    low
        Only branch conditions without distinctive literals were flagged;
        the heuristic cannot confirm coverage so gaps are conservative.
    """
    if not covering_tests:
        return (
            "high",
            "Function is not called by any test — all paths are untested.",
        )

    # Distinguish heuristic-only gaps (branch conditions with no string literals)
    # from gaps confirmed by explicit exception/literal matching.
    all_branches = func_meta["branches"]
    heuristic_only = all(
        not re.findall(r'"([^"]+)"|\'([^\']+)\'', b["condition"])
        for b in all_branches
        if f"branch: {b['condition']}" in missing_branches
        or b["condition"] in missing_branches
    )

    if missing_exceptions or not heuristic_only:
        return (
            "medium",
            (
                f"Function is covered by {len(covering_tests)} test(s) but "
                "missing branches or exceptions were detected."
            ),
        )

    return (
        "low",
        (
            "Branch gaps are based on heuristic matching only "
            "(no distinctive string literals in conditions); "
            "manual review recommended."
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_repository_gaps(repo_path: str) -> list[dict[str, Any]]:
    """Scan *repo_path* and return gap records for every under-tested function.

    Reuses :func:`~analyzer.code_analysis.function_extractor.extract_repository_functions`
    and :func:`~analyzer.code_analysis.test_extractor.extract_repository_tests`
    instead of reparsing files.

    Args:
        repo_path: Absolute or relative path to the repository root.

    Returns:
        A JSON-serializable list of gap records — one per function that has at
        least one missing branch or missing exception.  Functions with no
        branches and no raises are omitted.

        Each record::

            {
                "function":           str,
                "source_file":        str,
                "covering_tests":     list[str],
                "missing_branches":   list[str],
                "missing_exceptions": list[str],
                "confidence":         str,
                "reason":             str,
            }
    """
    all_functions = extract_repository_functions(repo_path)
    all_tests = extract_repository_tests(repo_path)

    gap_records: list[dict[str, Any]] = []

    for func_meta in all_functions:
        branches = func_meta["branches"]   # list[{"condition": str}]
        raises = func_meta["raises"]       # list[{"exc_type": str, "message": str}]

        # Nothing to analyse — skip entirely
        if not branches and not raises:
            continue

        # Identify every test that directly calls this function
        covering_tests = [
            t for t in all_tests
            if _function_is_called_by_test(func_meta["name"], t)
        ]

        # Determine which branches are not covered
        missing_branches: list[str] = []
        for branch in branches:
            if not _branch_is_covered(branch, covering_tests):
                missing_branches.append(branch["condition"])

        # Determine which raises are not covered
        missing_exceptions: list[str] = []
        for raise_info in raises:
            if not _raise_is_covered(raise_info, covering_tests):
                exc_label = raise_info["exc_type"]
                if raise_info["message"]:
                    exc_label += f': "{raise_info["message"]}"'
                missing_exceptions.append(exc_label)

        if not missing_branches and not missing_exceptions:
            continue  # fully covered — nothing to report

        confidence, reason = _rate_confidence(
            func_meta, covering_tests, missing_branches, missing_exceptions
        )

        gap_records.append({
            "function":           func_meta["name"],
            "source_file":        func_meta["source_file"],
            "covering_tests":     [t["name"] for t in covering_tests],
            "missing_branches":   missing_branches,
            "missing_exceptions": missing_exceptions,
            "confidence":         confidence,
            "reason":             reason,
        })

    return gap_records
