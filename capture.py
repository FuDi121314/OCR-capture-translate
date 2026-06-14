import mss
import numpy as np
import pygetwindow as gw
from config import config

def get_window_rect():
    """Return the bounding box of the target window (left, top, width, height)."""
    if config.capture_window_title:
        windows = gw.getWindowsWithTitle(config.capture_window_title)
        if windows:
            win = windows[0]
            # Ensure the window is not minimized; may need to activate
            return (win.left, win.top, win.width, win.height)
    # Fallback: capture entire primary monitor
    with mss.mss() as sct:
        monitor = sct.monitors[1]   # primary
        return (monitor["left"], monitor["top"],
                monitor["width"], monitor["height"])

def capture():
    """Capture the target region and return an RGB numpy array."""
    region = get_window_rect()
    left, top, width, height = region
    with mss.mss() as sct:
        monitor = {"top": top, "left": left, "width": width, "height": height}
        img = sct.grab(monitor)
        # Convert from BGRA to RGB
        return np.array(img)[:, :, :3][:, :, ::-1]