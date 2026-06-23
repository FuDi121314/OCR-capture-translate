from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Config:
    source_lang: str = "en"         # OCR language
    target_lang: str = "zh"         # Translation target language
    capture_window_title: Optional[str] = None   # None = entire screen
    mtranserver_url: str = "http://127.0.0.1:8989/translate"   # mtranserver default port
    overlay_opacity: float = 0.85   
    update_interval_ms: int = 850   # refresh time

# constructor
config = Config()