"""Isolated document fixtures, including the actual ClamAV binary and OCR inputs."""
from base64 import b64encode
from dataclasses import replace
from hashlib import md5, sha256
from io import BytesIO
from pathlib import Path
from secrets import token_bytes, token_hex
import shutil
import subprocess
from tempfile import TemporaryDirectory

import httpx
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

SCANNER_HOST = "acceptance-scanner.invalid"
CONTROL = b"PracticaMIA fictional scanner control only. This content is harmless."
MARKER = "PRACTICAMIA SYNTHETIC TEST ONLY"


def pdf(*lines, image=None):
    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=(600, 380))
    if image is None:
        for i, line in enumerate(lines):
            page.drawString(44, 320 - i * 28, line)
    else:
        page.drawImage(ImageReader(image), 0, 0, width=600, height=380)
    page.save()
    return buffer.getvalue()


def image(*lines):
    result = Image.new("RGB", (1400, 880), "white")
    draw = ImageDraw.Draw(result)
    font = ImageFont.truetype("DejaVuSans.ttf", 40)
    for i, line in enumerate((MARKER, *lines)):
        draw.text((85, 115 + i * 100), line, font=font, fill="black")
    return result


def encode(bitmap, file_format):
    buffer = BytesIO()
    bitmap.save(buffer, format=file_format)
    return buffer.getvalue()


class DocumentFixtures:
    def __init__(self):
        self.scanner = shutil.which("clamscan")
        if not self.scanner:
            raise RuntimeError("Install ClamAV before running document acceptance")
        self.temporary = TemporaryDirectory(prefix="practicamia-document-acceptance-")
        self.directory = Path(self.temporary.name)
        self.signatures = self.directory / "test-only.hdb"
        self.signatures.write_text(
            f"{md5(CONTROL, usedforsecurity=False).hexdigest()}:{len(CONTROL)}:PracticaMIA.Fictional.Control\n",
            encoding="ascii",
        )
        italian = image("Titolo di occupazione: Contratto di locazione registrato",
                        "Data del trasferimento: 05.11.2026")
        english = image("Housing arrangement: Registered private rental",
                        "Move-in date: 2026-11-05")
        infected_pdf = pdf(MARKER, "Housing basis: guest")
        self.files = {
            "lease.pdf": ("application/pdf", pdf(
                MARKER, "Housing basis: Registered private rental",
                "Move-in date: 2026-11-06", "Synthetic private marker: FIXTURE_ONLY_64")),
            "scanned-lease.pdf": ("application/pdf", pdf(image=italian)),
            "lease-it.png": ("image/png", encode(italian, "PNG")),
            "lease-en.jpg": ("image/jpeg", encode(english, "JPEG")),
            "scanner-control.pdf": ("application/pdf", infected_pdf),
        }
        self.infected_digest = sha256(infected_pdf).hexdigest()
        self.malformed = b"%PDF-1.7\nsynthetic invalid PDF without document structure\n"
        self.verdict = "normal"
        self.token = token_hex(24)
        self.cron_secret = token_hex(24)

    def settings(self, settings):
        return replace(
            settings, enable_private_document_api=True,
            private_document_key=b64encode(token_bytes(32)).decode("ascii"),
            private_document_scan_url=f"https://{SCANNER_HOST}/check",
            private_document_scan_host=SCANNER_HOST,
            private_document_scan_token=self.token,
            private_document_cron_secret=self.cron_secret,
            private_document_privacy_approved=True,
            private_document_controller="Synthetic test controller",
            private_document_contact="privacy@example.invalid",
        )

    def scanner_response(self, request):
        body = request.read()
        digest = sha256(body).hexdigest()
        assert request.method == "POST"
        assert str(request.url) == f"https://{SCANNER_HOST}/check"
        assert request.headers["authorization"] == f"Bearer {self.token}"
        assert request.headers["content-type"] == "application/octet-stream"
        assert request.headers["x-content-sha256"] == digest
        assert body == self.malformed or any(raw == body for _, raw in self.files.values()), (
            "The scanner accepts only generated fixture uploads"
        )
        if self.verdict == "unavailable":
            return httpx.Response(503)
        if self.verdict == "bad_digest":
            return httpx.Response(200, json={"status": "clean", "sha256": "0" * 64})
        # Attach a harmless control marker only inside the scanner adapter.
        # No malware samples or operational signature database are used.
        result = subprocess.run(
            [self.scanner, "--no-summary", "--stdout", "--database", str(self.signatures), "-"],
            input=CONTROL if digest == self.infected_digest else body,
            capture_output=True, timeout=6, check=False,
        )
        if result.returncode not in (0, 1):
            return httpx.Response(503)
        return httpx.Response(200, json={
            "status": "infected" if result.returncode == 1 else "clean",
            "sha256": digest,
        })
