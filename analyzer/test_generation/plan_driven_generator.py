"""Plan-driven pytest test code generator.

Converts structured test-plan items (as produced by ``generate_test_plan()``)
into ready-to-run pytest function strings — no LLM or external API required.

The generator is intentionally generic: it never contains sample-specific
function names, argument values, or business logic.  All call expressions and
assertion targets are derived from the plan's ``inputs``, ``expected_behavior``
and ``gap_ref`` fields (and the ``prompt_payload`` from the parent entry) at
runtime.

Output schema (same as the legacy generator)
---------------------------------------------
Each returned dict contains:

    function : str   — name of the function under test
    gap      : str   — the ``gap_ref`` string from the plan item
    code     : str   — a syntactically valid pytest function as a string

When a plan item cannot be safely converted to executable pytest code, it is
returned in the ``unsupported`` list rather than the ``generated`` list so the
caller can report it without guessing invalid code.

Public functions
----------------
generate_tests_from_plans(plan_entries)
    Main entry point — accepts the list returned by ``generate_test_plan()``.
    Returns ``(generated: list[dict], unsupported: list[dict])``.
"""

from __future__ import annotations

import ast
import re
import textwrap
from typing import Any


# ---------------------------------------------------------------------------
# Regex patterns used for extracting structured info from plan fields
# ---------------------------------------------------------------------------

# Matches "func_name(arg1=val1, arg2=val2, ...)" in the inputs field.
# We accept both keyword and positional forms since inputs may contain either.
_CALL_RE = re.compile(
    r'^(?P<func>\w+)\((?P<args>[^)]*)\)\s*$'
)

# Matches exception expectation in expected_behavior:
#   "A ValueError is raised ..."
#   "A ValueError is raised with a message containing \"...\""
_EXC_EXPECT_RE = re.compile(
    r'\bA\s+(?P<exc>\w+Error|\w+Exception|\w+Warning)\s+is\s+raised'
    r'(?:.*?containing\s+"(?P<msg>[^"]+)")?',
    re.IGNORECASE | re.DOTALL,
)

