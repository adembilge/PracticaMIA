"""Run bundled OCR in a child process so the request can enforce a deadline."""

from pathlib import Path
import sys


TESSDATA_DIR = Path(__file__).with_name("tessdata")


if __name__ == "__main__":
    from io import BytesIO

    from PIL import Image
    from tesserocr import PyTessBaseAPI

    with Image.open(BytesIO(sys.stdin.buffer.read())) as image:
        with PyTessBaseAPI(path=str(TESSDATA_DIR), lang="ita+eng") as engine:
            engine.SetImage(image)
            sys.stdout.buffer.write(engine.GetUTF8Text().encode("utf-8"))
