"""Tests for cart.py — intentionally incomplete (happy-path only)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cart import calculate_discount, apply_coupon, checkout


def test_calculate_discount_basic():
    assert calculate_discount(100.0, 10) == 90.0


def test_apply_coupon_save10():
    assert apply_coupon(100.0, "SAVE10") == 90.0


def test_checkout_single_item():
    items = [{"price": 50.0, "quantity": 2}]
    result = checkout(items)
    assert result["total"] == 100.0
    assert result["item_count"] == 1
    assert result["status"] == "ok"


def test_checkout_multiple_items():
    items = [
        {"price": 20.0, "quantity": 1},
        {"price": 10.0, "quantity": 3},
    ]
    result = checkout(items)
    assert result["total"] == 50.0
    assert result["item_count"] == 2
