"""Extract structured metadata from Python source files using the AST.

For each function defined at the top level of a module this module extracts:

- ``name``            – function name
- ``source_file``     – absolute path to the file
- ``arguments``       – positional/keyword argument names (no ``*args``/``**kwargs`` noise)
- ``branches``        – list of ``{"condition": str}`` for every ``if`` statement
- ``raises``          – list of ``{"exc_type": str, "message": str}`` for every ``raise``
- ``returns``         – list of unparsed return-expression strings where a value is present

All values are JSON-serializable (strings, lists, dicts).
"""

import ast
import os
from pathlib import Path

from analyzer.code_analysis.repo_scanner import discover_files


# ---------------------------------------------------------------------------
# Low-level AST helpers
# ---------------------------------------------------------------------------

def _parse_file(path: str) -> ast.Module:
    return ast.parse(Path(path).read_text(encoding="utf-8"))


def _top_level_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    """Return every top-level ``FunctionDef`` in *tree*."""
    return [
        node for node in ast.iter_child_nodes(tree)
        if isinstance(node, ast.FunctionDef)
    ]


def _extract_arguments(func: ast.FunctionDef) -> list[str]:
    """Return the plain argument names for *func* (positional + keyword-only).

    ``*args`` and ``**kwargs`` are excluded because they do not map to
    individual parameter names that a caller must supply.
    """
    args = func.args
    names: list[str] = []
    for arg in args.posonlyargs + args.args + args.kwonlyargs:
        names.append(arg.arg)
    return names


def _extract_branches(func: ast.FunctionDef) -> list[dict]:
    """Return one entry per ``if`` statement inside *func*.

    Each entry::

        {"condition": "<unparsed condition string>"}
    """
    results = []
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        try:
            condition = ast.unparse(node.test)
        except Exception:
            condition = "<condition>"
        results.append({"condition": condition})
    return results


def _extract_raises(func: ast.FunctionDef) -> list[dict]:
    """Return one entry per ``raise`` inside *func*.

    Each entry::

        {"exc_type": "ValueError", "message": "Price cannot be negative"}

    ``message`` is the first string-literal argument to the exception
    constructor, or ``""`` when none is present.
    """
    results = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        exc = node.exc
        exc_type = ""
        message = ""
        if isinstance(exc, ast.Call):
            if isinstance(exc.func, ast.Name):
                exc_type = exc.func.id
            elif isinstance(exc.func, ast.Attribute):
                exc_type = exc.func.attr
            if exc.args and isinstance(exc.args[0], ast.Constant):
                message = str(exc.args[0].value)
        elif isinstance(exc, ast.Name):
            exc_type = exc.id
        results.append({"exc_type": exc_type, "message": message})
    return results


def _extract_returns(func: ast.FunctionDef) -> list[str]:
    """Return one unparsed expression string per ``return <value>`` statement.

    Bare ``return`` (no value) is omitted because it carries no information
    about what the function produces.
    """
    results = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        try:
            expr = ast.unparse(node.value)
        except Exception:
            expr = "<return value>"
        results.append(expr)
    return results


# ---------------------------------------------------------------------------
# Per-file extraction
# ---------------------------------------------------------------------------

def extract_functions(source_file: str) -> list[dict]:
    """Parse *source_file* and return structured metadata for every function.

    Args:
        source_file: Path to a Python source file.

    Returns:
        A list of dicts — one per top-level function — each containing::

            {
                "name":        str,
                "source_file": str,         # absolute path
                "arguments":   list[str],
                "branches":    list[{"condition": str}],
                "raises":      list[{"exc_type": str, "message": str}],
                "returns":     list[str],
            }
    """
    abs_path = os.path.abspath(source_file)
    tree = _parse_file(abs_path)
    results = []
    for func in _top_level_functions(tree):
        results.append({
            "name":        func.name,
            "source_file": abs_path,
            "arguments":   _extract_arguments(func),
            "branches":    _extract_branches(func),
            "raises":      _extract_raises(func),
            "returns":     _extract_returns(func),
        })
    return results


# ---------------------------------------------------------------------------
# Repository-level extraction
# ---------------------------------------------------------------------------

def extract_repository_functions(repo_path: str) -> list[dict]:
    """Discover all source files in *repo_path* and extract function metadata.

    Uses :func:`~analyzer.code_analysis.repo_scanner.discover_files` for
    discovery, so the same ignore rules and test-file filters apply.

    Args:
        repo_path: Absolute or relative path to the repository root.

    Returns:
        A flat list of function-metadata dicts (see :func:`extract_functions`),
        one entry per function across all discovered source files.
    """
    discovered = discover_files(repo_path)
    all_functions = []
    for source_file in discovered["source_files"]:
        all_functions.extend(extract_functions(source_file))
    return all_functions
