from PyQt5 import QtCore, QtWidgets, QtGui
import keyboard
from config import config

class Overlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.original_text = ""
        self.translated_text = ""
        self.show_original = False   # True shows original, False shows translation

        # Window flags: frameless, always on top, tool (doesn't show in taskbar on Windows)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)  # click-through

        # Setup UI
        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.label.setWordWrap(True)
        self.label.setStyleSheet(
            f"background-color: rgba(0, 0, 0, {int(config.overlay_opacity * 255)}); "
            "color: white; padding: 10px; font-size: 16px;"
        )
        self.resize(800, 200)

        # Hotkey
        keyboard.add_hotkey('ctrl+shift+t', self.toggle_display)

    def update_text(self, original: str, translated: str):
        self.original_text = original
        self.translated_text = translated
        self._refresh_label()

    def toggle_display(self):
        self.show_original = not self.show_original
        self._refresh_label()

    def _refresh_label(self):
        text = self.original_text if self.show_original else self.translated_text
        self.label.setText(text)
        self.label.adjustSize()
        self.adjustSize()

    def move_to(self, x, y, width, height):
        self.setGeometry(x, y, width, height)

    def closeEvent(self, event):
        keyboard.remove_hotkey('ctrl+shift+t')
        super().closeEvent(event)