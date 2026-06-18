import sys
import threading
import time
from turtle import title
import pygetwindow as gw
from PyQt5 import QtWidgets, QtCore, QtGui

from config import config
from capture import capture_window
from ocr_engine import init_ocr, do_ocr
from translator import translate
from overlay import Overlay

QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)

class WindowListWidget(QtWidgets.QListWidget):
    # new signal: (list_widget, item_text)
    itemDoubleClicked = QtCore.pyqtSignal(QtWidgets.QListWidget, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            # emit signal with self and the text (stripped)
            self.itemDoubleClicked.emit(self, item.text().strip())
        super().mouseDoubleClickEvent(event)



class ManagerWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Translator Manager")
        self.setMinimumSize(700, 500)

        # Active overlays: dict[window_title -> Overlay]
        self.overlays = {}
        # Translation worker states: dict[window_title -> bool] (running flag)
        self.translation_active = {}

        self.init_ui()
        self.refresh_window_list()

        # Timer to refresh the all‑windows list every 2 seconds
        self.list_timer = QtCore.QTimer()
        self.list_timer.timeout.connect(self.refresh_window_list)
        self.list_timer.start(2000)

    def init_ui(self):
                
        layout = QtWidgets.QVBoxLayout(self)

        # ── Top: language selection ──
        lang_layout = QtWidgets.QHBoxLayout()
        lang_layout.addWidget(QtWidgets.QLabel("Source:"))
        self.src_combo = QtWidgets.QComboBox()
        self.src_combo.addItems(["en", "es", "fr", "de", "ja", "ko", "zh"])
        self.src_combo.setCurrentText("en")
        lang_layout.addWidget(self.src_combo)

        lang_layout.addWidget(QtWidgets.QLabel("Target:"))
        self.tgt_combo = QtWidgets.QComboBox()
        self.tgt_combo.addItems(["en", "es", "fr", "de", "ja", "ko", "zh"])
        self.tgt_combo.setCurrentText("zh")
        lang_layout.addWidget(self.tgt_combo)

        self.apply_lang_btn = QtWidgets.QPushButton("Apply Languages")
        self.apply_lang_btn.clicked.connect(self.apply_languages)
        lang_layout.addWidget(self.apply_lang_btn)
        layout.addLayout(lang_layout)

        # ── Middle: dual lists ──
        lists_layout = QtWidgets.QHBoxLayout()

        # Left: all windows
        left_box = QtWidgets.QVBoxLayout()
        left_box.addWidget(QtWidgets.QLabel("All Windows (double‑click to add)"))
        self.all_windows_list = WindowListWidget(self)
        left_box.addWidget(self.all_windows_list)
        lists_layout.addLayout(left_box)

        # Right: selected for translation
        right_box = QtWidgets.QVBoxLayout()
        right_box.addWidget(QtWidgets.QLabel("Selected for Translation (double‑click to remove)"))
        self.selected_list = WindowListWidget(self)
        right_box.addWidget(self.selected_list)
        lists_layout.addLayout(right_box)

        layout.addLayout(lists_layout)

        # ── Bottom: status ──
        self.status_label = QtWidgets.QLabel("Ready. Double‑click a window to start/stop translation.")
        layout.addWidget(self.status_label)
        
        self.all_windows_list.itemDoubleClicked.connect(self.on_list_double_click)
        self.selected_list.itemDoubleClicked.connect(self.on_list_double_click)
        
    def on_list_double_click(self, list_widget: QtWidgets.QListWidget, title: str):
        
        """Handle double‑click on either list."""
        # Normalize title (strip spaces)
        title = title.strip()
        if not title:
            return

        # Determine which list was clicked
        if list_widget is self.all_windows_list:
            # Remove from all, add to selected
            self.add_to_selected(title)
        elif list_widget is self.selected_list:
            # Remove from selected, add back to all
            self.remove_from_selected(title)

    def refresh_window_list(self):
        """Update the 'all windows' list (does not disturb selected list)."""
        selected_titles = {self.selected_list.item(i).text() for i in range(self.selected_list.count())}
        current_all = {self.all_windows_list.item(i).text()
                       for i in range(self.all_windows_list.count())}
        real_windows = {w for w in gw.getAllTitles() if w.strip()}
        
        # Add new windows
        for w in real_windows - current_all:
            if w not in selected_titles:
                self.all_windows_list.addItem(w)

        # Remove windows that no longer exist (also clean up overlays)
        for i in range(self.all_windows_list.count() - 1, -1, -1):
            title = self.all_windows_list.item(i).text()
            if title not in real_windows:
                self.all_windows_list.takeItem(i)
                # If this window was being translated, stop it
                self.stop_translating(title)
                
    """
    def move_window_between_lists(self, title: str):
        # Double‑click handler: move 'title' between the two lists.
        # Is it currently in the 'all windows' list?
        in_all = any(self.all_windows_list.item(i).text() == title
                     for i in range(self.all_windows_list.count()))
        in_selected = any(self.selected_list.item(i).text() == title
                          for i in range(self.selected_list.count()))

        if in_all and not in_selected:
            # Move FROM all TO selected → start translating
            self.add_to_selected(title)
        elif in_selected and not in_all:
            # Move FROM selected TO all → stop translating
            self.remove_from_selected(title)
        else:
            self.status_label.setText(f"Window '{title}' not found in either list.")
    """
    
    def add_to_selected(self, title: str):
        
        title = title.strip()
        # Remove from all‑windows list (if present)
        items = self.all_windows_list.findItems(title, QtCore.Qt.MatchExactly)
        for item in items:
            self.all_windows_list.takeItem(self.all_windows_list.row(item))

        # Add to selected list (avoid duplicates)
        existing = self.selected_list.findItems(title, QtCore.Qt.MatchExactly)
        if not existing:
            self.selected_list.addItem(title)

        # Start translating
        self.start_translating(title)
        self.status_label.setText(f"Started translating: {title}")

    def remove_from_selected(self, title: str):
        """Remove window from selected list and stop translation overlay."""
        title = title.strip()

        # Remove from selected list
        items = self.selected_list.findItems(title, QtCore.Qt.MatchExactly)
        for item in items:
            self.selected_list.takeItem(self.selected_list.row(item))
    
        # Add back to all‑windows list (avoid duplicates)
        existing = self.all_windows_list.findItems(title, QtCore.Qt.MatchExactly)
        if not existing:
            self.all_windows_list.addItem(title)
    
        # Stop translating
        self.stop_translating(title)
        self.status_label.setText(f"Stopped translating: {title}")

    def start_translating(self, title: str):
        """Spawn an overlay and a translation worker thread for this window."""
        title = title.strip()   # normalize
        
        # print(f"start_translating: title = '{title}' (len={len(title)})")       #debugger
        if title in self.overlays:
            # print(f"Overlay for '{title}' already exists, skipping")    #debugger
            return
        
        overlay = Overlay(title)
        overlay.show()
        self.overlays[title] = overlay
        self.translation_active[title] = True
        # print(f"Starting translation thread for '{title}'")         #debugger
        t = threading.Thread(target=self.translation_loop, args=(title,), daemon=True) 
        t.start()
        # print(f"Thread started for '{title}'")          #debugger

    def stop_translating(self, title: str):
        """Stop the translation loop and remove the overlay."""
        self.translation_active[title] = False
        if title in self.overlays:
            self.overlays[title].close()
            del self.overlays[title]

    def extract_text_color(self,crop):
        """
        Given a cropped image (numpy array HxWx3), guess the text color.
        """
        import numpy as np
        from PyQt5.QtGui import QColor

        pixels = crop.reshape(-1, 3)
        # Find the most common color (the background)
        from collections import Counter
        # Quantize to reduce noise (each channel to multiples of 16)
        quantized = (pixels // 16) * 16
        pixel_tuples = [tuple(p) for p in quantized]
        bg_tuple = Counter(pixel_tuples).most_common(1)[0][0]
        bg_color = np.array(bg_tuple, dtype=np.uint8)

        # Compute distance from background for each pixel
        dist = np.sqrt(np.sum((pixels - bg_color) ** 2, axis=1))
        # Take the color of the pixel with maximum distance (text)
        text_pixel = pixels[np.argmax(dist)]
        return QColor(int(text_pixel[0]), int(text_pixel[1]), int(text_pixel[2]))

    def translation_loop(self, title: str):
        """Continuously capture, OCR, translate, and update overlay with positions."""
        from ocr_engine import do_ocr
        import numpy as np
        from collections import Counter

        # print(f"translation_loop ENTERED with title = '{title}' (len={len(title)})")            #debugger
        # print(f"self.translation_active keys: {list(self.translation_active.keys())}")          #debugger
        # print(f"self.translation_active.get('{title}') = {self.translation_active.get(title)}") #debugger

        while self.translation_active.get(title, False):
            img = capture_window(title)
            if img is None:
                # print("capture_window returned None")
                time.sleep(config.update_interval_ms / 1000.0)
                continue
            
            # print("capture_window succeeded, doing OCR...")     #debugger
            ocr_results = do_ocr(img)
            # print(f"OCR returned {len(ocr_results)} items")     #debugger
    
            # Build label data: [(x, y, w, h, translated_text), ...]
            label_data = []
            for bbox, text, conf in ocr_results:
                # bbox corners: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                x1, y1 = bbox[0]
                x2, y2 = bbox[2]
                x, y = int(x1), int(y1)
                w, h = int(x2 - x1), int(y2 - y1)
    
                if w < 1 or h < 1 or not text.strip():
                    continue
                
                # Crop the bounding box from the captured image
                crop = img[y:y+h, x:x+w]
                # Extract text color from crop
                text_color = self.extract_text_color(crop)
    
                # Outline color: black if text is light, white if text is dark
                luminance = 0.299 * text_color.red() + 0.587 * text_color.green() + 0.114 * text_color.blue()
                if luminance > 128:
                    outline_color = QtGui.QColor(0, 0, 0)
                else:
                    outline_color = QtGui.QColor(255, 255, 255)
    
                translated = translate(text)
                label_data.append((x, y, max(w, 50), max(h, 15), translated, text_color, outline_color))
    
            # print(f"Built {len(label_data)} labels")
            if title in self.overlays:
                overlay = self.overlays[title]
                # print(f"Emitting {len(label_data)} labels for {title}")       #debugger
                overlay.text_update_signal.emit(label_data)
            else:
                print(f"Overlay for '{title}' not found in self.overlays")      # this is not debugger, sb
    
            time.sleep(config.update_interval_ms / 1000.0)
        
    def apply_languages(self):
        config.source_lang = self.src_combo.currentText()
        config.target_lang = self.tgt_combo.currentText()
        init_ocr()  # re‑init OCR with new language
        self.status_label.setText(f"Languages set: {config.source_lang} → {config.target_lang}")

    def closeEvent(self, event):
        # Stop all translations
        for title in list(self.overlays.keys()):
            self.stop_translating(title)
        self.list_timer.stop()
        super().closeEvent(event)



def main():
    app = QtWidgets.QApplication(sys.argv)
    init_ocr()
    manager = ManagerWindow()
    manager.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()