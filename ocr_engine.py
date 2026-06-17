import easyocr
import torch
from config import config

reader = None

def init_ocr():
    global reader
    doihavegpu = torch.cuda.is_available()
    print(f"EasyOCR GPU available: {doihavegpu}")
    reader = easyocr.Reader([config.source_lang], gpu=doihavegpu)

def do_ocr_with_boxes(image):
    """
    Run OCR and return a list of (bbox, text, confidence).
    bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] in pixel coordinates.
    """
    if reader is None:
        init_ocr()
    results = reader.readtext(image, detail=1)  # detail=1 gives bounding boxes
    return results

def do_ocr(image):
    """Legacy: return only concatenated text."""
    results = do_ocr_with_boxes(image)
    return " ".join(r[1] for r in results)