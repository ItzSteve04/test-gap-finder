"""Gemini AI plan provider.

Implements :class:`~analyzer.test_generation.planner.PlanProvider` using the
Google Gemini Developer API (``google-genai`` SDK).

Configuration
-------------
Read exclusively from environment variables — no secrets in source:

``GEMINI_API_KEY``
    Required.  Your Gemini Developer API key.
``GEMINI_MODEL``
    Optional.  Model name to use (default: ``gemini-3.8-flash``).

Provider selection
------------------
Call :func:`make_provider` at startup.  It returns a :class:`GeminiPlanner`
when ``GEMINI_API_KEY`` is set; otherwise it returns ``None`` so the caller
can fall through to :class:`~analyzer.test_generation.planner.DeterministicPlanner`.

Fallback
--------
:class:`GeminiPlanner` falls back to
:class:`~analyzer.test_generation.planner.DeterministicPlanner` internally on
any of: missing API key, import error, timeout, API error, invalid JSON, or
schema validation failure.  The caller never needs to handle these cases.

Isolation
---------
This module is the *only* place that imports ``google.genai``.  The rest of
the analyzer has no direct dependency on the Gemini SDK.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from analyzer.test_generation.planner import DeterministicPlanner, PlanProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MODEL = "gemini-3.8-flash"
_REQUEST_TIMEOUT = 30  # seconds

# Required keys that every returned plan item must contain
_REQUIRED_KEYS = frozenset(
    {"title", "reason", "inputs", "expected_behavior", "gap_type", "gap_ref"}
)

_SYSTEM_PROMPT = (
    "You are a test-plan generator for a software quality tool. "
    "You will receive a JSON object describing a Python function and the gaps "
    "in its test coverage. "
    "Respond with a JSON array only — no markdown fences, no prose, no keys "
    "outside the array. "
    "Each element of the array must be a JSON object with exactly these keys: "
    '"title" (string), "reason" (string), "inputs" (string), '
    '"expected_behavior" (string), "gap_type" (string, one of "exception" or "branch"), '
    '"gap_ref" (string). '
    "Produce one element per entry in missing_exceptions plus one per entry in "
    "missing_branches that is not already covered by a missing_exception. "
    "Do not include any other text in your response."
)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def _validate_plan_items(raw: Any) -> list[dict[str, Any]]:
    """Validate and sanitize Gemini output.

    Args:
        raw: The parsed JSON value returned by Gemini.

    Returns:
        A list of sanitized plan-item dicts.

    Raises:
        ValueError: If *raw* is not a non-empty list, or any item is missing a
                    required key, or any value is not a string.
    """
    if not isinstance(raw, list) or len(raw) == 0:
        raise ValueError(f"Expected a non-empty JSON array, got: {type(raw).__name__}")

    validated: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx} is not a JSON object: {item!r}")
        missing = _REQUIRED_KEYS - item.keys()
        if missing:
            raise ValueError(f"Item {idx} is missing required keys: {missing}")
        sanitized: dict[str, Any] = {}
        for key in _REQUIRED_KEYS:
            val = item[key]
            if not isinstance(val, str):
                raise ValueError(
                    f"Item {idx} key '{key}' must be a string, got {type(val).__name__}"
                )
            sanitized[key] = val.strip()
        validated.append(sanitized)

    return validated


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class GeminiPlanner:
    """PlanProvider that delegates to the Google Gemini API.

    Falls back to :class:`~analyzer.test_generation.planner.DeterministicPlanner`
    on any error so the caller always receives a valid plan.

    Args:
        api_key: Gemini Developer API key.
        model:   Gemini model name (default: ``gemini-3.8-flash``).
    """

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._api_key = api_key
        self._model = model
        self._fallback = DeterministicPlanner()

    # ------------------------------------------------------------------
    # PlanProvider protocol
    # ------------------------------------------------------------------

    def plan(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate plan items via Gemini, falling back to deterministic rules.

        Args:
            payload: The compact prompt payload produced by
                :func:`~analyzer.test_generation.plan_builder.build_prompt_payload`.

        Returns:
            A validated list of plan-item dicts.  Always non-empty unless the
            function has no coverage gaps at all.
        """
        try:
            return self._call_gemini(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "GeminiPlanner: falling back to DeterministicPlanner due to: %s: %s",
                type(exc).__name__,
                exc,
            )
            return self._fallback.plan(payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_gemini(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Send *payload* to Gemini and return validated plan items.

        Raises:
            Any exception from the SDK, JSON parsing, or schema validation.
        """
        from google import genai  # isolated import — only here

        client = genai.Client(api_key=self._api_key)

        user_message = json.dumps(payload, ensure_ascii=False)

        response = client.models.generate_content(
            model=self._model,
            contents=user_message,
            config=genai.types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.2,
                response_mime_type="application/json",
                http_options=genai.types.HttpOptions(timeout=_REQUEST_TIMEOUT * 1000),
            ),
        )

        raw_text: str = response.text.strip()
        parsed = json.loads(raw_text)
        return _validate_plan_items(parsed)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_provider() -> GeminiPlanner | None:
    """Return a :class:`GeminiPlanner` if ``GEMINI_API_KEY`` is set, else ``None``.

    Call this once at application startup and pass the result to
    :func:`~analyzer.test_generation.planner.set_provider` when it is not ``None``.

    Example::

        from analyzer.test_generation.gemini_provider import make_provider
        from analyzer.test_generation.planner import set_provider

        provider = make_provider()
        if provider is not None:
            set_provider(provider)

    Returns:
        A configured :class:`GeminiPlanner`, or ``None`` when the key is absent.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    logger.info("Using GeminiPlanner (model=%s)", model)
    return GeminiPlanner(api_key=api_key, model=model)
