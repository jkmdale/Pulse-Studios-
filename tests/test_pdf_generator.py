import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from pdf_generator import generate


SAMPLE_PEAKS = [abs(0.5 * (i % 10) / 10) for i in range(500)]
SAMPLE_CUSTOMER = {
    "name": "Sarah Johnson",
    "baby_name": "Baby Emma",
    "due_date": "March 2025",
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah@example.com",
    "phone": "+64 21 000 0000",
}


class TestPdfGenerator:
    def test_pdf_created(self, tmp_path):
        output = str(tmp_path / "print.pdf")
        generate(
            order_id="test-001",
            peaks=SAMPLE_PEAKS,
            bpm=142.5,
            customer_info=SAMPLE_CUSTOMER,
            output_pdf_path=output,
            base_url="https://pulseheirloom.com",
        )
        assert os.path.exists(output)

    def test_pdf_minimum_size(self, tmp_path):
        output = str(tmp_path / "print.pdf")
        generate(
            order_id="test-002",
            peaks=SAMPLE_PEAKS,
            bpm=138.0,
            customer_info=SAMPLE_CUSTOMER,
            output_pdf_path=output,
            base_url="https://pulseheirloom.com",
        )
        size = os.path.getsize(output)
        assert size > 50_000, f"PDF too small ({size} bytes) — may be incomplete"

    def test_pdf_contains_order_id_url(self, tmp_path):
        order_id = "unique-order-xyz"
        output = str(tmp_path / "print.pdf")
        generate(
            order_id=order_id,
            peaks=SAMPLE_PEAKS,
            bpm=150.0,
            customer_info=SAMPLE_CUSTOMER,
            output_pdf_path=output,
            base_url="https://pulseheirloom.com",
        )
        with open(output, "rb") as f:
            content = f.read()
        assert order_id.encode() in content

    def test_empty_peaks_handled(self, tmp_path):
        output = str(tmp_path / "empty_peaks.pdf")
        generate(
            order_id="test-003",
            peaks=[],
            bpm=135.0,
            customer_info=SAMPLE_CUSTOMER,
            output_pdf_path=output,
            base_url="https://pulseheirloom.com",
        )
        assert os.path.exists(output)

    def test_missing_optional_customer_fields(self, tmp_path):
        output = str(tmp_path / "minimal.pdf")
        generate(
            order_id="test-004",
            peaks=SAMPLE_PEAKS[:100],
            bpm=148.0,
            customer_info={"name": "Test Parent", "email": "test@test.com"},
            output_pdf_path=output,
            base_url="https://pulseheirloom.com",
        )
        assert os.path.exists(output)
