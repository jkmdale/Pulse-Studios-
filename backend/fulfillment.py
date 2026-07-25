import os

import requests
from dotenv import load_dotenv

load_dotenv()

# Correct Gelato v4 endpoint (requirements doc had an outdated URL)
GELATO_API_URL = "https://order.gelatoapis.com/v4/orders"
GELATO_API_KEY = os.getenv("GELATO_API_KEY", "")
GELATO_PRODUCT_UID = os.getenv("GELATO_PRODUCT_UID", "")


def submit_print_order(order_id: str, pdf_url: str, shipping: dict, customer: dict) -> str:
    """
    Submit a print order to Gelato.

    pdf_url must be a publicly reachable URL (use 7-day presigned S3 URL).
    Returns the Gelato order ID string.
    """
    if not GELATO_API_KEY:
        raise RuntimeError("GELATO_API_KEY is not set")
    if not GELATO_PRODUCT_UID:
        raise RuntimeError("GELATO_PRODUCT_UID is not set — configure the product in your Gelato dashboard first")

    payload = {
        "orderReferenceId": order_id,
        "customerReferenceId": order_id,
        "currency": "NZD",
        "items": [
            {
                "itemReferenceId": f"{order_id}-item-1",
                "productUid": GELATO_PRODUCT_UID,
                "files": [
                    {"type": "default", "url": pdf_url}
                ],
                "quantity": 1,
            }
        ],
        "shippingAddress": {
            "firstName": customer.get("first_name", ""),
            "lastName": customer.get("last_name", ""),
            "addressLine1": shipping.get("address1", ""),
            "addressLine2": shipping.get("address2", ""),
            "city": shipping.get("city", ""),
            "postCode": shipping.get("zip", ""),
            "country": shipping.get("country_code", "NZ"),
            "email": customer.get("email", ""),
            "phone": customer.get("phone", ""),
        },
    }

    headers = {
        "X-API-KEY": GELATO_API_KEY,
        "Content-Type": "application/json",
    }

    response = requests.post(GELATO_API_URL, json=payload, headers=headers, timeout=30)

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(
            f"Gelato API error {response.status_code}: {response.text}"
        ) from e

    return response.json()["id"]


def get_order_status(gelato_order_id: str) -> dict:
    """Fetch current Gelato order status."""
    headers = {"X-API-KEY": GELATO_API_KEY}
    response = requests.get(
        f"{GELATO_API_URL}/{gelato_order_id}",
        headers=headers,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()
