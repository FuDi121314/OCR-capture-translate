import mss
import numpy as np
import pygetwindow as gw

def get_window_by_title(title: str):
    """Return the window object for a given title, or None."""
    windows = gw.getWindowsWithTitle(title)
    return windows[0] if windows else None

def get_window_rect(title: str):
    """Return (left, top, width, height) for a window, or None."""
    win = get_window_by_title(title)
    if win and not win.isMinimized:
        return (win.left, win.top, win.width, win.height)
    return None

def capture_window(title: str):
    """Capture a specific window and return an RGB numpy array, or None."""
    rect = get_window_rect(title)
    if rect is None:
        return None
    left, top, width, height = rect
    with mss.mss() as sct:
        monitor = {"top": top, "left": left, "width": width, "height": height}
        img = sct.grab(monitor)
        return np.array(img)[:, :, :3][:, :, ::-1]