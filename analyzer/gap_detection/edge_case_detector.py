"""Heuristic detection of richer test edge-case gaps."""

from __future__ import annotations

import re
from typing import Any


DEPENDENCY_KEYWORDS = {
    "request",
    "requests",
    "http",
    "client",
    "api",
    "database",
    "db",
    "session",
    "fetch",
    "send",
    "publish",
    "commit",
    "save",
    "read",
    "write",
}

TIMEOUT_KEYWORDS = {
    "timeout",
    "retry",
    "retries",
    "backoff",
}


def _all_test_literals(covering_tests: list[dict]) -> list[Any]:
    """Collect literals from all covering tests."""

    literals: list[Any] = []

    for test in covering_tests:
        literals.extend(test.get("literals", []))

    return literals


def _all_test_text(covering_tests: list[dict]) -> str:
    """Build searchable text from test calls and assertions."""

    parts: list[str] = []

    for test in covering_tests:
        for call in test.get("calls", []):
            parts.append(str(call.get("func", "")))

            for arg in call.get("args", []):
                parts.append(str(arg))

        for assertion in test.get("assertions", []):
            parts.append(str(assertion.get("expression", "")))

    return " ".join(parts).lower()


def _contains_none_check(condition: str) -> bool:
    text = condition.lower()

    return any(
        pattern in text
        for pattern in (
            " is none",
            " is not none",
            " == none",
            " != none",
        )
    )


def _looks_like_empty_check(condition: str) -> bool:
    text = condition.strip().lower()

    if re.fullmatch(r"not\s+[a-zA-Z_][a-zA-Z0-9_]*", text):
        return True

    empty_patterns = (
        "== []",
        "== {}",
        "== ()",
        '== ""',
        "== ''",
        "len(",
    )

    return any(pattern in text for pattern in empty_patterns)


def _numeric_boundary(condition: str) -> float | int | None:
    """Return a numeric comparison boundary if one is present."""

    match = re.search(
        r"(?:<=|>=|<|>|==|!=)\s*(-?\d+(?:\.\d+)?)",
        condition,
    )

    if not match:
        return None

    raw_value = match.group(1)

    try:
        if "." in raw_value:
            return float(raw_value)

        return int(raw_value)
    except ValueError:
        return None


def _string_values(condition: str) -> list[str]:
    """Return string literals present in a condition."""

    matches = re.findall(
        r'"([^"]+)"|\'([^\']+)\'',
        condition,
    )

    return [a or b for a, b in matches]


def _dependency_calls(func_meta: dict) -> list[str]:
    """Return calls that look like external/dependency interactions."""

    results: list[str] = []

    for call in func_meta.get("calls", []):
        call_lower = call.lower()

        parts = re.split(r"[._]", call_lower)

        if any(keyword in parts for keyword in DEPENDENCY_KEYWORDS):
            results.append(call)

    return results


def _timeout_or_retry_signals(func_meta: dict) -> list[str]:
    """Return timeout/retry-related signals from calls and arguments."""

    candidates: list[str] = []

    for call in func_meta.get("calls", []):
        if any(keyword in call.lower() for keyword in TIMEOUT_KEYWORDS):
            candidates.append(call)

    for argument in func_meta.get("arguments", []):
        if any(keyword in argument.lower() for keyword in TIMEOUT_KEYWORDS):
            candidates.append(argument)

    return candidates


def detect_edge_case_gaps(
    func_meta: dict,
    covering_tests: list[dict],
    missing_branches: list[str],
) -> list[dict]:
    """Detect likely missing edge-case tests for one function."""

    gaps: list[dict] = []

    literals = _all_test_literals(covering_tests)
    test_text = _all_test_text(covering_tests)

    # ------------------------------------------------------------------
    # Branch-driven edge cases
    # ------------------------------------------------------------------

    for condition in missing_branches:

        # None input
        if _contains_none_check(condition):
            if None not in literals and "none" not in test_text:
                gaps.append({
                    "type": "none_input",
                    "condition": condition,
                    "confidence": "probably",
                    "suggestion": (
                        "Add a test using None for the relevant input."
                    ),
                })

        # Empty collections / empty string
        if _looks_like_empty_check(condition):
            empty_signals = (
                "[]",
                "{}",
                "()",
                '""',
                "''",
            )

            if not any(signal in test_text for signal in empty_signals):
                gaps.append({
                    "type": "empty_input",
                    "condition": condition,
                    "confidence": "probably",
                    "suggestion": (
                        "Add a test using an empty collection or empty value."
                    ),
                })

        # Numeric boundary
        boundary = _numeric_boundary(condition)

        if boundary is not None and boundary not in literals:
            gaps.append({
                "type": "boundary",
                "condition": condition,
                "confidence": "probably",
                "boundary": boundary,
                "suggestion": (
                    f"Add a test at the boundary value {boundary} and "
                    "consider values immediately on either side."
                ),
            })

        # Distinct string/state branch
        string_values = _string_values(condition)

        for value in string_values:
            if str(value).lower() not in {
                str(literal).lower()
                for literal in literals
            }:
                gaps.append({
                    "type": "state_or_value",
                    "condition": condition,
                    "confidence": "probably",
                    "value": value,
                    "suggestion": (
                        f'Add a test exercising the value/state "{value}".'
                    ),
                })

    # ------------------------------------------------------------------
    # Dependency failure hints
    # ------------------------------------------------------------------

    dependency_calls = _dependency_calls(func_meta)

    for dependency_call in dependency_calls:
        gaps.append({
            "type": "dependency_failure",
            "call": dependency_call,
            "confidence": "uncertain",
            "suggestion": (
                f"Consider testing failure or exception behavior from "
                f"dependency call '{dependency_call}'."
            ),
        })

    # ------------------------------------------------------------------
    # Retry / timeout hints
    # ------------------------------------------------------------------

    signals = _timeout_or_retry_signals(func_meta)

    for signal in signals:
        gaps.append({
            "type": "timeout_or_retry",
            "signal": signal,
            "confidence": "uncertain",
            "suggestion": (
                "Consider testing timeout, retry exhaustion, and recovery "
                "behavior."
            ),
        })

    # Remove exact duplicate dicts while preserving order.
    unique: list[dict] = []

    for gap in gaps:
        if gap not in unique:
            unique.append(gap)

    return unique