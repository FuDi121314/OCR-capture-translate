import easyocr
from config import config

reader = None

def init_ocr():
    global reader
    reader = easyocr.Reader([config.source_lang], gpu=True)   # change to gpu=False if no CUDA

def do_ocr(image):
    """Run OCR on the image and return the concatenated text."""
    if reader is None:
        init_ocr()
    results = reader.readtext(image, detail=0)   # detail=0 returns only text
    return " ".join(results)   # join lines with space