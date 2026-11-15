"""Bounded document intake and evidence-backed, untrusted field suggestions.

Only available in isolated, synthetic-only preview. No document text goes to
an LLM, and extracted text is never an approved case fact without user action.
Image OCR uses Tesseract with Italian and English language data.
"""
from __future__ import annotations

from contextlib import closing
from io import BytesIO
from math import isfinite
import re
import subprocess
import sys
from threading import Lock
from time import monotonic

from pypdf import PdfReader

from app.preparation.ocr_worker import TESSDATA_DIR

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_PAGES = 15
MAX_EXTRACTED_CHARS = 18000
MAX_OCR_PIXELS = 12_000_000
MAX_RENDER_PIXELS = 4_000_000
MAX_RENDER_EDGE = 2800
OCR_TIMEOUT = 10
PDF_OCR_BUDGET = 25
PDFIUM_LOCK = Lock()
MIME = {"application/pdf", "image/png", "image/jpeg"}
DANGEROUS_PDF_MARKERS = (
    b"/JavaScript", b"/JS ", b"/Launch", b"/EmbeddedFile",
    b"/OpenAction", b"/RichMedia", b"/AcroForm",
)
ADDRESS_LABEL = re.compile(
    r"(?im)^(?:property address|indirizzo (?:immobile|abitazione))"
    r"\s*:\s*(?P<value>[^\r\n]{5,180})\s*$"
)


class DocumentRejected(ValueError):
    pass


class ExtractionUnavailable(RuntimeError):
    pass


def validate_document(content: bytes, media_type: str) -> None:
    if media_type not in MIME:
        raise DocumentRejected("Unsupported document type")
    if not content or len(content) > MAX_FILE_BYTES:
        raise DocumentRejected("Document is empty or exceeds 2 MiB")
    if media_type == "application/pdf":
        if not content.startswith(b"%PDF-"):
            raise DocumentRejected("PDF content does not match type")
        if any(marker in content for marker in DANGEROUS_PDF_MARKERS):
            raise DocumentRejected("Interactive or embedded PDF content is not supported")
    elif media_type == "image/png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise DocumentRejected("PNG content does not match type")
    elif not content.startswith(b"\xff\xd8\xff") or not content.endswith(b"\xff\xd9"):
        raise DocumentRejected("JPEG content does not match type")


