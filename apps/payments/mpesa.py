"""
Safaricom Daraja API client.
Handles M-Pesa STK Push (Lipa na M-Pesa Online) payment flow.

Environment variables required:
    MPESA_CONSUMER_KEY
    MPESA_CONSUMER_SECRET
    MPESA_SHORTCODE
    MPESA_PASSKEY
    MPESA_ENVIRONMENT  (sandbox | production)
    MPESA_CALLBACK_URL
"""

import base64
import logging
import re
from datetime import datetime

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE = "https://api.safaricom.co.ke"


def _base_url():
    env = getattr(settings, "MPESA_ENVIRONMENT", "sandbox")
    return SANDBOX_BASE if env == "sandbox" else PRODUCTION_BASE


def get_access_token():
    """
    Fetch a short-lived OAuth access token from Safaricom.
    Token is valid for 3600 seconds.
    """
    consumer_key = settings.MPESA_CONSUMER_KEY
    consumer_secret = settings.MPESA_CONSUMER_SECRET

    if not consumer_key or not consumer_secret:
        raise ValueError("MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET must be set.")

    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(
            url,
            auth=(consumer_key, consumer_secret),
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise ValueError(f"No access_token in Daraja response: {data}")
        return token
    except requests.RequestException as e:
        logger.error(f"M-Pesa get_access_token failed: {e}")
        raise


def _generate_password(timestamp):
    """
    Generate the Lipa na M-Pesa Online password.
    Formula: Base64(Shortcode + Passkey + Timestamp)
    """
    shortcode = settings.MPESA_SHORTCODE
    passkey = settings.MPESA_PASSKEY
    raw = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw.encode()).decode()


def format_phone(phone: str) -> str:
    """
    Normalise Kenyan phone numbers to 254XXXXXXXXX format
    required by the Daraja API.

    Accepts:
        07XXXXXXXX  → 2547XXXXXXXX
        +2547XXXXXXXX → 2547XXXXXXXX
        2547XXXXXXXX → 2547XXXXXXXX
    """
    cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)

    if cleaned.startswith("0") and len(cleaned) == 10:
        return "254" + cleaned[1:]
    if cleaned.startswith("254") and len(cleaned) == 12:
        return cleaned
    if cleaned.startswith("7") and len(cleaned) == 9:
        return "254" + cleaned
    if cleaned.startswith("1") and len(cleaned) == 9:
        return "254" + cleaned

    raise ValueError(
        f"Cannot format phone number '{phone}' to Safaricom format. "
        "Please provide a valid Kenyan number."
    )


def initiate_stk_push(phone: str, amount: int, order_number: str) -> dict:
    """
    Initiate an M-Pesa STK Push to the customer's phone.

    Returns the raw Daraja API response dict which includes:
        CheckoutRequestID — use this to poll status or match callback
        MerchantRequestID
        ResponseCode       — "0" = success
        CustomerMessage
    """
    token = get_access_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = _generate_password(timestamp)
    formatted_phone = format_phone(phone)

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": formatted_phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": formatted_phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": order_number,
        "TransactionDesc": f"Payment for Maecky Sounds Order {order_number}",
    }

    url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        logger.info(f"STK Push initiated for order {order_number}: {data}")
        return data
    except requests.RequestException as e:
        logger.error(f"STK Push failed for order {order_number}: {e}")
        raise


def query_stk_push(checkout_request_id: str) -> dict:
    """
    Query the status of a pending STK push transaction.
    Useful for polling when the callback hasn't arrived yet.
    """
    token = get_access_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = _generate_password(timestamp)

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    url = f"{_base_url()}/mpesa/stkpushquery/v1/query"

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"STK Push query failed for {checkout_request_id}: {e}")
        raise


def verify_callback(data: dict) -> bool:
    """
    Basic validation of an incoming M-Pesa callback.
    Checks that required fields are present and result code is valid.

    Note: In production, also validate the source IP is from Safaricom's
    known IP ranges for additional security.
    """
    try:
        stk_callback = data["Body"]["stkCallback"]
        required_fields = ["MerchantRequestID", "CheckoutRequestID", "ResultCode"]
        for field in required_fields:
            if field not in stk_callback:
                logger.warning(f"M-Pesa callback missing field: {field}")
                return False
        return True
    except (KeyError, TypeError) as e:
        logger.warning(f"M-Pesa callback validation failed: {e}")
        return False


def parse_successful_callback(data: dict) -> dict:
    """
    Extract useful fields from a successful M-Pesa STK callback.

    Returns:
        {
            "checkout_request_id": str,
            "merchant_request_id": str,
            "result_code": int,
            "amount": float,
            "receipt": str,        # M-Pesa transaction ID e.g. "NLJ7RT61SV"
            "phone": str,
            "transaction_date": str,
        }
    """
    stk = data["Body"]["stkCallback"]
    result = {
        "checkout_request_id": stk.get("CheckoutRequestID", ""),
        "merchant_request_id": stk.get("MerchantRequestID", ""),
        "result_code": int(stk.get("ResultCode", -1)),
        "result_desc": stk.get("ResultDesc", ""),
        "amount": None,
        "receipt": "",
        "phone": "",
        "transaction_date": "",
    }

    if result["result_code"] == 0:
        # Payment successful — extract metadata items
        items = stk.get("CallbackMetadata", {}).get("Item", [])
        meta = {item["Name"]: item.get("Value") for item in items}
        result["amount"] = meta.get("Amount")
        result["receipt"] = meta.get("MpesaReceiptNumber", "")
        result["phone"] = str(meta.get("PhoneNumber", ""))
        result["transaction_date"] = str(meta.get("TransactionDate", ""))

    return result