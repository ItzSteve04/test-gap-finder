"""Extract metadata from Python source functions and class methods."""

from __future__ import annotations

import ast
import os

from analyzer.code_analysis.repo_scanner import discover_files


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_file(path: str) -> ast.Module:
    """Parse a Python file and return its AST."""

    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()

    return ast.parse(source, filename=path)


def _safe_unparse(node: ast.AST | None) -> str:
    """Return source-like text for an AST node."""

    if node is None:
        return ""

    try:
        return ast.unparse(node)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Function metadata helpers
# ---------------------------------------------------------------------------


def _extract_arguments(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Return function argument names."""

    arguments: list[str] = []

    for arg in node.args.posonlyargs:
        arguments.append(arg.arg)

    for arg in node.args.args:
        arguments.append(arg.arg)

    if node.args.vararg:
        arguments.append(f"*{node.args.vararg.arg}")

    for arg in node.args.kwonlyargs:
        arguments.append(arg.arg)

    if node.args.kwarg:
        arguments.append(f"**{node.args.kwarg.arg}")

    return arguments


def _extract_branches(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict]:
    """Extract branch conditions from a function or method."""

    branches: list[dict] = []

    for child in ast.walk(node):
        if isinstance(child, ast.If):
            branches.append({
                "condition": _safe_unparse(child.test),
            })

        elif isinstance(child, ast.While):
            branches.append({
                "condition": _safe_unparse(child.test),
            })

        elif isinstance(child, ast.IfExp):
            branches.append({
                "condition": _safe_unparse(child.test),
            })

    return branches


def _extract_raises(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict]:
    """Extract explicit raise statements."""

    raises: list[dict] = []

    for child in ast.walk(node):
        if not isinstance(child, ast.Raise):
            continue

        exc_type = ""
        message = ""

        exc = child.exc

        if isinstance(exc, ast.Call):
            exc_type = _safe_unparse(exc.func)

            if exc.args:
                first_arg = exc.args[0]

                if isinstance(first_arg, ast.Constant):
                    if isinstance(first_arg.value, str):
                        message = first_arg.value
                else:
                    message = _safe_unparse(first_arg)

        elif exc is not None:
            exc_type = _safe_unparse(exc)

        raises.append({
            "exc_type": exc_type,
            "message": message,
        })

    return raises

def _call_name(node: ast.Call) -> str:
    """Return a readable function name for a call expression."""

    return _safe_unparse(node.func)


def _extract_calls(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Extract function/dependency calls made inside a callable."""

    calls: list[str] = []

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            call_name = _call_name(child)

            if call_name and call_name not in calls:
                calls.append(call_name)

    return calls

def _extract_returns(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Extract return expressions."""

    returns: list[str] = []

    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            returns.append(_safe_unparse(child.value))

    return returns


def _build_function_metadata(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_file: str,
    class_name: str | None = None,
) -> dict:
    """Build metadata for one function or class method."""

    is_method = class_name is not None
    is_async = isinstance(node, ast.AsyncFunctionDef)

    qualified_name = (
        f"{class_name}.{node.name}"
        if class_name
        else node.name
    )

    arguments = _extract_arguments(node)

    # self/cls are implementation details rather than caller-supplied values.
    public_arguments = [
        argument
        for argument in arguments
        if argument not in {"self", "cls"}
    ]

    return {
        # Keep `name` as the raw callable name for compatibility with the
        # existing matcher and planner.
        "name": node.name,

        # New richer metadata.
        "qualified_name": qualified_name,
        "class_name": class_name,
        "is_method": is_method,
        "is_async": is_async,

        "source_file": source_file,
        "arguments": public_arguments,
        "branches": _extract_branches(node),
        "raises": _extract_raises(node),
        "returns": _extract_returns(node),
        "calls": _extract_calls(node),
    }


# ---------------------------------------------------------------------------
# Per-file extraction
# ---------------------------------------------------------------------------


def extract_functions(source_file: str) -> list[dict]:
    """Extract top-level functions and class methods from a Python file.

    Supported callable types:

    - def function(...)
    - async def function(...)
    - class methods
    - async class methods

    Nested functions are intentionally ignored for now.
    """

    abs_path = os.path.abspath(source_file)
    tree = _parse_file(abs_path)

    results: list[dict] = []

    for node in tree.body:

        # ---------------------------------------------------------------
        # Top-level synchronous or async function
        # ---------------------------------------------------------------
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            results.append(
                _build_function_metadata(
                    node=node,
                    source_file=abs_path,
                    class_name=None,
                )
            )

        # ---------------------------------------------------------------
        # Class methods
        # ---------------------------------------------------------------
        elif isinstance(node, ast.ClassDef):

            for child in node.body:
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    results.append(
                        _build_function_metadata(
                            node=child,
                            source_file=abs_path,
                            class_name=node.name,
                        )
                    )

    return results


# ---------------------------------------------------------------------------
# Repository extraction
# ---------------------------------------------------------------------------


def extract_repository_functions(repo_path: str) -> list[dict]:
    """Extract function metadata from every discovered source file."""

    discovered = discover_files(repo_path)

    results: list[dict] = []

    for source_file in discovered["source_files"]:
        try:
            results.extend(extract_functions(source_file))
        except (SyntaxError, UnicodeDecodeError, OSError):
            # One unsupported/broken source file should not prevent the rest
            # of the repository from being analyzed.
            continue

    return results