def _ocr_image(image, *, timeout: float = OCR_TIMEOUT) -> str:
    if TESSDATA_DIR.is_dir():
        buffer = BytesIO()
        with image.convert("RGB") as rgb:
            rgb.save(buffer, format="PNG")
        try:
            result = subprocess.run(
                [sys.executable, str(TESSDATA_DIR.with_name("ocr_worker.py"))],
                input=buffer.getvalue(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=timeout, check=True,
            )
            return result.stdout.decode("utf-8")
        except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
            raise ExtractionUnavailable("Bundled OCR did not complete") from exc

    try:
        import pytesseract
    except ImportError as exc:
        raise ExtractionUnavailable("OCR dependencies are not installed") from exc

    try:
        languages = set(pytesseract.get_languages())
        if not {"ita", "eng"}.issubset(languages):
            raise ExtractionUnavailable("Italian and English OCR language data are required")
        return pytesseract.image_to_string(image, lang="ita+eng", timeout=timeout)
    except pytesseract.TesseractNotFoundError as exc:
        raise ExtractionUnavailable("Tesseract executable is not available") from exc
    except ExtractionUnavailable:
        raise
    except (pytesseract.TesseractError, RuntimeError) as exc:
        raise ExtractionUnavailable("Local OCR did not complete") from exc


def _rasterize_page(content: bytes, index: int):
    try:
        import pypdfium2 as pdfium
    except (ImportError, OSError) as exc:
        raise ExtractionUnavailable("PDF rasterizer is unavailable") from exc
    # PDFium's native API is process-global and does not support concurrent calls.
    with PDFIUM_LOCK, closing(pdfium.PdfDocument(content)) as document, closing(document[index]) as page:
        width, height = page.get_size()
        if not all(isfinite(value) and 1 <= value <= 14_400 for value in (width, height)):
            raise DocumentRejected("Unsupported PDF page dimensions")
        scale = min(3, MAX_RENDER_EDGE / max(width, height),
                    ((MAX_RENDER_PIXELS / (width * height)) ** 0.5))
        with closing(page.render(scale=scale, may_draw_forms=False)) as bitmap:
            return bitmap.to_pil().convert("RGB")


def _extract_pdf(content: bytes, *, ocr_pdf_scans: bool) -> list[dict]:
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise DocumentRejected("Encrypted PDFs are not supported")
        if not 1 <= len(reader.pages) <= MAX_PAGES:
            raise DocumentRejected("PDF page count must be 1-15")
        pages = []
        deadline = monotonic() + PDF_OCR_BUDGET
        for index, page in enumerate(reader.pages):
            raw = page.extract_text() or ""
            if ocr_pdf_scans and not raw.strip() and len(page.images) > 0:
                with _rasterize_page(content, index) as image:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        raise ExtractionUnavailable("PDF OCR exceeded its time budget")
                    raw = _ocr_image(image, timeout=min(OCR_TIMEOUT, remaining))
            if len(raw) > MAX_EXTRACTED_CHARS:
                raise DocumentRejected("PDF page text exceeds size budget")
            pages.append({"page": index + 1, "text": raw})
        return pages
    except (DocumentRejected, ExtractionUnavailable):
        raise
    except Exception as exc:
        raise DocumentRejected("PDF could not be safely parsed") from exc


def _extract_image(content: bytes, media_type: str) -> str:
    from PIL import Image

    try:
        with Image.open(BytesIO(content)) as image:
            expected = "PNG" if media_type == "image/png" else "JPEG"
            if image.width * image.height > MAX_OCR_PIXELS:
                raise DocumentRejected("Image exceeds pixel budget")
            if image.format != expected:
                raise DocumentRejected("Invalid image format")
            image.verify()
        with Image.open(BytesIO(content)) as image:
            return _ocr_image(image)
    except (DocumentRejected, ExtractionUnavailable):
        raise
    except Exception as exc:
        raise DocumentRejected("Image could not be safely processed") from exc


def extract_document(content: bytes, media_type: str, *, ocr_pdf_scans: bool = False) -> dict:
    validate_document(content, media_type)
    pages = (_extract_pdf(content, ocr_pdf_scans=ocr_pdf_scans)
             if media_type == "application/pdf" else
             [{"page": 1, "text": _extract_image(content, media_type)}])
    if sum(len(page["text"]) for page in pages) > MAX_EXTRACTED_CHARS:
        raise DocumentRejected("Total extracted text exceeds size budget")
    if not any(p["text"].strip() for p in pages):
        return {"status": "unreadable", "pages": [], "candidates": []}
    candidates: list[dict] = []
    for page in pages:
        for match in ADDRESS_LABEL.finditer(page["text"]):
            candidates.append({
                "field_name": "property_address",
                "raw_value": match.group("value").strip(),
                "page": page["page"],
                "evidence_span": match.group(0),
                "verification_state": "needs_user_confirmation",
            })
    return {
        "status": "needs_user_confirmation",
        "pages": pages,
        "candidates": candidates[:10],
    }


def verify_confirmation(extraction: dict, field_name: str, raw_value: str,
                        page: int) -> None:
    if field_name != "property_address" or not isinstance(page, int):
        raise DocumentRejected("Unsupported confirmation field")
    if extraction.get("status") != "needs_user_confirmation":
        raise DocumentRejected("Document has no readable extraction")
    if not any(
        value["field_name"] == field_name
        and value["raw_value"] == raw_value
        and value["page"] == page
        for value in extraction.get("candidates", [])
    ):
        raise DocumentRejected("Confirmation has no matching source evidence")
