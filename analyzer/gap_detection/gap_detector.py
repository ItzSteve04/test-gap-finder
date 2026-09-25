"""Deterministic gap detector using AST analysis.

Parses a source module and its test file to identify branches and raises
that are not exercised by the existing tests.
"""

import ast
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _parse(path: str) -> ast.Module:
    return ast.parse(Path(path).read_text(encoding="utf-8"))


def _top_level_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    """Return all top-level function definitions in the module."""
    return [node for node in ast.iter_child_nodes(tree)
            if isinstance(node, ast.FunctionDef)]


def _called_names_in_test(tree: ast.Module) -> set[str]:
    """Return all function/attribute names called anywhere in the test file."""
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
    return called


# ---------------------------------------------------------------------------
# Branch/raise extraction
# ---------------------------------------------------------------------------

def _extract_raises(func: ast.FunctionDef) -> list[dict]:
    """Return one entry per raise inside *func*.

    Each entry has:
        label   – human-readable description
        message – the string literal passed to the exception (or "")
    """
    results = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        exc = node.exc
        if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
            exc_type = exc.func.id
            msg = ""
            if exc.args and isinstance(exc.args[0], ast.Constant):
                msg = str(exc.args[0].value)
            label = f'raises {exc_type}: "{msg}"' if msg else f"raises {exc_type}"
            results.append({"label": label, "message": msg, "exc_type": exc_type})
    return results


def _extract_branches(func: ast.FunctionDef) -> list[dict]:
    """Return one entry per if-branch inside *func*.

    Each entry has:
        label     – human-readable description
        condition – the unparsed condition string
        literals  – string/numeric literals found in the condition
    """
    results = []
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        try:
            cond = ast.unparse(node.test)
        except Exception:
            cond = "<condition>"
        # Collect string/numeric literals from the condition
        literals = []
        for child in ast.walk(node.test):
            if isinstance(child, ast.Constant):
                literals.append(str(child.value))
        results.append({"label": f"branch: {cond}", "condition": cond, "literals": literals})
    return results


# ---------------------------------------------------------------------------
# Coverage heuristics
# ---------------------------------------------------------------------------

def _raise_is_tested(raise_info: dict, test_text: str) -> bool:
    """Return True if the test file appears to test this raise path.

    A raise is considered tested when its exception message (or a meaningful
    portion of it) appears in the test file — which would only happen if the
    test asserts on the raised exception text (e.g. via pytest.raises /
    match= or a string in assertRaises context).
    """
    msg = raise_info["message"]
    if not msg:
        # No message to search for — fall back to exc type name
        return raise_info["exc_type"].lower() in test_text

    # Use the full message for matching; strip common stop words first
    # so short messages like "Cart is empty" still match on "cart is empty"
    return msg.lower() in test_text


def _branch_is_tested(branch_info: dict, test_text: str) -> bool:
    """Return True if the test file appears to exercise this branch.

    Strategy: look for string/numeric literals that appear in the condition
    (e.g. "SAVE20", "FREESHIP") directly in the test file.  Plain variable-
    name conditions (e.g. `not items`) are detected via their unique string
    literals only; if there are none we cannot confidently say it's untested,
    so we conservatively treat it as tested.
    """
    literals = branch_info["literals"]
    # Only string literals are distinctive enough; numbers like 0/1/100
    # are too common to be reliable signals.
    string_literals = [
        lit for lit in literals
        if not re.fullmatch(r"-?\d+(\.\d+)?", lit)
    ]
    if not string_literals:
        return False  # no distinctive literal → cannot confirm, flag as gap
    # If ANY distinctive literal is absent from the test, the branch is untested
    return all(lit.lower() in test_text for lit in string_literals)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_gaps(source_path: str, test_path: str) -> list[dict]:
    """Analyse *source_path* against *test_path* and return gap findings.

    Args:
        source_path: Path to the Python module to analyse.
        test_path:   Path to the corresponding test file.

    Returns:
        A list of dicts, one per function that has gaps::

            [
                {
                    "function": "calculate_discount",
                    "missing_cases": [
                        "raises ValueError: \\"Price cannot be negative\\"",
                        "raises ValueError: \\"Discount must be between 0 and 100\\"",
                    ]
                },
                ...
            ]
    """
    src_tree = _parse(source_path)
    test_tree = _parse(test_path)
    test_text = Path(test_path).read_text(encoding="utf-8").lower()

    tested_functions = _called_names_in_test(test_tree)
    functions = _top_level_functions(src_tree)

    results = []
    for func in functions:
        raises = _extract_raises(func)
        branches = _extract_branches(func)

        if not raises and not branches:
            continue

        if func.name not in tested_functions:
            # Function never called in tests — all paths are gaps
            missing = [r["label"] for r in raises] + [b["label"] for b in branches]
        else:
            missing = []
            for r in raises:
                if not _raise_is_tested(r, test_text):
                    missing.append(r["label"])
            for b in branches:
                if not _branch_is_tested(b, test_text):
                    missing.append(b["label"])

        if missing:
            results.append({
                "function": func.name,
                "missing_cases": missing,
            })

    return results
