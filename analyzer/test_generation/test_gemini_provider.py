"""Tests for the Gemini plan provider.

Two cases validated:
1. No credentials configured  → generate_test_plan falls back to DeterministicPlanner.
2. Credentials configured     → GeminiPlanner is selected; valid plan output passes
                                schema validation.

The Gemini API is always mocked — no network calls are made.
"""

from __future__ import annotations

import json
import os
import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure the project root is importable when running directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analyzer.test_generation.gemini_provider import (
    GeminiPlanner,
    _validate_plan_items,
    make_provider,
)
from analyzer.test_generation.planner import (
    DeterministicPlanner,
    generate_test_plan,
    get_provider,
)

# ---------------------------------------------------------------------------
# Minimal plan-item fixture
# ---------------------------------------------------------------------------

_VALID_ITEM: dict[str, Any] = {
    "title": "Test that calculate_discount() raises ValueError when the price is negative",
    "reason": "The function raises ValueError but no test exercises this path.",
    "inputs": "calculate_discount(price=-5.0, discount_percent=10)",
    "expected_behavior": "A ValueError is raised.",
    "gap_type": "exception",
    "gap_ref": 'ValueError: "Price cannot be negative"',
}

_MINIMAL_PAYLOAD: dict[str, Any] = {
    "function": "calculate_discount",
    "source_file": "sample_repo/src/cart.py",
    "arguments": ["price", "discount_percent"],
    "branches": ["price < 0"],
    "raises": ['ValueError: "Price cannot be negative"'],
    "covering_tests": ["test_calculate_discount_basic"],
    "missing_branches": [],
    "missing_exceptions": ['ValueError: "Price cannot be negative"'],
    "confidence": "high",
    "existing_literals": [100.0, 10],
    "task": "You are a test-plan generator …",
}


# ---------------------------------------------------------------------------
# _validate_plan_items unit tests
# ---------------------------------------------------------------------------

class TestValidatePlanItems:
    def test_accepts_valid_item(self):
        result = _validate_plan_items([_VALID_ITEM.copy()])
        assert len(result) == 1
        assert result[0]["gap_type"] == "exception"

    def test_strips_whitespace(self):
        item = {k: f"  {v}  " for k, v in _VALID_ITEM.items()}
        result = _validate_plan_items([item])
        for key, val in result[0].items():
            assert val == val.strip()

    def test_rejects_empty_list(self):
        with pytest.raises(ValueError, match="non-empty"):
            _validate_plan_items([])

    def test_rejects_non_list(self):
        with pytest.raises(ValueError):
            _validate_plan_items({"title": "x"})

    def test_rejects_missing_key(self):
        bad = {k: v for k, v in _VALID_ITEM.items() if k != "gap_ref"}
        with pytest.raises(ValueError, match="gap_ref"):
            _validate_plan_items([bad])

    def test_rejects_non_string_value(self):
        bad = {**_VALID_ITEM, "gap_type": 42}
        with pytest.raises(ValueError, match="gap_type"):
            _validate_plan_items([bad])

    def test_accepts_multiple_items(self):
        items = [_VALID_ITEM.copy(), {**_VALID_ITEM, "gap_type": "branch"}]
        result = _validate_plan_items(items)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# make_provider unit tests
# ---------------------------------------------------------------------------

