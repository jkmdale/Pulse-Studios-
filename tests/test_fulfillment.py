import os
import sys

import pytest
import responses as responses_lib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import fulfillment

GELATO_URL = "https://order.gelatoapis.com/v4/orders"
SAMPLE_SHIPPING = {
    "address1": "123 Nursery Lane",
    "address2": "",
    "city": "Auckland",
    "zip": "1010",
    "country_code": "NZ",
}
SAMPLE_CUSTOMER = {
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah@example.com",
    "phone": "+64 21 000 0000",
}


class TestSubmitPrintOrder:
    @responses_lib.activate
    def test_success_returns_gelato_id(self, monkeypatch):
        monkeypatch.setenv("GELATO_API_KEY", "test-key")
        monkeypatch.setenv("GELATO_PRODUCT_UID", "poster-12x16-matte")

        responses_lib.add(
            responses_lib.POST,
            GELATO_URL,
            json={"id": "gelato-order-abc123"},
            status=201,
        )

        # Reload module to pick up monkeypatched env vars
        import importlib
        importlib.reload(fulfillment)

        result = fulfillment.submit_print_order(
            order_id="shopify-9001",
            pdf_url="https://s3.example.com/orders/9001/print.pdf?signed=yes",
            shipping=SAMPLE_SHIPPING,
            customer=SAMPLE_CUSTOMER,
        )
        assert result == "gelato-order-abc123"

    @responses_lib.activate
    def test_auth_failure_raises(self, monkeypatch):
        monkeypatch.setenv("GELATO_API_KEY", "bad-key")
        monkeypatch.setenv("GELATO_PRODUCT_UID", "poster-12x16-matte")

        responses_lib.add(
            responses_lib.POST,
            GELATO_URL,
            json={"message": "Unauthorized"},
            status=401,
        )

        import importlib
        importlib.reload(fulfillment)

        with pytest.raises(RuntimeError, match="Gelato API error 401"):
            fulfillment.submit_print_order(
                order_id="shopify-9002",
                pdf_url="https://s3.example.com/orders/9002/print.pdf",
                shipping=SAMPLE_SHIPPING,
                customer=SAMPLE_CUSTOMER,
            )

    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.setenv("GELATO_API_KEY", "")
        monkeypatch.setenv("GELATO_PRODUCT_UID", "poster-12x16-matte")

        import importlib
        importlib.reload(fulfillment)

        with pytest.raises(RuntimeError, match="GELATO_API_KEY"):
            fulfillment.submit_print_order(
                order_id="shopify-9003",
                pdf_url="https://s3.example.com/orders/9003/print.pdf",
                shipping=SAMPLE_SHIPPING,
                customer=SAMPLE_CUSTOMER,
            )

    def test_missing_product_uid_raises(self, monkeypatch):
        monkeypatch.setenv("GELATO_API_KEY", "test-key")
        monkeypatch.setenv("GELATO_PRODUCT_UID", "")

        import importlib
        importlib.reload(fulfillment)

        with pytest.raises(RuntimeError, match="GELATO_PRODUCT_UID"):
            fulfillment.submit_print_order(
                order_id="shopify-9004",
                pdf_url="https://s3.example.com/orders/9004/print.pdf",
                shipping=SAMPLE_SHIPPING,
                customer=SAMPLE_CUSTOMER,
            )
