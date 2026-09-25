"""Simple shopping cart with discount and checkout logic."""


def calculate_discount(price: float, discount_percent: float) -> float:
    """Return the discounted price.

    Raises:
        ValueError: if price is negative or discount is outside 0-100.
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
    if not (0 <= discount_percent <= 100):
        raise ValueError("Discount must be between 0 and 100")
    return price * (1 - discount_percent / 100)


def apply_coupon(total: float, coupon: str) -> float:
    """Apply a coupon code and return the adjusted total.

    Supported coupons:
        SAVE10  – 10% off
        SAVE20  – 20% off
        FREESHIP – no effect on price (shipping handled elsewhere)

    Unknown coupons are silently ignored.
    """
    if coupon == "SAVE10":
        return total * 0.90
    if coupon == "SAVE20":
        return total * 0.80
    if coupon == "FREESHIP":
        return total
    # Unknown coupon — no discount applied
    return total


def checkout(items: list[dict]) -> dict:
    """Calculate the order total from a list of cart items.

    Each item must be a dict with 'price' (float) and 'quantity' (int).
    An optional 'discount_percent' key applies a per-item discount.

    Returns a dict with 'item_count', 'total', and 'status'.

    Raises:
        ValueError: if items is empty or any item has a non-positive quantity.
    """
    if not items:
        raise ValueError("Cart is empty")

    total = 0.0
    for item in items:
        quantity = item.get("quantity", 1)
        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        price = item["price"]
        discount = item.get("discount_percent", 0)
        total += calculate_discount(price, discount) * quantity

    return {
        "item_count": len(items),
        "total": round(total, 2),
        "status": "ok",
    }