# Matches "func(... should return the value ..." or
# "{func}() should return the value associated with ..."
_RETURN_EXPECT_RE = re.compile(
    r'should\s+return\s+the\s+value\s+associated',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Syntax validation
# ---------------------------------------------------------------------------

def _valid_python(code: str) -> bool:
    """Return True when *code* is syntactically valid Python."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


# ---------------------------------------------------------------------------
# Test-name derivation
# ---------------------------------------------------------------------------

def _test_name(func_name: str, gap_ref: str) -> str:
    """Derive a snake_case test function name from *func_name* and *gap_ref*."""
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', gap_ref).strip('_').lower()
    slug = slug[:60].rstrip('_')
    return f"test_{func_name}_{slug}"


# ---------------------------------------------------------------------------
# Code templates
# ---------------------------------------------------------------------------

def _raises_template(
    func_name: str,
    gap_ref: str,
    call_expr: str,
    exc_type: str,
    message: str,
) -> str:
    name = _test_name(func_name, gap_ref)
    match_line = f', match=r"{re.escape(message)}"' if message else ""
    return textwrap.dedent(f"""\
        def {name}():
            with pytest.raises({exc_type}{match_line}):
                {call_expr}
    """)


def _value_template(
    func_name: str,
    gap_ref: str,
    call_expr: str,
    expected: str,
) -> str:
    name = _test_name(func_name, gap_ref)
    return textwrap.dedent(f"""\
        def {name}():
            result = {call_expr}
            assert result == {expected}
    """)


def _generic_call_template(func_name: str, gap_ref: str, call_expr: str) -> str:
    """Minimal test that just calls the function without asserting a value."""
    name = _test_name(func_name, gap_ref)
    return textwrap.dedent(f"""\
        def {name}():
            {call_expr}
    """)


# ---------------------------------------------------------------------------
# Call-expression extraction and argument healing
# ---------------------------------------------------------------------------

def _extract_call_expr(inputs: str) -> str | None:
    """Extract a Python call expression from the plan *inputs* field.

    Accepts the natural-language patterns produced by the DeterministicPlanner:
    ``"func_name(arg=<hint>, ...)"``
    Returns None when the inputs field doesn't contain a recognisable call.
    """
    m = _CALL_RE.match(inputs.strip())
    if not m:
        return None
    func = m.group("func")
    raw_args = m.group("args").strip()

    cleaned_args = _replace_placeholders(raw_args)

    candidate = f"{func}({cleaned_args})"
    if _valid_python(candidate):
        return candidate
    return None


def _replace_placeholders(arg_str: str) -> str:
    """Replace ``=<hint text>`` and bare ``<hint>`` placeholders with ``None``."""
    # keyword=<...> → keyword=None
    arg_str = re.sub(r'=<[^>]+>', '=None', arg_str)
    # Bare <...> (positional) → None
    arg_str = re.sub(r'<[^>]+>', 'None', arg_str)
    return arg_str


def _extract_rhs_value(inputs: str) -> str | None:
    """Extract the RHS value from an equality assignment pattern.

    For branch plans whose inputs field contains ``arg='VALUE'``, pull out the
    value so we can compare against it in the assertion.  Returns None if the
    pattern is not present.

    Example: ``"apply_coupon(total=<valid value>, coupon='SAVE20')"``
             → ``"'SAVE20'"`` (last concrete RHS)
    """
    matches = re.findall(
        r"\w+\s*=\s*(?!'?<)(?P<val>'[^']*'|\"[^\"]*\"|-?\d+(?:\.\d+)?|\w+)",
        inputs,
    )
    if matches:
        return matches[-1]
    return None


# ---------------------------------------------------------------------------
# Condition-aware argument inference
# ---------------------------------------------------------------------------

# Patterns for common guard conditions → violation value to substitute
# Each entry: (condition_regex, arg_name_regex, replacement_python_literal)
# We go through these in order and use the first match.
_CONDITION_VIOLATION_RULES: list[tuple[re.Pattern, re.Pattern, str]] = [
    # arg < 0  → pass -1
    (re.compile(r'^(\w+)\s*<\s*0$'),          re.compile(r'.*'), '-1'),
    # arg <= 0 → pass 0
    (re.compile(r'^(\w+)\s*<=\s*0$'),         re.compile(r'.*'), '0'),
    # not 0 <= arg <= N  → pass N+1
    (re.compile(r'^not\s+0\s*<=\s*(\w+)\s*<=\s*(\d+)$'), re.compile(r'.*'), None),  # handled below
    # not arg  → pass []  (empty collection guard)
    (re.compile(r'^not\s+(\w+)$'),             re.compile(r'.*'), '[]'),
    # arg > N  → pass N+1
    (re.compile(r'^(\w+)\s*>\s*(\d+)$'),       re.compile(r'.*'), None),  # handled below
]


def _violation_value_for_condition(condition: str) -> str | None:
    """Return a Python literal that violates *condition*, or None."""
    s = condition.strip()

    # not 0 <= x <= N  → N + 1
    m = re.match(r'^not\s+0\s*<=\s*\w+\s*<=\s*(\d+)$', s)
    if m:
        hi = int(m.group(1))
        return str(hi + 1)

    # x < 0  → -1
    if re.match(r'^\w+\s*<\s*0$', s):
        return '-1'

    # x <= 0  → 0
    if re.match(r'^\w+\s*<=\s*0$', s):
        return '0'

    # not x  → []
    if re.match(r'^not\s+\w+$', s):
        return '[]'

    # x > N  → N - 1  (violation: going below the minimum)
    m = re.match(r'^\w+\s*>\s*(\d+)$', s)
    if m:
        lo = int(m.group(1))
        return str(max(0, lo - 1))

    return None


def _heal_call_for_exception(
    inputs: str,
    condition: str,
    arguments: list[str],
) -> str | None:
    """Re-build the call expression using a concrete violation value.

    When *inputs* contains placeholder hints (``<value that violates the guard>``),
    use *condition* (the raw branch condition that guards the raise) to infer an
    appropriate concrete argument value.

    The substitution is done argument by argument:
    - The argument whose name appears in *condition* receives the violation value.
    - All other arguments that still have a placeholder receive a safe default.

    Returns a syntactically valid call string, or None when healing is not
    possible (e.g. the condition variable is not a direct function argument).
    """
    m = _CALL_RE.match(inputs.strip())
    if not m:
        return None

    func = m.group("func")
    raw_args = m.group("args").strip()

    # Derive the violating value from the condition
    violation = _violation_value_for_condition(condition)

    # Find which argument name appears in the condition
    condition_args: set[str] = set(re.findall(r'\b([a-zA-Z_]\w*)\b', condition))
    condition_args -= {'not', 'and', 'or', 'in', 'is', 'True', 'False', 'None'}

    # If no condition variable is a direct function argument we cannot safely
    # construct the call — the violating value would have to be buried inside
    # a nested data structure, which we cannot infer generically.
    func_arg_set = set(arguments)
    if condition_args and not (condition_args & func_arg_set):
        return None

    # Parse raw_args into name=value pairs (some may be placeholders)
    # Split on "," but only at top level (no nested brackets)
    arg_parts = _split_args(raw_args)
    healed_parts: list[str] = []
    for part in arg_parts:
        part = part.strip()
        kw_m = re.match(r'^(\w+)\s*=\s*(.+)$', part)
        if kw_m:
            arg_name = kw_m.group(1)
            arg_val = kw_m.group(2).strip()
            is_placeholder = bool(re.match(r'^<[^>]+>$', arg_val))
            if is_placeholder:
                if violation is not None and arg_name in condition_args:
                    healed_parts.append(f"{arg_name}={violation}")
                else:
                    # Safe numeric default: 1 avoids comparison errors with None
                    healed_parts.append(f"{arg_name}=1")
            else:
                healed_parts.append(part)
        else:
            # Positional or raw placeholder
            if re.match(r'^<[^>]+>$', part):
                healed_parts.append('None')
            else:
                healed_parts.append(part)

    candidate = f"{func}({', '.join(healed_parts)})"
    if _valid_python(candidate):
        return candidate
    return None


def _split_args(arg_str: str) -> list[str]:
    """Split a comma-separated argument string respecting nested brackets."""
    parts = []
    depth = 0
    current = []
    for ch in arg_str:
        if ch in ('(', '[', '{'):
            depth += 1
        elif ch in (')', ']', '}'):
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current))
    return parts


# ---------------------------------------------------------------------------
# Per-plan item converter
# ---------------------------------------------------------------------------

def _convert_plan(
    func_name: str,
    plan: dict[str, Any],
    prompt_payload: dict[str, Any] | None = None,
) -> str | None:
    """Attempt to convert one plan item into a pytest function string.

    Returns the code string on success, or None if a safe conversion is not
    possible.

    Args:
        func_name:      Name of the function under test.
        plan:           One plan item dict from ``generate_test_plan()``.
        prompt_payload: The ``prompt_payload`` dict from the parent plan entry,
                        used to retrieve raw condition strings for better
                        argument inference.
    """
    gap_ref: str = plan.get("gap_ref", "")
    inputs: str = plan.get("inputs", "")
    expected: str = plan.get("expected_behavior", "")
    gap_type: str = plan.get("gap_type", "")

    # -----------------------------------------------------------------------
    # Exception plan
    # -----------------------------------------------------------------------
    exc_match = _EXC_EXPECT_RE.search(expected)
    if gap_type == "exception" or exc_match:
        if exc_match:
            exc_type = exc_match.group("exc")
            message = exc_match.group("msg") or ""
        else:
            gr_match = re.match(r'^(\w+)(?:\s*:\s*"(.+)")?$', gap_ref)
            if not gr_match:
                return None
            exc_type = gr_match.group(1)
            message = gr_match.group(2) or ""

        # Try to find the branch condition that guards this raise so we can
        # use a concrete violation value instead of None.
        call_expr = _try_heal_exception_call(inputs, message, gap_ref, prompt_payload)
        if call_expr is None:
            # Healing failed — the condition variable is not a direct function
            # argument (e.g. it's an attribute of a nested dict).  Falling
            # back to None placeholders would likely trigger a different code
            # path and a different exception, so we cannot safely generate
            # this test.
            return None

        code = _raises_template(func_name, gap_ref, call_expr, exc_type, message)
        return code if _valid_python(code) else None

    # -----------------------------------------------------------------------
    # Branch plan
    # -----------------------------------------------------------------------
    if gap_type == "branch":
        # Generic branch: build the call and just verify the branch is
        # reachable (no assertion on return value, since the planner only
        # says "return the value associated…" without giving a concrete
        # expected result).
        call_expr = _try_heal_branch_call(inputs, gap_ref, prompt_payload)
        if call_expr is None:
            call_expr = _extract_call_expr(inputs)
        if call_expr is None:
            return None
        code = _generic_call_template(func_name, gap_ref, call_expr)
        return code if _valid_python(code) else None

    return None


def _try_heal_exception_call(
    inputs: str,
    message: str,
    gap_ref: str,
    prompt_payload: dict[str, Any] | None,
) -> str | None:
    """Find the branch condition linked to this exception and use it to heal the call."""
    if prompt_payload is None:
        return None

    arguments: list[str] = prompt_payload.get("arguments", [])
    missing_branches: list[str] = prompt_payload.get("missing_branches", [])
    missing_exceptions: list[str] = prompt_payload.get("missing_exceptions", [])

    # First try: match on the exception message tokens vs branch conditions
    msg_lower = message.lower()
    msg_tokens = set(re.findall(r'\b\w+\b', msg_lower))
    _NOISE = {'not', 'and', 'or', 'is', 'be', 'to', 'a', 'the', 'an', 'cannot', 'must'}

    best_condition: str | None = None
    best_overlap = 0

    # Check both missing_branches and all branches in the payload
    all_branches: list[str] = list(prompt_payload.get("missing_branches", []))
    for b in prompt_payload.get("branches", []):
        if b not in all_branches:
            all_branches.append(b)

    for condition in all_branches:
        cond_tokens = set(re.findall(r'\b\w+\b', condition.lower()))
        overlap = len((cond_tokens - _NOISE) & (msg_tokens - _NOISE))
        if overlap > best_overlap:
            best_overlap = overlap
            best_condition = condition

    # Also try the truthiness guard heuristic (not x → emptiness guard)
    for condition in all_branches:
        if re.match(r'^not\s+\w+$', condition.strip()):
            empty_words = {'empty', 'none', 'missing', 'required'}
            if msg_tokens & empty_words:
                best_condition = condition
                break

    if best_condition is None:
        return None

    return _heal_call_for_exception(inputs, best_condition, arguments)


def _try_heal_branch_call(
    inputs: str,
    gap_ref: str,
    prompt_payload: dict[str, Any] | None,
) -> str | None:
    """Heal a branch-plan call using the raw branch condition string."""
    if prompt_payload is None:
        return None
    arguments: list[str] = prompt_payload.get("arguments", [])
    # gap_ref for branch plans is the condition string itself
    condition = gap_ref
    return _heal_call_for_exception(inputs, condition, arguments)


# ---------------------------------------------------------------------------
# Module-level imports header
# ---------------------------------------------------------------------------

def _build_imports(
    source_files: list[str],
    function_imports: dict[str, list[str]] | None = None,
) -> str:
    """Build an import block that works for any repository.

    Uses ``sys.path`` insertion so the generated tests remain portable.
    When *function_imports* is supplied (a mapping from dotted module path to
    a list of names to import), explicit ``from <module> import ...`` lines are
    appended so the generated tests can resolve the function names.

    Args:
        source_files:      List of source file absolute paths (used for
                           computing the relative module path).
        function_imports:  Optional ``{module_path: [name, ...]}`` dict.  Each
                           key is a dotted Python module path relative to a
                           ``sys.path`` root; values are the function names to
                           import from that module.
    """
    lines = textwrap.dedent("""\
        import pytest
        import sys
        import os

        # Insert the repo root so relative imports work regardless of cwd.
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    """)
    if function_imports:
        import_lines = []
        for module_path, names in sorted(function_imports.items()):
            names_str = ", ".join(sorted(set(names)))
            import_lines.append(f"from {module_path} import {names_str}")
        lines += "\n" + "\n".join(import_lines) + "\n"
    return lines


def _module_path_from_source(
    source_file: str,
    repo_root: str | None = None,
) -> str | None:
    """Convert an absolute source file path to a dotted Python module path.

    The dotted path is computed relative to *repo_root* (when supplied) or to
    the first ancestor directory that is not itself a Python package (i.e. the
    first ancestor with no ``__init__.py`` in its parent).  The directory name
    of that ancestor is included in the path when it is NOT a package directory.

    Example::
        /repo/src/cart.py  (with repo_root="/repo")  →  "src.cart"
        /repo/src/pkg/mod.py (src/ has __init__.py)  →  "src.pkg.mod"
    """
    try:
        from pathlib import Path
        p = Path(source_file).resolve()
        parts = [p.stem]  # start with module name (filename sans .py)
        current_dir = p.parent

        if repo_root is not None:
            # Walk from source dir up to repo_root, collecting package dirs
            root = Path(repo_root).resolve()
            candidate = current_dir
            while candidate != root:
                parts.insert(0, candidate.name)
                candidate = candidate.parent
        else:
            # Walk up as long as __init__.py exists (standard package walk),
            # then include one more ancestor directory to capture the
            # top-level package/namespace (e.g. "src" in "src/cart.py").
            while (current_dir / "__init__.py").exists():
                parts.insert(0, current_dir.name)
                current_dir = current_dir.parent
            # Include the immediate parent dir if the file isn't at the path
            # root — this handles "src/cart.py" where src/ has no __init__.py
            # but still needs to be in the import path.
            if len(parts) == 1 and current_dir.name:
                parts.insert(0, current_dir.name)

        return ".".join(parts)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_tests_from_plans(
    plan_entries: list[dict[str, Any]],
) -> tuple[list[dict], list[dict]]:
    """Generate pytest test suggestions from ``generate_test_plan()`` output.

    Processes every plan item in every entry.  Duplicates are removed: when
    two plan items produce identical test bodies, only the first is kept.

    Args:
        plan_entries: The list returned by
            :func:`~analyzer.test_generation.planner.generate_test_plan`.

    Returns:
        A two-element tuple ``(generated, unsupported)``:

        *generated* — list of dicts, one per unique generated test::

            [
                {
                    "function": str,  # function under test
                    "gap":      str,  # gap_ref from the plan item
                    "code":     str,  # ready-to-run pytest function string
                },
                ...
            ]

        *unsupported* — list of plan items that could not be safely converted::

            [
                {
                    "function": str,
                    "title":    str,
                    "reason":   str,
                    "gap_ref":  str,
                },
                ...
            ]
    """
    generated: list[dict] = []
    unsupported: list[dict] = []
    seen_bodies: set[str] = set()

    for entry in plan_entries:
        func_name: str = entry.get("function", "")
        plans: list[dict] = entry.get("plans", [])
        prompt_payload: dict[str, Any] | None = entry.get("prompt_payload")

        for plan in plans:
            code = _convert_plan(func_name, plan, prompt_payload)

            if code is None:
                unsupported.append({
                    "function": func_name,
                    "title":    plan.get("title", ""),
                    "reason":   plan.get("reason", ""),
                    "gap_ref":  plan.get("gap_ref", ""),
                })
                continue

            stripped = code.strip()
            # Dedup key: body lines below the `def` heading, so tests that
            # produce identical assertions are counted as one scenario.
            body = "\n".join(stripped.splitlines()[1:])
            if body not in seen_bodies:
                seen_bodies.add(body)
                generated.append({
                    "function": func_name,
                    "gap":      plan.get("gap_ref", ""),
                    "code":     stripped,
                })

    return generated, unsupported


def generate_test_module_from_plans(
    plan_entries: list[dict[str, Any]],
    source_files: list[str] | None = None,
) -> str:
    """Render all generated tests as a single importable pytest module string.

    Automatically builds ``from <module> import <function>`` statements for
    every function that appears in the generated tests, deriving the module
    path from the plan entry's ``source_file`` field.

    Args:
        plan_entries:  Output of ``generate_test_plan()``.
        source_files:  Optional list of source file paths; currently unused
                       but kept for API compatibility.

    Returns:
        A complete Python module string ready for ``run_tests()``.
    """
    generated, _ = generate_tests_from_plans(plan_entries)

    # Infer repo root as the common ancestor of all source file directories.
    from pathlib import Path as _Path
    all_source_dirs = list({
        _Path(e.get("source_file", "")).resolve().parent
        for e in plan_entries
        if e.get("source_file")
    })
    repo_root_inferred: str | None = None
    if all_source_dirs:
        try:
            common_dir = all_source_dirs[0]
            for d in all_source_dirs[1:]:
                while common_dir not in [d] + list(d.parents):
                    common_dir = common_dir.parent
            # The repo root is one level above the common source directory
            repo_root_inferred = str(common_dir.parent)
        except Exception:
            repo_root_inferred = None

    # Build a mapping of module_path -> [function_names] so we can emit
    # one ``from <module> import ...`` line per source module.
    function_imports: dict[str, list[str]] = {}
    source_file_index: dict[str, str] = {
        entry.get("function", ""): entry.get("source_file", "")
        for entry in plan_entries
    }
    for test in generated:
        func_name = test.get("function", "")
        sf = source_file_index.get(func_name, "")
        if sf:
            module_path = _module_path_from_source(sf, repo_root_inferred)
            if module_path:
                function_imports.setdefault(module_path, [])
                if func_name not in function_imports[module_path]:
                    function_imports[module_path].append(func_name)

    header = _build_imports(source_files or [], function_imports or None)
    snippets = [t["code"] for t in generated]
    if not snippets:
        return header + "\n# No test suggestions generated.\n"
    return header + "\n\n" + "\n\n".join(snippets) + "\n"
