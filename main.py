import sys
import torch
from PyQt5 import QtWidgets, QtCore
import pygetwindow as gw

from config import config
from capture import capture
from ocr_engine import init_ocr, do_ocr
from translator import translate
from overlay import Overlay

class SetupDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Translator Setup")
        layout = QtWidgets.QFormLayout(self)

        # Language selects
        self.src_combo = QtWidgets.QComboBox()
        self.src_combo.addItems(["en", "es", "fr", "de", "ja", "ko", "zh"])
        self.src_combo.setCurrentText("en")
        layout.addRow("Source language:", self.src_combo)

        self.tgt_combo = QtWidgets.QComboBox()
        self.tgt_combo.addItems(["en", "es", "fr", "de", "ja", "ko", "zh"])
        self.tgt_combo.setCurrentText("es")
        layout.addRow("Target language:", self.tgt_combo)

        # Window selection
        self.win_combo = QtWidgets.QComboBox()
        self.win_combo.addItem("Entire screen")
        for title in gw.getAllTitles():
            if title.strip():
                self.win_combo.addItem(title)
        layout.addRow("Capture window:", self.win_combo)

        # Start button
        self.start_btn = QtWidgets.QPushButton("Start")
        self.start_btn.clicked.connect(self.accept)
        layout.addWidget(self.start_btn)

    def get_config(self):
        config.source_lang = self.src_combo.currentText()
        config.target_lang = self.tgt_combo.currentText()
        choice = self.win_combo.currentText()
        config.capture_window_title = None if choice == "Entire screen" else choice

def main():
    app = QtWidgets.QApplication(sys.argv)

    # Show setup dialog
    setup = SetupDialog()
    if setup.exec_() != QtWidgets.QDialog.Accepted:
        sys.exit()
    setup.get_config()

    # Initialize OCR reader (may take a moment for the first time)
    init_ocr()

    # Create overlay
    overlay = Overlay()
    overlay.show()

    # Main update timer
    timer = QtCore.QTimer()
    timer.setInterval(config.update_interval_ms)

    def update():
        img = capture()
        original = do_ocr(img)
        if original.strip():
            translated = translate(original)
        else:
            translated = ""
        overlay.update_text(original, translated)

        # Position overlay over the captured window
        from capture import get_window_rect
        x, y, w, h = get_window_rect()
        overlay.move_to(x, y, w, h)

    timer.timeout.connect(update)
    timer.start()
    update()  # immediate first update

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()