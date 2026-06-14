import requests
from config import config

def translate(text: str) -> str:
    """Send text to mtranserver and return the translation."""
    if not text.strip():
        return ""
    try:
        resp = requests.post(
            config.mtranserver_url,
            json={
                "text": text,
                "source": config.source_lang,
                "target": config.target_lang
            },
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json().get("translated_text", "")
        else:
            return f"[Error {resp.status_code}]"
    except Exception as e:
        return f"[{e}]"