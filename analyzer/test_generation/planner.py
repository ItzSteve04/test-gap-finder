"""AI-planning interface layer for test-plan generation.

Architecture
------------
There are two layers in this module:

1. **Provider interface** — a single abstract seam represented by
   :class:`PlanProvider`.  Any future AI integration (OpenAI, watsonx, etc.)
   only needs to implement the one-method protocol and be registered via
   :func:`set_provider`.  The rest of the analyzer never changes.

2. **Public entry point** — :func:`generate_test_plan` accepts pre-computed
   analysis data, delegates to the active provider, and returns structured
   test-plan items.

Provider resolution order
~~~~~~~~~~~~~~~~~~~~~~~~~
1. Explicitly registered provider (via :func:`set_provider`).
2. :class:`DeterministicPlanner` — always available, no external API required.

Output schema
-------------
``generate_test_plan`` always returns a JSON-serializable list of plan items::

    [
        {
            "title":             str,   # short imperative description of the test
            "reason":            str,   # why this case matters
            "inputs":            str,   # representative input description
            "expected_behavior": str,   # what the function should do
            "gap_type":          str,   # "exception" | "branch"
            "gap_ref":           str,   # the condition/exception string from the gap
        },
        ...
    ]
"""

from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from analyzer.code_analysis.function_extractor import extract_repository_functions
from analyzer.code_analysis.test_extractor import extract_repository_tests
from analyzer.gap_detection.repo_gap_analyzer import analyze_repository_gaps
from analyzer.test_generation.plan_builder import build_prompt_payload


# ---------------------------------------------------------------------------
# Provider protocol — the AI integration seam
# ---------------------------------------------------------------------------

