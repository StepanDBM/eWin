# eWin_miniWindow.py

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets


def enum_value(container, name, enum_names=()):
    value = getattr(container, name, None)

    if value is not None:
        return value

    for enum_name in enum_names:
        enum_class = getattr(container, enum_name, None)

        if enum_class:
            value = getattr(enum_class, name, None)

            if value is not None:
                return value

    raise AttributeError("Could not find Qt enum: {}".format(name))


NO_FOCUS = enum_value(QtCore.Qt, "NoFocus", ("FocusPolicy",))
ALIGN_RIGHT = enum_value(QtCore.Qt, "AlignRight", ("AlignmentFlag",))
ALIGN_VCENTER = enum_value(QtCore.Qt, "AlignVCenter", ("AlignmentFlag",))

KEEP_ASPECT_RATIO = enum_value(
    QtCore.Qt,
    "KeepAspectRatio",
    ("AspectRatioMode",),
)

SMOOTH_TRANSFORMATION = enum_value(
    QtCore.Qt,
    "SmoothTransformation",
    ("TransformationMode",),
)

LEFT_BUTTON = enum_value(QtCore.Qt, "LeftButton", ("MouseButton",))

POINTING_CURSOR = enum_value(
    QtCore.Qt,
    "PointingHandCursor",
    ("CursorShape",),
)

TRANSPARENT_FOR_MOUSE = enum_value(
    QtCore.Qt,
    "WA_TransparentForMouseEvents",
    ("WidgetAttribute",),
)

class EWinMiniWindow(QtWidgets.QFrame):

    activate_requested = QtCore.Signal(object)
    close_requested = QtCore.Signal(object)

    CARD_WIDTH = 260
    CARD_HEIGHT = 150
    TITLE_HEIGHT = 30
    CLOSE_SIZE = 22
    CORNER_RADIUS = 9

    def __init__(self, candidate, parent=None):
        super(EWinMiniWindow, self).__init__(parent)

        self.candidate = candidate
        self.snapshot = QtGui.QPixmap()
        self.selected = False

        self.setObjectName("eWinMiniWindow")
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setCursor(POINTING_CURSOR)

        self.title_label = QtWidgets.QLabel(candidate.title, self)
        self.title_label.setObjectName("eWinMiniWindowTitle")
        self.title_label.setAlignment(ALIGN_RIGHT | ALIGN_VCENTER)
        self.title_label.setToolTip(candidate.title)
        self.title_label.setAttribute(TRANSPARENT_FOR_MOUSE, True)

        self.close_button = QtWidgets.QPushButton("X", self)
        self.close_button.setObjectName("eWinMiniWindowClose")
        self.close_button.setFixedSize(self.CLOSE_SIZE, self.CLOSE_SIZE)
        self.close_button.setFocusPolicy(NO_FOCUS)
        self.close_button.setToolTip("Close {}".format(candidate.title))
        self.close_button.clicked.connect(self._emit_close)

        self.capture_snapshot()
        self.update_style()

    def resizeEvent(self, event):
        margin = 7

        self.close_button.move(
            self.width() - self.CLOSE_SIZE - margin,
            margin,
        )

        title_width = self.width() - 16
        title_y = self.height() - self.TITLE_HEIGHT - 8

        self.title_label.setGeometry(
            8,
            title_y,
            title_width,
            self.TITLE_HEIGHT,
        )

        super(EWinMiniWindow, self).resizeEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        border_width = 3 if self.selected else 1
        half_border = border_width * 0.5

        card_rect = QtCore.QRectF(self.rect()).adjusted(
            half_border,
            half_border,
            -half_border,
            -half_border,
        )

        clip_path = QtGui.QPainterPath()
        clip_path.addRoundedRect(
            card_rect,
            self.CORNER_RADIUS,
            self.CORNER_RADIUS,
        )

        painter.save()
        painter.setClipPath(clip_path)
        painter.fillPath(clip_path, QtGui.QColor("#242424"))

        if not self.snapshot.isNull():
            painter.drawPixmap(
                QtCore.QPointF(0, 0),
                self.snapshot,
            )

        gradient_height = 55
        gradient_rect = QtCore.QRectF(
            0,
            self.height() - gradient_height,
            self.width(),
            gradient_height,
        )

        gradient = QtGui.QLinearGradient(
            0,
            gradient_rect.top(),
            0,
            gradient_rect.bottom(),
        )

        gradient.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        gradient.setColorAt(1.0, QtGui.QColor(0, 0, 0, 220))

        painter.fillRect(gradient_rect, gradient)
        painter.restore()

        border_color = QtGui.QColor(
            "#78b7ff" if self.selected else "#666666"
        )

        pen = QtGui.QPen(border_color, border_width)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)

        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(
            card_rect,
            self.CORNER_RADIUS,
            self.CORNER_RADIUS,
        )

        painter.end()

    def capture_snapshot(self):
        self.snapshot = QtGui.QPixmap()

        if not self.candidate or not self.candidate.is_valid():
            self.update()
            return False

        self.candidate.refresh_widget()
        widget = self.candidate.widget

        if widget is None:
            self.update()
            return False

        try:
            pixmap = widget.grab()
        except RuntimeError:
            self.update()
            return False

        if pixmap.isNull() or pixmap.width() <= 1:
            self.update()
            return False

        target_width = max(1, self.width())

        self.snapshot = pixmap.scaledToWidth(
            target_width,
            SMOOTH_TRANSFORMATION,
        )

        self.update()
        return True

    def set_selected(self, selected):
        self.selected = bool(selected)
        self.update_style()

    def update_style(self):
        weight = "bold" if self.selected else "normal"

        self.setStyleSheet("""
            QFrame#eWinMiniWindow {
                background-color: transparent;
                border: none;
            }

            QLabel#eWinMiniWindowTitle {
                color: white;
                background-color: transparent;
                border: none;
                padding: 0 6px;
                font-size: 12px;
                font-weight: %s;
            }

            QPushButton#eWinMiniWindowClose {
                color: white;
                background-color: rgba(20, 20, 20, 190);
                border: 1px solid rgba(220, 220, 220, 110);
                border-radius: 11px;
                font-size: 11px;
                font-weight: bold;
            }

            QPushButton#eWinMiniWindowClose:hover {
                background-color: #cc4545;
                border-color: #ff8b8b;
            }

            QPushButton#eWinMiniWindowClose:pressed {
                background-color: #963333;
            }
        """ % weight)

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == LEFT_BUTTON and self.rect().contains(event.pos()):
            self.activate_requested.emit(self.candidate)
            event.accept()
            return

        super(EWinMiniWindow, self).mouseReleaseEvent(event)

    def _emit_close(self):
        self.close_requested.emit(self.candidate)