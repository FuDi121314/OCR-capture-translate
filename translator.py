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
                "from": config.source_lang,
                "to": config.target_lang,
                "text": text,
                "html": False
            },
            timeout=500
        )
        if resp.status_code == 200:
            #print("received from mtranserver")             # debugger
            #print("received from mtranserver", resp.json())      # debugger
            return resp.json().get("result", "")

        else:
            return f"[Error {resp.status_code}]"
    except Exception as e:
        return f"[{e}]"