"""Extract structured metadata from pytest test files using the AST.

For each top-level test function (name starts with ``test_``) this module
extracts:

- ``name``              – test function name
- ``source_file``       – absolute path to the test file
- ``calls``             – every function/method call made inside the test,
                          as ``{"func": str, "args": list[str]}``
- ``assertions``        – every ``assert`` statement, as
                          ``{"expression": str, "message": str | null}``
- ``expected_exceptions``– every ``pytest.raises(...)`` context manager,
                          as ``{"exc_type": str, "match": str | null}``
- ``literals``          – all string and numeric constant values found
                          anywhere in the body, deduplicated, preserving
                          first-seen order

All values are JSON-serializable (strings, lists, dicts, null).
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


def _top_level_test_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    """Return every top-level ``FunctionDef`` whose name starts with ``test_``."""
    return [
        node for node in ast.iter_child_nodes(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]


# ---------------------------------------------------------------------------
# Per-field extractors
# ---------------------------------------------------------------------------

def _extract_calls(func: ast.FunctionDef) -> list[dict]:
    """Return one entry per function or method call inside *func*.

    Each entry::

        {
            "func": "calculate_discount",   # callee name or "obj.method" form
            "args": ["100.0", "10"],        # positional args as unparsed strings
        }

    ``pytest.raises`` context-manager calls are intentionally kept here as
    well — they are also captured separately in :func:`_extract_expected_exceptions`.
    """
    results = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        # Resolve the callee to a readable string
        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Render the full attribute chain (e.g. "pytest.raises", "result.__getitem__")
            try:
                callee = ast.unparse(node.func)
            except Exception:
                callee = node.func.attr
        else:
            try:
                callee = ast.unparse(node.func)
            except Exception:
                callee = "<call>"

        args = []
        for arg in node.args:
            try:
                args.append(ast.unparse(arg))
            except Exception:
                args.append("<arg>")

        results.append({"func": callee, "args": args})
    return results


def _extract_assertions(func: ast.FunctionDef) -> list[dict]:
    """Return one entry per ``assert`` statement in *func*.

    Each entry::

        {
            "expression": "result['total'] == 100.0",
            "message":    null,              # or the assertion message string if present
        }
    """
    results = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Assert):
            continue
        try:
            expression = ast.unparse(node.test)
        except Exception:
            expression = "<assertion>"
        message: str | None = None
        if node.msg is not None:
            try:
                message = ast.unparse(node.msg)
            except Exception:
                message = "<message>"
        results.append({"expression": expression, "message": message})
    return results


def _extract_expected_exceptions(func: ast.FunctionDef) -> list[dict]:
    """Return one entry per ``with pytest.raises(...)`` block in *func*.

    Detects the pattern::

        with pytest.raises(SomeException) as ...:
        with pytest.raises(SomeException, match=r"...") as ...:

    Each entry::

        {
            "exc_type": "ValueError",
            "match":    "Price cannot be negative",  # or null
        }
    """
    results = []
    for node in ast.walk(func):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            call = item.context_expr
            if not isinstance(call, ast.Call):
                continue
            # Accept both `pytest.raises(...)` and bare `raises(...)` (with import alias)
            callee = ""
            if isinstance(call.func, ast.Attribute):
                try:
                    callee = ast.unparse(call.func)
                except Exception:
                    callee = call.func.attr
            elif isinstance(call.func, ast.Name):
                callee = call.func.id

            if not (callee == "pytest.raises" or callee.endswith(".raises") or callee == "raises"):
                continue

            # First positional argument is the exception type
            exc_type = ""
            if call.args:
                try:
                    exc_type = ast.unparse(call.args[0])
                except Exception:
                    exc_type = "<exc_type>"

            # Optional `match=` keyword argument
            match_value: str | None = None
            for kw in call.keywords:
                if kw.arg == "match":
                    try:
                        raw = ast.unparse(kw.value)
                        # Strip surrounding quotes so the value is a plain string
                        match_value = ast.literal_eval(kw.value) if isinstance(kw.value, ast.Constant) else raw
                    except Exception:
                        match_value = None

            results.append({"exc_type": exc_type, "match": match_value})
    return results


def _extract_literals(func: ast.FunctionDef) -> list[str | int | float]:
    """Return deduplicated string and numeric constant values found in *func*.

    Booleans and ``None`` are excluded — they are structural rather than
    domain-meaningful.  Order reflects first appearance in the AST walk.
    """
    seen: set = set()
    results = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Constant):
            continue
        value = node.value
        # Exclude bool (subclass of int), None, bytes
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            continue
        if value not in seen:
            seen.add(value)
            results.append(value)
    return results


def _extract_import_metadata(tree: ast.Module) -> tuple[list[str], dict[str, str]]:
    """Extract imported modules/names and aliases from a test module.

    Examples:

        import sample_repo.src.cart as cart

    becomes:

        imports = ["sample_repo.src.cart"]
        aliases = {"cart": "sample_repo.src.cart"}

    And:

        from sample_repo.src.cart import calculate_discount as calc

    becomes:

        imports = ["sample_repo.src.cart.calculate_discount"]
        aliases = {"calc": "calculate_discount"}

    Imports are module-level metadata and are attached to each test function
    extracted from the file.
    """

    imports: list[str] = []
    aliases: dict[str, str] = {}

    for node in tree.body:
        if isinstance(node, ast.Import):
            for item in node.names:
                imports.append(item.name)

                if item.asname:
                    aliases[item.asname] = item.name
                else:
                    # import package.module
                    # The directly usable name in Python is the first segment.
                    root_name = item.name.split(".")[0]
                    aliases.setdefault(root_name, root_name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            for item in node.names:
                if item.name == "*":
                    imports.append(f"{module}.*" if module else "*")
                    continue

                full_name = f"{module}.{item.name}" if module else item.name
                imports.append(full_name)

                local_name = item.asname or item.name

                # For `from x import function as alias`, keeping the imported
                # symbol name makes alias resolution straightforward.
                aliases[local_name] = item.name

    return imports, aliases

# ---------------------------------------------------------------------------
# Per-file extraction
# ---------------------------------------------------------------------------

def extract_tests(test_file: str) -> list[dict]:
    """Parse *test_file* and return structured metadata for every test function.

    Only top-level functions whose name starts with ``test_`` are included.

    Args:
        test_file: Path to a pytest test file.

    Returns:
        A list of dicts — one per test function — each containing::

            {
                "name":                 str,
                "source_file":          str,          # absolute path
                "calls":                list[{"func": str, "args": list[str]}],
                "assertions":           list[{"expression": str, "message": str | null}],
                "expected_exceptions":  list[{"exc_type": str, "match": str | null}],
                "literals":             list[str | int | float],
            }
    """
    abs_path = os.path.abspath(test_file)
    tree = _parse_file(abs_path)

    imports, aliases = _extract_import_metadata(tree)

    results = []
    for func in _top_level_test_functions(tree):
        results.append({
            "name":                func.name,
            "source_file":         abs_path,
            "calls":               _extract_calls(func),
            "assertions":          _extract_assertions(func),
            "expected_exceptions": _extract_expected_exceptions(func),
            "literals":            _extract_literals(func),
            "imports":             imports,
            "aliases":             aliases,
        })
    return results


# ---------------------------------------------------------------------------
# Repository-level extraction
# ---------------------------------------------------------------------------

def extract_repository_tests(repo_path: str) -> list[dict]:
    """Discover all test files in *repo_path* and extract test metadata.

    Uses :func:`~analyzer.code_analysis.repo_scanner.discover_files` for
    discovery, so the same ignore rules and source/test classification apply.

    Args:
        repo_path: Absolute or relative path to the repository root.

    Returns:
        A flat list of test-metadata dicts (see :func:`extract_tests`),
        one entry per test function across all discovered test files.
    """
    discovered = discover_files(repo_path)
    all_tests = []
    for test_file in discovered["test_files"]:
        all_tests.extend(extract_tests(test_file))
    return all_tests
