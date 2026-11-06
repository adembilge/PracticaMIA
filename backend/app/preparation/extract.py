"""Bounded document intake and evidence-backed, untrusted field suggestions.

Only available in isolated, synthetic-only preview. No document text goes to
an LLM, and extracted text is never an approved case fact without user action.
For images, OCR requires a separately installed Tesseract executable.
"""
from __future__ import annotations

from io import BytesIO
import re

from pypdf import PdfReader

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_PAGES = 15
MAX_EXTRACTED_CHARS = 18000
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


def extract_document(content: bytes, media_type: str) -> dict:
    validate_document(content, media_type)
    pages: list[dict] = []
    if media_type == "application/pdf":
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise DocumentRejected("Encrypted PDFs are not supported")
            if not 1 <= len(reader.pages) <= MAX_PAGES:
                raise DocumentRejected("PDF page count must be 1-15")
            for page_number, page in enumerate(reader.pages, 1):
                raw = page.extract_text() or ""
                if len(raw) > MAX_EXTRACTED_CHARS:
                    raise DocumentRejected("PDF page text exceeds size budget")
                pages.append({"page": page_number, "text": raw})
        except DocumentRejected:
            raise
        except Exception as exc:
            raise DocumentRejected("PDF could not be safely parsed") from exc
    else:
        try:
            from PIL import Image, UnidentifiedImageError
            import pytesseract
            from pytesseract import TesseractNotFoundError
        except ImportError as exc:
            raise ExtractionUnavailable("OCR dependencies are not installed") from exc
        try:
            img = Image.open(BytesIO(content))
            img.verify()
            img = Image.open(BytesIO(content))
            if img.width * img.height > 12_000_000:
                raise DocumentRejected("Image exceeds pixel budget")
            if media_type == "image/png" and img.format != "PNG":
                raise DocumentRejected("Invalid PNG")
            if media_type == "image/jpeg" and img.format != "JPEG":
                raise DocumentRejected("Invalid JPEG")
            value = pytesseract.image_to_string(img, lang="ita+eng", timeout=10)
            pages.append({"page": 1, "text": value})
        except TesseractNotFoundError as exc:
            raise ExtractionUnavailable("Tesseract executable is not available") from exc
        except DocumentRejected:
            raise
        except Exception as exc:
            raise DocumentRejected("Image could not be safely processed") from exc
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
