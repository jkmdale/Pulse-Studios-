import io
import os
import tempfile
from pathlib import Path
from typing import Optional

import qrcode
from PIL import Image
from reportlab.lib.colors import CMYKColor, HexColor
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# Brand palette in CMYK (never RGB for print)
CREAM = CMYKColor(0.00, 0.02, 0.08, 0.02)
BLUSH = CMYKColor(0.00, 0.25, 0.15, 0.05)
NAVY = CMYKColor(0.80, 0.55, 0.00, 0.40)
GOLD = CMYKColor(0.00, 0.15, 0.70, 0.05)

# Print dimensions (12" × 16" at 72pt/inch)
PAGE_W = 12 * inch
PAGE_H = 16 * inch
BLEED = 0.125 * inch


def _register_fonts() -> str:
    """Register Lato fonts for PDF embedding. Falls back to Helvetica if missing."""
    lato_regular = os.path.join(FONTS_DIR, "Lato-Regular.ttf")
    lato_light = os.path.join(FONTS_DIR, "Lato-Light.ttf")

    if os.path.exists(lato_regular) and os.path.exists(lato_light):
        pdfmetrics.registerFont(TTFont("Lato", lato_regular))
        pdfmetrics.registerFont(TTFont("Lato-Light", lato_light))
        return "Lato"
    # Helvetica is not embedded by default — warn, use as fallback during dev only
    return "Helvetica"


def _draw_waveform(c: canvas.Canvas, peaks: list, x_start: float, y_center: float,
                   width: float, max_height: float) -> None:
    """Draw a filled waveform shape from amplitude peaks using a closed path."""
    n = len(peaks)
    if n < 2:
        return

    path = c.beginPath()
    # Top half
    for i, amp in enumerate(peaks):
        x = x_start + (i / (n - 1)) * width
        y = y_center + amp * max_height
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    # Bottom half (mirror, reversed)
    for i, amp in enumerate(reversed(peaks)):
        x = x_start + ((n - 1 - i) / (n - 1)) * width
        y = y_center - amp * max_height
        path.lineTo(x, y)
    path.close()

    c.setFillColor(BLUSH)
    c.setStrokeColor(BLUSH)
    c.drawPath(path, fill=1, stroke=0)


def _make_qr_image(url: str, tmp_dir: str, order_id: str) -> str:
    """Generate QR code PNG, return local path."""
    qr = qrcode.QRCode(box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    qr_path = os.path.join(tmp_dir, f"{order_id}_qr.png")
    img.save(qr_path)
    return qr_path


def generate(order_id: str, peaks: list, bpm: float, customer_info: dict,
             output_pdf_path: str, base_url: str = None) -> None:
    """
    Render a print-ready 12"×16" CMYK PDF.

    customer_info keys: name, baby_name (optional), due_date (optional)
    """
    if base_url is None:
        base_url = os.getenv("BASE_URL", "https://pulseheirloom.com")

    font_name = _register_fonts()
    haptic_url = f"{base_url}/listen/{order_id}"

    tmp_dir = tempfile.gettempdir()
    qr_path = _make_qr_image(haptic_url, tmp_dir, order_id)

    c = canvas.Canvas(output_pdf_path, pagesize=(PAGE_W + 2 * BLEED, PAGE_H + 2 * BLEED))
    c.setPageCompression(0)  # lossless for print

    # --- Background ---
    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W + 2 * BLEED, PAGE_H + 2 * BLEED, fill=1, stroke=0)

    # Offset all content by bleed margin
    ox, oy = BLEED, BLEED

    # --- Header: customer / baby name ---
    baby_name = customer_info.get("baby_name") or customer_info.get("name", "")
    c.setFillColor(NAVY)
    c.setFont(font_name, 28)
    header = f"{baby_name}'s Heartbeat" if baby_name else "Your Baby's Heartbeat"
    c.drawCentredString(ox + PAGE_W / 2, oy + PAGE_H - 1.2 * inch, header)

    # --- Due / birth date subtitle ---
    due_date = customer_info.get("due_date", "")
    if due_date:
        c.setFont(font_name + "-Light" if font_name == "Lato" else font_name, 16)
        c.setFillColor(NAVY)
        c.drawCentredString(ox + PAGE_W / 2, oy + PAGE_H - 1.75 * inch, due_date)

    # --- Decorative top rule ---
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(ox + 1 * inch, oy + PAGE_H - 2.1 * inch, ox + PAGE_W - 1 * inch, oy + PAGE_H - 2.1 * inch)

    # --- Waveform art (center of page) ---
    waveform_x = ox + 0.75 * inch
    waveform_w = PAGE_W - 1.5 * inch
    waveform_y = oy + PAGE_H / 2
    waveform_h = 2.8 * inch
    _draw_waveform(c, peaks, waveform_x, waveform_y, waveform_w, waveform_h)

    # --- BPM display ---
    c.setFont(font_name, 20)
    c.setFillColor(NAVY)
    bpm_text = f"{int(round(bpm))} BPM"
    c.drawCentredString(ox + PAGE_W / 2, oy + PAGE_H / 2 - waveform_h - 0.5 * inch, bpm_text)

    # --- Decorative bottom rule ---
    c.setStrokeColor(GOLD)
    c.line(ox + 1 * inch, oy + 2.2 * inch, ox + PAGE_W - 1 * inch, oy + 2.2 * inch)

    # --- QR code (bottom-right) ---
    qr_size = 1.5 * inch
    qr_x = ox + PAGE_W - qr_size - 0.6 * inch
    qr_y = oy + 0.5 * inch
    c.drawImage(qr_path, qr_x, qr_y, width=qr_size, height=qr_size, mask="auto")

    # --- QR caption ---
    c.setFont(font_name, 8)
    c.setFillColor(NAVY)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 0.18 * inch, "Scan to feel the heartbeat")

    # --- Customer name footer (bottom-left) ---
    parent_name = customer_info.get("name", "")
    if parent_name:
        c.setFont(font_name, 10)
        c.setFillColor(NAVY)
        c.drawString(ox + 0.6 * inch, oy + 0.65 * inch, f"A gift for {parent_name}")

    c.save()
