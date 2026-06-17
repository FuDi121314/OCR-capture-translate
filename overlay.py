from PyQt5 import QtCore, QtWidgets, QtGui
from config import config

class TranslationLabel(QtWidgets.QLabel):
    """A single floating label for one translated text region."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.setWordWrap(False)
        self.setStyleSheet("color: yellow; background-color: rgba(0, 0, 0, 180); padding: 2px;")


class Overlay(QtWidgets.QWidget):
    """
    A transparent window that follows a target window and places
    translated text labels exactly where the original text was detected.
    """
    text_update_signal = QtCore.pyqtSignal(list)  # list of (x, y, w, h, translated_text)

    def __init__(self, target_window_title: str):
        super().__init__()
        self.target_title = target_window_title
        self.labels = []  # list of TranslationLabel

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # NOTE: The overlay itself is NOT transparent for mouse events,
        # but each label is. So you can click through the labels.

        self.resize(400, 200)

        # Connect signal
        self.text_update_signal.connect(self.update_labels)

        # Timer to follow target window
        self.tracker = QtCore.QTimer()
        self.tracker.timeout.connect(self.follow_target)
        self.tracker.start(100)

        self.follow_target()

    def update_labels(self, label_data: list):
        """
        label_data: list of tuples (x, y, w, h, translated_text)
        Removes old labels and creates new ones at the given positions.
        """
        # Remove all existing labels
        for lbl in self.labels:
            lbl.deleteLater()
        self.labels.clear()

        for (x, y, w, h, text) in label_data:
            if not text.strip():
                continue

            lbl = TranslationLabel(self)
            lbl.setText(text)

            # Calculate font size based on the original text height
            # Use ~80% of the box height for the font
            font_size = max(8, int(h * 0.8))
            font = lbl.font()
            font.setPixelSize(font_size)
            lbl.setFont(font)

            # Position and size the label
            lbl.setGeometry(int(x), int(y), max(int(w), 50), int(h))
            lbl.show()
            self.labels.append(lbl)

    def follow_target(self):
        """Move and resize the overlay to exactly cover the target window."""
        from capture import get_window_rect
        rect = get_window_rect(self.target_title)
        if rect is None:
            self.hide()
            return

        x, y, w, h = rect

        if w <= 0 or h <= 0 or x < -10000 or y < -10000:
            self.hide()
            return

        if not self.isVisible():
            self.show()

        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        x = max(x, screen.left())
        y = max(y, screen.top())
        w = min(w, screen.width())
        h = min(h, screen.height())

        self.setGeometry(x, y, w, h)

    def closeEvent(self, event):
        self.tracker.stop()
        super().closeEvent(event)