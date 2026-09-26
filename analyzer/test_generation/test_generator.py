"""Legacy deterministic pytest test code generator (raw-gap-string based).

Accepts gap detection results from detect_gaps() and returns structured
test suggestions — no LLM or external API required.

.. note::
    This module is kept as a fallback.  The main /analyze workflow now uses
    :mod:`analyzer.test_generation.plan_driven_generator` which accepts the
    structured plan items returned by ``generate_test_plan()`` instead of
    these raw gap strings.

Each suggestion contains:
    - function  : name of the function under test
    - gap       : the missing_cases string that triggered this suggestion
    - code      : a ready-to-run pytest function as a string
"""

import re
import textwrap


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _test_name(function: str, gap: str) -> str:
    """Derive a snake_case test function name from the function and gap."""
    # Strip label prefixes
    label = re.sub(r'^(raises \w+: |raises \w+|branch: )', '', gap)
    # Keep alphanumeric and spaces, collapse to underscores
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', label).strip('_').lower()
    # Truncate so names stay readable
    slug = slug[:60].rstrip('_')
    return f"test_{function}_{slug}"


def _raises_template(function: str, gap: str, exc_type: str,
                     message: str, call_args: str) -> str:
    """Return a pytest test that asserts a specific exception is raised."""
    name = _test_name(function, gap)
    match_line = f', match=r"{re.escape(message)}"' if message else ""
    return textwrap.dedent(f"""\
        def {name}():
            with pytest.raises({exc_type}{match_line}):
                {call_args}
    """)


def _value_template(function: str, gap: str, call_args: str,
                    expected: str) -> str:
    """Return a pytest test that asserts a return value."""
    name = _test_name(function, gap)
    return textwrap.dedent(f"""\
        def {name}():
            result = {call_args}
            assert result == {expected}
    """)


# ---------------------------------------------------------------------------
# Per-gap code generators
# Each handler receives (function_name, gap_string) and returns a code string
# or None if it cannot handle this gap.
# ---------------------------------------------------------------------------

_RAISES_RE = re.compile(r'^raises (\w+): "(.+)"$')
_RAISES_BARE_RE = re.compile(r'^raises (\w+)$')
_BRANCH_RE = re.compile(r'^branch: (.+)$')


def _handle_gap(function: str, gap: str) -> str | None:
    """Map a single gap description to a pytest code string."""

    # ---- raises ValueError: "message" ------------------------------------
    m = _RAISES_RE.match(gap)
    if m:
        exc_type, message = m.group(1), m.group(2)
        call_args = _call_for_raise(function, message)
        if call_args:
            return _raises_template(function, gap, exc_type, message, call_args)

    # ---- raises ExcType (no message) -------------------------------------
    m = _RAISES_BARE_RE.match(gap)
    if m:
        exc_type = m.group(1)
        call_args = _call_for_raise(function, "")
        if call_args:
            return _raises_template(function, gap, exc_type, "", call_args)

    # ---- branch: <condition> ---------------------------------------------
    m = _BRANCH_RE.match(gap)
    if m:
        condition = m.group(1)
        return _handle_branch(function, gap, condition)

    return None


def _call_for_raise(function: str, message: str) -> str | None:
    """Return the function call expression that should trigger the given raise."""
    msg = message.lower()

    if function == "calculate_discount":
        if "negative" in msg:
            return "calculate_discount(-1.0, 10)"
        if "discount" in msg or "between" in msg:
            return "calculate_discount(100.0, 150)"

    if function == "checkout":
        if "empty" in msg:
            return "checkout([])"
        if "quantity" in msg or "positive" in msg:
            return 'checkout([{"price": 10.0, "quantity": 0}])'

    return None


