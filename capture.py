import win32gui
import win32ui
import win32con
import numpy as np
import pygetwindow as gw
from ctypes import windll

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
    """Capture the window's own content using PrintWindow (ignores overlays)."""
    # Find the window handle
    hwnd = win32gui.FindWindow(None, title)
    if not hwnd:
        # fallback: case‑insensitive search
        for w in gw.getAllWindows():
            if w.title.strip().lower() == title.lower():
                hwnd = w._hWnd
                break
        if not hwnd:
            return None

    windll.user32.SetProcessDPIAware() ## dpi awareness for correct scaling on high‑DPI displays, or some part disappears
    # Get window dimensions
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    w, h = right - left, bottom - top
    if w <= 0 or h <= 0:
        return None

    # Get the window's device context (DC)
    hwndDC = win32gui.GetWindowDC(hwnd)
    if not hwndDC:
        return None

    try:
        # Create a compatible DC and bitmap
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(bitmap)

        
        # Parameters: (hwnd, hdc, flags) – flags=0 means capture entire window
        success = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)   #  api return bool

        # Fallback to BitBlt if PrintWindow fails (unlikely on modern Windows)
        if not success:
            print("PrintWindow failed, falling back to BitBlt")
            win32gui.BitBlt(
                saveDC.GetSafeHdc(), 0, 0, w, h,
                hwndDC, 0, 0,
                win32con.SRCCOPY
            )

        # Read bitmap data into a numpy array (BGRA format)
        bmpstr = bitmap.GetBitmapBits(True)
        img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((h, w, 4))

        # Convert BGRA -> RGB
        return img[:, :, :3][:, :, ::-1]

    except Exception as e:
        print(f"Capture error: {e}")
        return None

    finally:
        # Clean up all DCs and resources safely
        if 'mfcDC' in locals() and mfcDC:
            try:
                mfcDC.DeleteDC()
            except:
                pass
        if 'saveDC' in locals() and saveDC:
            try:
                saveDC.DeleteDC()
            except:
                pass
        if 'bitmap' in locals() and bitmap:
            try:
                win32gui.DeleteObject(bitmap.GetHandle())
            except:
                pass
        if hwndDC:
            win32gui.ReleaseDC(hwnd, hwndDC)
            
if __name__ == "__main__":
    
    img = capture_window("Steam")
    if img is not None:
        import cv2
        cv2.imwrite("debug/ThisCapture.png", img)
    else:
        print("Failed to capture window.")