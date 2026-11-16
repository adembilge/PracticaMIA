"""Bundle pinned OCR language data for permitted document runtimes."""

from hashlib import sha256
import os
from pathlib import Path
from urllib.request import urlopen


TESSDATA_REVISION = "65727574dfcd264acbb0c3e07860e4e9e9b22185"
TESSDATA_URL = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{TESSDATA_REVISION}"
TESSDATA_CHECKSUMS = {
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
    "ita": "b8f89e1e785118dac4d51ae042c029a64edb5c3ee42ef73027a6d412748d8827",
}


def install_tessdata(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for language, expected in TESSDATA_CHECKSUMS.items():
        name = f"{language}.traineddata"
        with urlopen(f"{TESSDATA_URL}/{name}", timeout=20) as response:
            data = response.read(8 * 1024 * 1024)
        if sha256(data).hexdigest() != expected:
            raise ValueError(f"OCR model checksum mismatch: {name}")
        (directory / name).write_bytes(data)


if __name__ == "__main__":
    environment = os.environ.get("VERCEL_ENV")
    isolated_preview = (
        environment == "preview"
        and os.environ.get("VERCEL_GIT_COMMIT_REF") == "preview/auth-review-isolated"
    )
    approved_vault_build = (
        environment == "production"
        and os.environ.get("ENABLE_PRIVATE_DOCUMENT_API") == "1"
        and os.environ.get("PRIVATE_DOCUMENT_PRIVACY_APPROVED") == "1"
        and os.environ.get("PRIVATE_DOCUMENT_FIXTURE_MODE") != "1"
    )
    if isolated_preview or approved_vault_build:
        install_tessdata(Path(__file__).parent / "app" / "preparation" / "tessdata")
        print("Bundled English and Italian OCR language data.")
