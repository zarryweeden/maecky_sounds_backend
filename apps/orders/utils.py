from django.conf import settings


def calculate_shipping(cart_total: int, method: str) -> int:
    """
    Returns shipping cost in KES.
    Standard delivery is free over FREE_SHIPPING_MINIMUM.
    """
    free_threshold = getattr(settings, "FREE_SHIPPING_MINIMUM", 10000)

    if method == "pickup":
        return 0
    if method == "standard":
        return 0 if cart_total >= free_threshold else 500
    if method == "express":
        return 1500
    return 0


def get_estimated_delivery(method: str):
    """Return estimated delivery date based on delivery method."""
    from django.utils import timezone
    from datetime import timedelta

    today = timezone.now().date()
    days_map = {
        "standard": 6,   # mid-point of 5–7
        "express": 2,
        "pickup": 0,
    }
    days = days_map.get(method, 6)
    return today + timedelta(days=days)


def build_shipping_address_snapshot(address_data: dict) -> dict:
    """Normalise and snapshot a shipping address."""
    return {
        "full_name": address_data.get("full_name", ""),
        "phone": address_data.get("phone", ""),
        "address_line1": address_data.get("address_line1", ""),
        "address_line2": address_data.get("address_line2", ""),
        "city": address_data.get("city", ""),
        "county": address_data.get("county", ""),
        "postal_code": address_data.get("postal_code", ""),
    }