def _handle_branch(function: str, gap: str, condition: str) -> str | None:
    """Return a test for an untested branch condition."""
    cond = condition.strip()

    # apply_coupon branches on specific coupon string literals
    coupon_match = re.search(r"coupon == '([A-Z0-9]+)'", cond)
    if coupon_match and function == "apply_coupon":
        coupon = coupon_match.group(1)
        expected_map = {
            "SAVE20":   ("apply_coupon(100.0, 'SAVE20')", "80.0"),
            "FREESHIP": ("apply_coupon(100.0, 'FREESHIP')", "100.0"),
        }
        if coupon in expected_map:
            call_args, expected = expected_map[coupon]
            return _value_template(function, gap, call_args, expected)
        # Unknown coupon fallback
        return _value_template(
            function, gap,
            "apply_coupon(100.0, 'UNKNOWN')", "100.0",
        )

    # calculate_discount guard branches — same inputs as the raise tests
    if function == "calculate_discount":
        if "price < 0" in cond:
            return _raises_template(
                function, gap, "ValueError", "Price cannot be negative",
                "calculate_discount(-1.0, 10)",
            )
        if "discount_percent" in cond:
            return _raises_template(
                function, gap, "ValueError", "Discount must be between 0 and 100",
                "calculate_discount(100.0, 150)",
            )

    # checkout guard branches
    if function == "checkout":
        if "not items" in cond:
            return _raises_template(
                function, gap, "ValueError", "Cart is empty",
                "checkout([])",
            )
        if "quantity" in cond:
            return _raises_template(
                function, gap, "ValueError", "Quantity must be a positive integer",
                'checkout([{"price": 10.0, "quantity": 0}])',
            )

    return None


# ---------------------------------------------------------------------------
# Module-level imports header
# ---------------------------------------------------------------------------

_IMPORTS = textwrap.dedent("""\
    import pytest
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from src.cart import calculate_discount, apply_coupon, checkout
""")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_tests_legacy(gaps: list[dict]) -> list[dict]:
    """Generate pytest test suggestions from detect_gaps() output (legacy).

    This function is retained for fallback use only.  The main /analyze
    workflow uses
    :func:`~analyzer.test_generation.plan_driven_generator.generate_tests_from_plans`
    which works from structured plan items.

    Duplicates are removed: when two different gaps produce identical test
    bodies, only the first occurrence is kept (preserving insertion order).

    Args:
        gaps: The list of gap dicts returned by detect_gaps(), each with
              keys ``function`` and ``missing_cases``.

    Returns:
        A list of dicts, one per unique generated test::

            [
                {
                    "function": "calculate_discount",
                    "gap": "raises ValueError: \\"Price cannot be negative\\"",
                    "code": "def test_calculate_discount_...:\\n    ..."
                },
                ...
            ]

        Gaps for which no template exists are silently skipped.
    """
    results = []
    seen_bodies: set[str] = set()
    for entry in gaps:
        function = entry["function"]
        for gap in entry["missing_cases"]:
            code = _handle_gap(function, gap)
            if code:
                stripped = code.strip()
                # Dedup key: the test body without the `def` line so that
                # two gaps that produce the same assertions (but different
                # auto-generated function names) are treated as one scenario.
                body = "\n".join(stripped.splitlines()[1:])
                if body not in seen_bodies:
                    seen_bodies.add(body)
                    results.append({
                        "function": function,
                        "gap": gap,
                        "code": stripped,
                    })
    return results


def generate_tests(gaps: list[dict]) -> list[dict]:
    """Backwards-compatible alias for :func:`generate_tests_legacy`.

    Kept so any existing callers of ``generate_tests(gaps)`` continue to work
    without modification.
    """
    return generate_tests_legacy(gaps)


def generate_test_module(gaps: list[dict]) -> str:
    """Render all generated tests as a single importable pytest module string.

    Useful for previewing or writing to disk later.  Uses the legacy gap-string
    path.  For plan-driven output use
    :func:`~analyzer.test_generation.plan_driven_generator.generate_test_module_from_plans`.
    """
    snippets = [t["code"] for t in generate_tests_legacy(gaps)]
    if not snippets:
        return _IMPORTS + "\n# No test suggestions generated.\n"
    return _IMPORTS + "\n\n" + "\n\n".join(snippets) + "\n"
