"""One reviewed extraction dispatch for HTML and PDF snapshots."""
from app.knowledge.html_extraction import (
    EXTRACTION_VERSION, MAX_HTML_BYTES, extract_html,
)
from app.knowledge.pdf_extraction import (
    PDF_EXTRACTION_VERSION, MAX_PDF_BYTES, extract_pdf,
)

from app.knowledge.browser_text_extraction import (
    EXTRACTION_VERSION as BROWSER_TEXT_VERSION, MAX_BROWSER_TEXT_BYTES,
    extract_browser_text,
)

MEDIA_LIMITS = {
    "text/html": MAX_HTML_BYTES,
    "application/xhtml+xml": MAX_HTML_BYTES,
    "application/pdf": MAX_PDF_BYTES,
    "text/plain": MAX_BROWSER_TEXT_BYTES,
}
EXTRACTION_VERSIONS = {
    "text/html": EXTRACTION_VERSION,
    "application/xhtml+xml": EXTRACTION_VERSION,
    "application/pdf": PDF_EXTRACTION_VERSION,
    "text/plain": BROWSER_TEXT_VERSION,
}


def extract_document(body: bytes, media_type: str):
    limit = MEDIA_LIMITS.get(media_type)
    if limit is None:
        raise ValueError("Unsupported document type")
    if not body or len(body) > limit:
        raise ValueError("Document is empty or exceeds the media type size limit")
    if media_type == "text/plain":
        return extract_browser_text(body), BROWSER_TEXT_VERSION
    if media_type == "application/pdf":
        return extract_pdf(body), PDF_EXTRACTION_VERSION
    return extract_html(body), EXTRACTION_VERSION