@runtime_checkable
class PlanProvider(Protocol):
    """Protocol that any AI (or deterministic) plan provider must satisfy.

    Implement this interface and call :func:`set_provider` to replace the
    built-in deterministic fallback with a real model.
    """

    def plan(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate test-plan items from a prompt payload.

        Args:
            payload: The dict produced by
                :func:`~analyzer.test_generation.plan_builder.build_prompt_payload`.

        Returns:
            A list of plan-item dicts (see module docstring for the schema).
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_active_provider: PlanProvider | None = None


def set_provider(provider: PlanProvider) -> None:
    """Register *provider* as the active plan provider.

    Call this once at application startup before any analysis runs.
    The provider must satisfy the :class:`PlanProvider` protocol.

    Example (future AI integration)::

        from my_ai_module import WatsonxPlanner
        set_provider(WatsonxPlanner(api_key="..."))

    Args:
        provider: An object with a ``plan(payload) -> list[dict]`` method.

    Raises:
        TypeError: if *provider* does not satisfy :class:`PlanProvider`.
    """
    if not isinstance(provider, PlanProvider):
        raise TypeError(
            f"{provider!r} does not implement the PlanProvider protocol "
            "(requires a callable 'plan(payload)' method)."
        )
    global _active_provider
    _active_provider = provider


def get_provider() -> PlanProvider:
    """Return the active provider, falling back to :class:`DeterministicPlanner`."""
    return _active_provider if _active_provider is not None else DeterministicPlanner()


# ---------------------------------------------------------------------------
# Deterministic fallback planner
# ---------------------------------------------------------------------------

class DeterministicPlanner:
    """Rule-based test-plan generator — works with no external API.

    Produces one plan item per missing exception and one per missing branch,
    deriving human-readable descriptions from the gap strings and the function
    metadata present in the prompt payload.  No function-specific names are
    hard-coded; all text is derived from the payload at runtime.
    """

    # Regex to parse "ExcType: \"message\"" from missing_exceptions entries
    _EXC_RE = re.compile(r'^(\w+)(?:\s*:\s*"(.+)")?$')

    def plan(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Derive plan items from *payload* using deterministic rules.

        Args:
            payload: Dict produced by :func:`~analyzer.test_generation.plan_builder.build_prompt_payload`.

        Returns:
            List of plan-item dicts.
        """
        func_name: str = payload["function"]
        arguments: list[str] = payload["arguments"]
        missing_exceptions: list[str] = payload["missing_exceptions"]
        missing_branches: list[str] = payload["missing_branches"]

        plans: list[dict[str, Any]] = []

        for exc_str in missing_exceptions:
            plans.append(self._plan_exception(func_name, arguments, exc_str))

        for branch_cond in missing_branches:
            plans.append(self._plan_branch(func_name, arguments, branch_cond))

        return plans

    # ------------------------------------------------------------------
    # Per-gap item builders
    # ------------------------------------------------------------------

    def _plan_exception(
        self, func_name: str, arguments: list[str], exc_str: str
    ) -> dict[str, Any]:
        m = self._EXC_RE.match(exc_str)
        exc_type = m.group(1) if m else exc_str
        message = m.group(2) if (m and m.group(2)) else ""

        title = (
            f"Test that {func_name}() raises {exc_type}"
            + (f' when {self._condition_hint_from_message(message)}' if message else "")
        )
        reason = (
            f"The function raises {exc_type}"
            + (f' with message \"{message}\"' if message else "")
            + " but no existing test exercises this error path."
        )
        inputs = self._infer_inputs_for_exception(func_name, arguments, message)
        expected = (
            f"A {exc_type} is raised"
            + (f' with a message containing \"{message}\"' if message else "")
            + "."
        )
        return {
            "title":             title,
            "reason":            reason,
            "inputs":            inputs,
            "expected_behavior": expected,
            "gap_type":          "exception",
            "gap_ref":           exc_str,
        }

    def _plan_branch(
        self, func_name: str, arguments: list[str], condition: str
    ) -> dict[str, Any]:
        readable = self._humanise_condition(condition)
        title = f"Test {func_name}() when {readable}"
        reason = (
            f"The branch `{condition}` in {func_name}() is not exercised by "
            "any existing test."
        )
        inputs = self._infer_inputs_for_branch(func_name, arguments, condition)
        expected = self._infer_expected_for_branch(func_name, condition)
        return {
            "title":             title,
            "reason":            reason,
            "inputs":            inputs,
            "expected_behavior": expected,
            "gap_type":          "branch",
            "gap_ref":           condition,
        }

    # ------------------------------------------------------------------
    # Text-derivation helpers — all generic, no domain hard-coding
    # ------------------------------------------------------------------

    @staticmethod
    def _humanise_condition(condition: str) -> str:
        """Turn an AST-unparsed condition string into plain English.

        Examples::
            "price < 0"                       → "price is less than 0"
            "not items"                       → "items is empty / falsy"
            "coupon == 'SAVE20'"              → "coupon equals 'SAVE20'"
            "quantity <= 0"                   → "quantity is less than or equal to 0"
            "not 0 <= discount_percent <= 100"→ "discount_percent is outside 0 to 100"
        """
        s = condition.strip()

        # Special-case chained bounds like "not 0 <= x <= 100" before generic subs
        chained = re.match(
            r'^not\s+(-?[\d.]+)\s*<=\s*(\w+)\s*<=\s*(-?[\d.]+)$', s
        )
        if chained:
            lo, var, hi = chained.group(1), chained.group(2), chained.group(3)
            return f"{var} is outside {lo} to {hi}"

        # Replace comparison operators with words
        s = re.sub(r'\s*<=\s*', ' is less than or equal to ', s)
        s = re.sub(r'\s*>=\s*', ' is greater than or equal to ', s)
        s = re.sub(r'\s*<\s*', ' is less than ', s)
        s = re.sub(r'\s*>\s*', ' is greater than ', s)
        s = re.sub(r'\s*==\s*', ' equals ', s)
        s = re.sub(r'\s*!=\s*', ' does not equal ', s)
        s = re.sub(r'\bnot\s+(\w+)\b', r'\1 is empty / falsy', s)
        return s.strip()

    @staticmethod
    def _condition_hint_from_message(message: str) -> str:
        """Derive a short 'when ...' clause from an exception message string."""
        msg = message.lower()
        # Try to extract the most informative fragment after common patterns
        for prefix in ("cannot be ", "must be ", "is ", "are "):
            idx = msg.find(prefix)
            if idx != -1:
                return message[idx:].strip()
        return f"an invalid value is supplied ({message})"

    @staticmethod
    def _infer_inputs_for_exception(
        func_name: str, arguments: list[str], message: str
    ) -> str:
        """Build a generic inputs description for an exception plan item."""
        if not arguments:
            return "Call with arguments that trigger the invalid-input guard."
        msg_lower = message.lower()
        hints: list[str] = []
        for arg in arguments:
            arg_lower = arg.lower()
            # Match the argument name to the message text to give the most useful hint
            if arg_lower in msg_lower or any(
                word in msg_lower for word in _words_in(arg_lower)
            ):
                hints.append(f"{arg}=<value that violates the guard>")
            else:
                hints.append(f"{arg}=<valid value>")
        return f"{func_name}({', '.join(hints)})"

    @staticmethod
    def _infer_inputs_for_branch(
        func_name: str, arguments: list[str], condition: str
    ) -> str:
        """Build a generic inputs description for a branch plan item."""
        if not arguments:
            return "Call with arguments that satisfy the branch condition."
        hints: list[str] = []
        for arg in arguments:
            arg_lower = arg.lower()
            if arg_lower in condition.lower():
                # Extract the RHS from the original condition (preserves case)
                rhs_match = re.search(
                    rf'(?i){re.escape(arg_lower)}\s*==\s*([\'"][^\'"]+[\'"]|\S+)',
                    condition,
                )
                if rhs_match:
                    hints.append(f"{arg}={rhs_match.group(1)}")
                else:
                    hints.append(f"{arg}=<value satisfying `{condition}`>")
            else:
                hints.append(f"{arg}=<valid value>")
        return f"{func_name}({', '.join(hints)})"

    @staticmethod
    def _infer_expected_for_branch(func_name: str, condition: str) -> str:
        """Describe what should happen when the branch condition is met."""
        cond_lower = condition.lower()
        # If the condition looks like a guard that raises, say so
        if "not " in cond_lower or "< 0" in cond_lower or "<= 0" in cond_lower:
            return (
                "The function should raise an appropriate exception or return "
                "a defined sentinel value indicating the invalid state."
            )
        # String equality branches usually return a transformed value
        if "==" in cond_lower:
            return (
                f"{func_name}() should return the value associated with the "
                "matched condition branch."
            )
        return (
            f"{func_name}() should behave according to the logic defined "
            f"inside the `{condition}` branch."
        )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _words_in(text: str) -> list[str]:
    """Split *text* on non-alphanumeric characters and return non-empty tokens."""
    return [w for w in re.split(r'\W+', text) if w]


# ---------------------------------------------------------------------------
# Repository-level helper
# ---------------------------------------------------------------------------

def _build_index(
    all_functions: list[dict],
    all_tests: list[dict],
) -> dict[str, dict]:
    """Build a lookup from function name → {meta, covering_tests}.

    Used internally so :func:`generate_test_plan` can resolve covering tests
    without re-scanning.
    """
    # Index tests by the function names they call
    callers: dict[str, list[dict]] = {}
    for test in all_tests:
        for call in test.get("calls", []):
            callee: str = call["func"]
            # Strip attribute prefix (e.g. "obj.foo" → "foo")
            name = callee.rsplit(".", 1)[-1]
            callers.setdefault(name, [])
            if test not in callers[name]:
                callers[name].append(test)

    index: dict[str, dict] = {}
    for func in all_functions:
        fn = func["name"]
        index[fn] = {
            "meta":           func,
            "covering_tests": callers.get(fn, []),
        }
    return index


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_test_plan(
    repo_path: str,
    *,
    provider: PlanProvider | None = None,
) -> list[dict[str, Any]]:
    """Generate structured test-plan items for every gap found in *repo_path*.

    Orchestrates the full pipeline:

    1. Extract function metadata (reuses
       :func:`~analyzer.code_analysis.function_extractor.extract_repository_functions`).
    2. Extract test metadata (reuses
       :func:`~analyzer.code_analysis.test_extractor.extract_repository_tests`).
    3. Compute gap records (reuses
       :func:`~analyzer.gap_detection.repo_gap_analyzer.analyze_repository_gaps`).
    4. For each gap record, build a compact prompt payload via
       :func:`~analyzer.test_generation.plan_builder.build_prompt_payload`.
    5. Delegate planning to *provider* (or :func:`get_provider` if omitted).

    No files are reparsed — the extractors each read every file exactly once
    and the results are shared across all three steps above.

    AI integration
    ~~~~~~~~~~~~~~
    Pass a custom *provider* argument, or call :func:`set_provider` at startup,
    to route planning through an external model.  The deterministic fallback
    is used when neither is set.

    Args:
        repo_path: Absolute or relative path to the repository root.
        provider:  Optional one-shot provider override.  When supplied it is
                   used for this call only and does not affect the global registry.

    Returns:
        A JSON-serializable list of plan items grouped by function::

            [
                {
                    "function":   str,         # source function name
                    "source_file": str,        # absolute path to the source module
                    "gap_record": dict,        # the raw gap record from repo_gap_analyzer
                    "prompt_payload": dict,    # the compact payload sent to the planner
                    "plans": [                 # list of plan items from the provider
                        {
                            "title":             str,
                            "reason":            str,
                            "inputs":            str,
                            "expected_behavior": str,
                            "gap_type":          str,  # "exception" | "branch"
                            "gap_ref":           str,
                        },
                        ...
                    ],
                },
                ...
            ]
    """
    active = provider if provider is not None else get_provider()

    # -- Step 1-2: extract once, share everywhere -------------------------
    all_functions = extract_repository_functions(repo_path)
    all_tests = extract_repository_tests(repo_path)

    # -- Step 3: gap records ----------------------------------------------
    gap_records = analyze_repository_gaps(repo_path)

    # -- Step 4-5: build payloads and delegate ----------------------------
    func_index = _build_index(all_functions, all_tests)
    results: list[dict[str, Any]] = []

    for gap_record in gap_records:
        func_name = gap_record["function"]
        entry = func_index.get(func_name)
        if entry is None:
            continue  # gap references a function not in the index (shouldn't happen)

        payload = build_prompt_payload(
            function_meta=entry["meta"],
            covering_tests=entry["covering_tests"],
            gap_record=gap_record,
        )

        plans = active.plan(payload)

        results.append({
            "function":       func_name,
            "source_file":    gap_record["source_file"],
            "gap_record":     gap_record,
            "prompt_payload": payload,
            "plans":          plans,
        })

    return results
