import sys
import threading
import time
import pygetwindow as gw
from PyQt5 import QtWidgets, QtCore, QtGui

from config import config
from capture import capture_window
from ocr_engine import init_ocr, do_ocr
from translator import translate
from overlay import Overlay

class WindowListWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            # Emit a custom signal; the main window will handle the move logic
            self.parent().move_window_between_lists(item.text())
        super().mouseDoubleClickEvent(event)


# ─────────────────────────────────────────
# Main Manager Window
# ─────────────────────────────────────────
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

    def refresh_window_list(self):
        """Update the 'all windows' list (does not disturb selected list)."""
        current_all = {self.all_windows_list.item(i).text()
                       for i in range(self.all_windows_list.count())}
        real_windows = {w for w in gw.getAllTitles() if w.strip()}

        # Add new windows
        for w in real_windows - current_all:
            self.all_windows_list.addItem(w)

        # Remove windows that no longer exist (also clean up overlays)
        for i in range(self.all_windows_list.count() - 1, -1, -1):
            title = self.all_windows_list.item(i).text()
            if title not in real_windows:
                self.all_windows_list.takeItem(i)
                # If this window was being translated, stop it
                self.stop_translating(title)

    def move_window_between_lists(self, title: str):
        """Double‑click handler: move 'title' between the two lists."""
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

    def add_to_selected(self, title: str):
        """Add window to selected list and start translation overlay."""
        # Remove from all‑windows list
        items = self.all_windows_list.findItems(title, QtCore.Qt.MatchExactly)
        for item in items:
            self.all_windows_list.takeItem(self.all_windows_list.row(item))

        # Add to selected list
        self.selected_list.addItem(title)

        # Start translating
        self.start_translating(title)
        self.status_label.setText(f"Started translating: {title}")

    def remove_from_selected(self, title: str):
        """Remove window from selected list and stop translation overlay."""
        # Remove from selected list
        items = self.selected_list.findItems(title, QtCore.Qt.MatchExactly)
        for item in items:
            self.selected_list.takeItem(self.selected_list.row(item))

        # Add back to all‑windows list
        self.all_windows_list.addItem(title)

        # Stop translating
        self.stop_translating(title)
        self.status_label.setText(f"Stopped translating: {title}")

    def start_translating(self, title: str):
        """Spawn an overlay and a translation worker thread for this window."""
        if title in self.overlays:
            return  # already active

        overlay = Overlay(title)
        overlay.show()
        self.overlays[title] = overlay

        # Start a translation loop in a separate thread
        self.translation_active[title] = True
        t = threading.Thread(target=self.translation_loop, args=(title,), daemon=True)
        t.start()

    def stop_translating(self, title: str):
        """Stop the translation loop and remove the overlay."""
        self.translation_active[title] = False
        if title in self.overlays:
            self.overlays[title].close()
            del self.overlays[title]

    def translation_loop(self, title: str):
        """Continuously capture, OCR, translate, and update overlay with positions."""
        from ocr_engine import do_ocr_with_boxes
    
        while self.translation_active.get(title, False):
            img = capture_window(title)
            if img is None:
                time.sleep(config.update_interval_ms / 1000.0)
                continue
            
            # Get OCR results with bounding boxes: (bbox, text, confidence)
            ocr_results = do_ocr_with_boxes(img)
    
            # Build label data: [(x, y, w, h, translated_text), ...]
            label_data = []
            for bbox, text, conf in ocr_results:
                # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                # We need the top-left corner and width/height
                x1, y1 = bbox[0]
                x2, y2 = bbox[2]  # bottom-right corner
    
                x = x1
                y = y1
                w = x2 - x1
                h = y2 - y1
    
                if text.strip():
                    translated = translate(text)
                    # Make the box a bit wider for translated text (often longer)
                    label_data.append((x, y, max(w, 50), max(h, 15), translated))
    
            # Emit signal to update overlay
            if title in self.overlays:
                overlay = self.overlays[title]
                overlay.text_update_signal.emit(label_data)
    
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