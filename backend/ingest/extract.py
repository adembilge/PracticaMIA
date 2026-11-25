from io import BytesIO

import pypdf
import trafilatura


def extract_html(body: bytes, url: str) -> tuple[str, str]:
    text = trafilatura.extract(body, url=url, output_format="txt")
    if text is None or not str(text).strip():
        return ("", "")

    metadata = trafilatura.extract_metadata(body, default_url=url)
    title = ""
    if metadata is not None and metadata.title:
        title = str(metadata.title).strip()

    return (title, str(text).strip())


def extract_pdf(body: bytes) -> tuple[str, str]:
    reader = pypdf.PdfReader(BytesIO(body))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages)
    if not text.strip():
        return ("", "")

    title = "document"
    if reader.metadata is not None and reader.metadata.title:
        raw = str(reader.metadata.title).strip()
        if raw:
            title = raw

    return (title, text)