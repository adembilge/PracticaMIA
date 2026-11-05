"""Conservative bounded extraction of original official PDF bytes.

Page-numbered passages preserve exact offsets into normalized_text and allow
a human reviewer to compare the extraction with the PDF page. Layout, tables,
check boxes and scanned images are not verified by automated text extraction.
"""
from hashlib import sha256
from io import BytesIO

from pypdf import PdfReader

from app.knowledge.html_extraction import (
    ExtractedHTML, ExtractedPassage, MAX_PASSAGES, MAX_PASSAGE_CHARS, _split_text,
)

PDF_EXTRACTION_VERSION = "pdf-v1"
MAX_PDF_BYTES = 4 * 1024 * 1024
MAX_PDF_PAGES = 20
MAX_PDF_TEXT_CHARS = 250000


def extract_pdf(raw: bytes) -> ExtractedHTML:
    if not raw.startswith(b"%PDF-") or len(raw) > MAX_PDF_BYTES:
        raise ValueError("PDF must have its original header and be at most 4 MiB")

    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs require separate review")
        page_count = len(reader.pages)
        if not 1 <= page_count <= MAX_PDF_PAGES:
            raise ValueError("PDF page count outside the supported range")
        chunks: list[tuple[str, str]] = []
        total_chars = 0
        for page_index, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text(extraction_mode="plain") or ""
            normalized = " ".join(raw_text.split())
            total_chars += len(normalized)
            if total_chars > MAX_PDF_TEXT_CHARS:
                raise ValueError("Extracted PDF text is too large")
            for fragment in _split_text(normalized):
                if fragment:
                    chunks.append((f"Page {page_index}", fragment))
            if len(chunks) > MAX_PASSAGES:
                raise ValueError("Too many extracted PDF passages")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("PDF parsing or text extraction failed") from exc

    if not chunks:
        raise ValueError("PDF has no extractable text; scanned PDFs need manual review")

    text_parts: list[str] = []
    passages: list[ExtractedPassage] = []
    offset = 0
    for ordinal, (section, content) in enumerate(chunks):
        if ordinal:
            text_parts.append("\n\n")
            offset += 2
        start = offset
        text_parts.append(content)
        offset += len(content)
        passages.append(ExtractedPassage(
            ordinal=ordinal, section_path=section, start_offset=start,
            end_offset=offset, content=content,
            content_sha256=sha256(content.encode("utf-8")).hexdigest(),
        ))
    return ExtractedHTML("".join(text_parts), tuple(passages))
