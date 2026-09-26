"""Construct a compact, LLM-ready prompt payload from analysis metadata.

This module is *pure* — it performs no I/O, makes no network calls, and has
no side effects.  It transforms three already-computed data structures into a
single JSON-serializable dict that a language model (or the deterministic
fallback) can consume to produce test plans.

Input types
-----------
function_meta : dict
    One entry from :func:`~analyzer.code_analysis.function_extractor.extract_functions`.
covering_tests : list[dict]
    The subset of test metadata dicts (from
    :func:`~analyzer.code_analysis.test_extractor.extract_tests`) whose
    ``calls`` include the function under analysis.
gap_record : dict
    One entry from
    :func:`~analyzer.gap_detection.repo_gap_analyzer.analyze_repository_gaps`.

Output schema
-------------
::

    {
        "function":        str,           # function name
        "source_file":     str,           # absolute path (for context only)
        "arguments":       list[str],     # positional/keyword parameter names
        "branches":        list[str],     # all condition strings in the function
        "raises":          list[str],     # all "ExcType: message" strings
        "covering_tests":  list[str],     # names of tests that call this function
        "missing_branches": list[str],    # from the gap record
        "missing_exceptions": list[str],  # from the gap record
        "confidence":      str,           # gap confidence rating
        "existing_literals": list,        # literals found across covering tests
        "task":            str,           # static instruction string for the LLM
    }

The ``task`` field is a plain-English instruction that tells the LLM exactly
what to produce; it is fixed so the caller never has to compose prompt text.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TASK_INSTRUCTION = (
    "You are a test-plan generator. "
    "Given the function metadata and gap analysis below, produce a list of "
    "test plan items — one per missing branch or missing exception — each "
    "describing WHAT to test and WHY, without writing any code. "
    "For each item include: title, reason, inputs (representative values), "
    "and expected_behavior."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summarise_raises(raises: list[dict]) -> list[str]:
    """Convert raw raise dicts to compact human-readable strings.

    ``{"exc_type": "ValueError", "message": "Price cannot be negative"}``
    becomes ``'ValueError: "Price cannot be negative"'``.
    """
    summaries = []
    for r in raises:
        exc = r.get("exc_type", "")
        msg = r.get("message", "")
        summaries.append(f'{exc}: "{msg}"' if msg else exc)
    return summaries


def _collect_existing_literals(covering_tests: list[dict]) -> list[Any]:
    """Return a deduplicated, ordered list of all literals from *covering_tests*.

    Preserves first-seen order across all tests so the payload stays stable.
    """
    seen: set = set()
    result = []
    for test in covering_tests:
        for lit in test.get("literals", []):
            key = (type(lit).__name__, lit)
            if key not in seen:
                seen.add(key)
                result.append(lit)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_prompt_payload(
    function_meta: dict,
    covering_tests: list[dict],
    gap_record: dict,
) -> dict[str, Any]:
    """Assemble a compact, JSON-serializable prompt payload.

    The result is suitable for either:

    - serialising to JSON and sending to an LLM as the ``user`` message body, or
    - passing directly to the deterministic fallback planner.

    No external calls or I/O are performed.

    Args:
        function_meta:   Metadata dict for one source function.
        covering_tests:  Test metadata dicts whose ``calls`` include this function.
        gap_record:      Gap record for this function from ``analyze_repository_gaps``.

    Returns:
        A JSON-serializable dict (see module docstring for the full schema).
    """
    return {
        "function":           function_meta["name"],
        "source_file":        function_meta["source_file"],
        "arguments":          function_meta.get("arguments", []),
        "branches":           [b["condition"] for b in function_meta.get("branches", [])],
        "raises":             _summarise_raises(function_meta.get("raises", [])),
        "covering_tests":     [t["name"] for t in covering_tests],
        "missing_branches":   gap_record.get("missing_branches", []),
        "missing_exceptions": gap_record.get("missing_exceptions", []),
        "confidence":         gap_record.get("confidence", ""),
        "existing_literals":  _collect_existing_literals(covering_tests),
        "task":               _TASK_INSTRUCTION,
    }
