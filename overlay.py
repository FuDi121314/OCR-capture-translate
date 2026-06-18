from PyQt5 import QtCore, QtWidgets, QtGui
from config import config

class OutlinedLabel(QtWidgets.QLabel):
    """A label that draws text with an outline (stroke)."""
    def __init__(self, text_color=QtGui.QColor(255, 255, 255), outline_color=QtGui.QColor(0, 0, 0), parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False) 
        self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.setWordWrap(False)
        self.setStyleSheet("background: transparent; border: none;") 

        self._text_color = text_color
        self._outline_color = outline_color

        # Transparent background
        self.setStyleSheet("background: transparent;")

    def setColors(self, text_color, outline_color):
        self._text_color = text_color
        self._outline_color = outline_color
        self.update()

    def paintEvent(self, event):
        """Custom paint to draw text with outline."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Draw outline (multiple offsets)
        pen = QtGui.QPen(self._outline_color, 2, QtCore.Qt.SolidLine)
        painter.setPen(pen)
        font = self.font()
        painter.setFont(font)

        # Draw text multiple times offset to create outline
        x, y = 1, 1  # padding
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (-1,0), (1,0), (0,-1), (0,1)]:
            painter.drawText(x + dx, y + dy + font.pixelSize(), self.text())

        # Draw main text
        pen = QtGui.QPen(self._text_color)
        painter.setPen(pen)
        painter.drawText(x, y + font.pixelSize(), self.text())
        # print(f"Painting with text_color: {self._text_color.name()}, outline: {self._outline_color.name()}")        #debugger
        painter.end()


class Overlay(QtWidgets.QWidget):
    text_update_signal = QtCore.pyqtSignal(list)

    def __init__(self, target_window_title: str):
        super().__init__()
        self.target_title = target_window_title
        self.labels = []

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)


        self.resize(400, 200)

        # Connect signal
        self.text_update_signal.connect(self.update_labels)

        # Timer to follow target window
        self.tracker = QtCore.QTimer()
        self.tracker.timeout.connect(self.follow_target)
        self.tracker.start(100)
        self.follow_target()

    def update_labels(self, label_data: list):
        """Remove old labels and create new ones at positions adjusted for DPI."""
        # Remove existing labels
        # print(f"update_labels called with {len(label_data)} items")     #debugger
        for lbl in self.labels:
            lbl.deleteLater()
        self.labels.clear()

        # Get the DPR of the screen this overlay is on
        dpr = self.devicePixelRatioF()

        for (x, y, w, h, text, text_color, outline_color) in label_data:
            if not text.strip():
                continue

            # Convert physical coordinates to logical pixels
            x_log = int(x / dpr)
            y_log = int(y / dpr)
            w_log = int(w / dpr)
            h_log = int(h / dpr)

            lbl = OutlinedLabel(text_color, outline_color, self)
            lbl.setText(text)

            # Font size based on logical height
            font_size = max(8, int(h_log * 0.8))
            font = lbl.font()
            font.setPixelSize(font_size)
            lbl.setFont(font)

            lbl.setGeometry(x_log, y_log, max(w_log, 50), max(h_log, 15))
            lbl.show()
            self.labels.append(lbl)
            # print(f"Creating label with text_color: {text_color.name()}, outline: {outline_color.name()}")      #debugger
            
            
    def follow_target(self):
        """Move and resize the overlay to exactly cover the target window (DPI‑aware)."""
        from capture import get_window_rect

        rect = get_window_rect(self.target_title)
        
        # print(f"follow_target: rect = {rect}") #debugger
         
        if rect is None:
            self.hide()
            return

        x_phys, y_phys, w_phys, h_phys = rect

        # Find the screen that contains the window's top-left point (physical coordinates)
        point = QtCore.QPoint(x_phys, y_phys)
        screen = None
        for s in QtWidgets.QApplication.screens():
            if s.geometry().contains(point):
                screen = s
                break
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()

        # Get device pixel ratio for this screen
        dpr = screen.devicePixelRatio() if hasattr(screen, 'devicePixelRatio') else self.devicePixelRatioF()

        # Convert physical to logical pixels
        x_log = x_phys / dpr
        y_log = y_phys / dpr
        w_log = w_phys / dpr
        h_log = h_phys / dpr

        # Clip to screen's available geometry (logical)
        screen_geom = screen.availableGeometry()
        x_log = max(x_log, screen_geom.x())
        y_log = max(y_log, screen_geom.y())
        w_log = min(w_log, screen_geom.width())
        h_log = min(h_log, screen_geom.height())

        self.setGeometry(int(round(x_log)), int(round(y_log)), int(round(w_log)), int(round(h_log)))

        if not self.isVisible():
            self.show()

    def closeEvent(self, event):
        self.tracker.stop()
        super().closeEvent(event)