class TestMakeProvider:
    def test_returns_none_when_key_absent(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert make_provider() is None

    def test_returns_none_when_key_empty(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "   ")
        assert make_provider() is None

    def test_returns_gemini_planner_when_key_set(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-abc")
        provider = make_provider()
        assert isinstance(provider, GeminiPlanner)

    def test_uses_default_model(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-abc")
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        provider = make_provider()
        assert provider._model == "gemini-3.8-flash"

    def test_uses_custom_model(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key-abc")
        monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-pro")
        provider = make_provider()
        assert provider._model == "gemini-1.5-pro"


# ---------------------------------------------------------------------------
# Case 1 — no credentials configured
# ---------------------------------------------------------------------------

class TestNoCredentials:
    """generate_test_plan must succeed using DeterministicPlanner when GEMINI_API_KEY is unset."""

    def test_get_provider_returns_deterministic(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        # Also clear the global registry for this test
        import analyzer.test_generation.planner as planner_mod
        original = planner_mod._active_provider
        planner_mod._active_provider = None
        try:
            provider = get_provider()
            assert isinstance(provider, DeterministicPlanner)
        finally:
            planner_mod._active_provider = original

    def test_generate_test_plan_succeeds_without_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        import analyzer.test_generation.planner as planner_mod
        original = planner_mod._active_provider
        planner_mod._active_provider = None
        try:
            results = generate_test_plan("sample_repo")
            assert isinstance(results, list)
            assert len(results) > 0
            # Every entry must have the required structure
            for entry in results:
                assert "function" in entry
                assert "plans" in entry
                for plan in entry["plans"]:
                    for key in ("title", "reason", "inputs", "expected_behavior", "gap_type", "gap_ref"):
                        assert key in plan, f"Missing key '{key}' in plan: {plan}"
        finally:
            planner_mod._active_provider = original


# ---------------------------------------------------------------------------
# Case 2 — credentials configured
# ---------------------------------------------------------------------------

def _make_mock_response(items: list[dict]) -> MagicMock:
    """Build a mock Gemini response object whose .text is a JSON array."""
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(items)
    return mock_resp


def _build_mock_genai(response_items: list[dict]) -> types.ModuleType:
    """Return a minimal mock of ``google.genai`` that returns *response_items*."""
    mock_genai = MagicMock()
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_client.models.generate_content.return_value = _make_mock_response(response_items)
    # types namespace used by GeminiPlanner._call_gemini
    mock_genai.types = MagicMock()
    mock_genai.types.GenerateContentConfig = MagicMock(return_value=MagicMock())
    mock_genai.types.HttpOptions = MagicMock(return_value=MagicMock())
    return mock_genai


class TestGeminiProviderSelected:
    """When GEMINI_API_KEY is present, GeminiPlanner is selected and plan output is valid."""

    def _patched_planner(self, monkeypatch) -> GeminiPlanner:
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
        monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
        return GeminiPlanner(api_key="fake-key-for-test", model="gemini-3.8-flash")

    def test_get_provider_returns_gemini_planner(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
        import analyzer.test_generation.planner as planner_mod
        original = planner_mod._active_provider
        planner_mod._active_provider = None
        try:
            provider = get_provider()
            assert isinstance(provider, GeminiPlanner)
        finally:
            planner_mod._active_provider = original

    def test_plan_returns_validated_items(self, monkeypatch):
        """GeminiPlanner.plan() returns validated items when Gemini responds correctly."""
        planner = self._patched_planner(monkeypatch)
        mock_genai = _build_mock_genai([_VALID_ITEM])

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = planner.plan(_MINIMAL_PAYLOAD)

        assert len(result) == 1
        item = result[0]
        for key in ("title", "reason", "inputs", "expected_behavior", "gap_type", "gap_ref"):
            assert key in item
            assert isinstance(item[key], str)

    def test_plan_items_pass_schema_validation(self, monkeypatch):
        """Each returned item must contain all six required keys with string values."""
        planner = self._patched_planner(monkeypatch)
        mock_genai = _build_mock_genai([_VALID_ITEM])

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = planner.plan(_MINIMAL_PAYLOAD)

        validated = _validate_plan_items(result)
        assert validated == result

    def test_plan_falls_back_on_api_error(self, monkeypatch):
        """plan() falls back to DeterministicPlanner when the Gemini SDK raises."""
        planner = self._patched_planner(monkeypatch)
        mock_genai = MagicMock()
        mock_genai.Client.return_value.models.generate_content.side_effect = RuntimeError("API down")
        mock_genai.types = MagicMock()

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = planner.plan(_MINIMAL_PAYLOAD)

        # Fallback should produce at least one item for the missing exception
        assert len(result) >= 1
        for item in result:
            assert "gap_type" in item

    def test_plan_falls_back_on_invalid_json(self, monkeypatch):
        """plan() falls back when Gemini returns non-JSON text."""
        planner = self._patched_planner(monkeypatch)
        mock_genai = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "Here are your test plans: ..."  # invalid JSON
        mock_genai.Client.return_value.models.generate_content.return_value = mock_resp
        mock_genai.types = MagicMock()

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = planner.plan(_MINIMAL_PAYLOAD)

        assert len(result) >= 1

    def test_plan_falls_back_on_schema_violation(self, monkeypatch):
        """plan() falls back when Gemini returns JSON that fails schema validation."""
        planner = self._patched_planner(monkeypatch)
        bad_items = [{"title": "Only title, nothing else"}]
        mock_genai = _build_mock_genai(bad_items)

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = planner.plan(_MINIMAL_PAYLOAD)

        # Fallback items must be valid
        assert len(result) >= 1
        _validate_plan_items(result)  # should not raise


# ---------------------------------------------------------------------------
# Structured output example test
# ---------------------------------------------------------------------------

class TestStructuredGeminiOutput:
    """Verify the exact shape of a realistic multi-item Gemini response."""

    _MULTI_ITEM_RESPONSE = [
        {
            "title": "Test that calculate_discount() raises ValueError when the price is negative",
            "reason": "The function raises ValueError with message \"Price cannot be negative\" but no existing test exercises this error path.",
            "inputs": "calculate_discount(price=-1.0, discount_percent=<valid value>)",
            "expected_behavior": "A ValueError is raised with a message containing \"Price cannot be negative\".",
            "gap_type": "exception",
            "gap_ref": "ValueError: \"Price cannot be negative\"",
        },
        {
            "title": "Test that calculate_discount() raises ValueError when the discount_percent is outside 0 to 100",
            "reason": "The function raises ValueError with message \"Discount must be between 0-100\" but no existing test exercises this error path.",
            "inputs": "calculate_discount(price=<valid value>, discount_percent=150)",
            "expected_behavior": "A ValueError is raised with a message containing \"Discount must be between 0-100\".",
            "gap_type": "exception",
            "gap_ref": "ValueError: \"Discount must be between 0-100\"",
        },
    ]

    def test_multi_item_response_passes_schema(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
        planner = GeminiPlanner(api_key="fake-key-for-test")
        mock_genai = _build_mock_genai(self._MULTI_ITEM_RESPONSE)

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}):
            result = planner.plan(_MINIMAL_PAYLOAD)

        assert len(result) == 2
        validated = _validate_plan_items(result)
        assert len(validated) == 2
        assert validated[0]["gap_type"] == "exception"
        assert validated[1]["gap_ref"] == "ValueError: \"Discount must be between 0-100\""
