# eWin_overlay.py

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

import eWin_windows


def log(message):
    print("[eWin] {}".format(message))


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


WINDOW_FLAGS = (
    enum_value(QtCore.Qt, "Tool", ("WindowType",))
    | enum_value(QtCore.Qt, "FramelessWindowHint", ("WindowType",))
    | enum_value(QtCore.Qt, "WindowStaysOnTopHint", ("WindowType",))
    | enum_value(QtCore.Qt, "WindowDoesNotAcceptFocus", ("WindowType",))
)

ATTRIBUTE_TRANSLUCENT = enum_value(
    QtCore.Qt,
    "WA_TranslucentBackground",
    ("WidgetAttribute",),
)

ATTRIBUTE_SHOW_WITHOUT_ACTIVATING = enum_value(
    QtCore.Qt,
    "WA_ShowWithoutActivating",
    ("WidgetAttribute",),
)

ALIGN_CENTER = enum_value(QtCore.Qt, "AlignCenter", ("AlignmentFlag",))

SCROLLBAR_OFF = enum_value(
    QtCore.Qt,
    "ScrollBarAlwaysOff",
    ("ScrollBarPolicy",),
)


class WindowCard(QtWidgets.QFrame):

    close_requested = QtCore.Signal(object)

    def __init__(self, candidate, parent=None):
        super(WindowCard, self).__init__(parent)

        self.candidate = candidate
        self.setObjectName("eWinCard")
        self.setFixedSize(210, 90)

        self.close_button = QtWidgets.QPushButton("X")
        self.close_button.setObjectName("eWinCloseButton")
        self.close_button.setFixedSize(20, 20)
        self.close_button.setToolTip("Close {}".format(candidate.title))
        self.close_button.clicked.connect(self._emit_close)

        title = QtWidgets.QLabel(candidate.title)
        title.setObjectName("eWinCardTitle")
        title.setAlignment(ALIGN_CENTER)
        title.setWordWrap(True)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addStretch()
        header_layout.addWidget(self.close_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 10)
        layout.setSpacing(2)
        layout.addLayout(header_layout)
        layout.addWidget(title, 1)

        self.set_selected(False)

    def _emit_close(self):
        self.close_requested.emit(self.candidate)

    def set_selected(self, selected):
        border = "2px solid #78b7ff" if selected else "1px solid #666666"
        background = "#3d6fa8" if selected else "#353535"
        weight = "bold" if selected else "normal"
        color = "white" if selected else "#dddddd"

        self.setStyleSheet("""
            QFrame#eWinCard {{
                background-color: {};
                border: {};
                border-radius: 8px;
            }}

            QLabel#eWinCardTitle {{
                color: {};
                font-size: 13px;
                font-weight: {};
                border: none;
                background: transparent;
            }}

            QPushButton#eWinCloseButton {{
                color: #dddddd;
                background-color: transparent;
                border: none;
                border-radius: 10px;
                font-size: 11px;
                font-weight: bold;
            }}

            QPushButton#eWinCloseButton:hover {{
                color: white;
                background-color: #c74747;
            }}

            QPushButton#eWinCloseButton:pressed {{
                background-color: #9f3030;
            }}
        """.format(background, border, color, weight))


class EWinOverlay(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(EWinOverlay, self).__init__(parent, WINDOW_FLAGS)

        self.setObjectName("eWinOverlay")
        self.setAttribute(ATTRIBUTE_TRANSLUCENT, True)
        self.setAttribute(ATTRIBUTE_SHOW_WITHOUT_ACTIVATING, True)

        self.cards = []

        self.center_button = QtWidgets.QPushButton()
        self.center_button.setObjectName("eWinCenterButton")
        self.center_button.setCheckable(True)
        self.center_button.setFocusPolicy(
            enum_value(QtCore.Qt, "NoFocus", ("FocusPolicy",))
        )
        self.center_button.setChecked(
            eWin_windows.center_on_activate_enabled()
        )
        self.center_button.clicked.connect(self.toggle_centering)
        self.update_center_button()

        self.container = QtWidgets.QFrame()
        self.container.setObjectName("eWinContainer")
        self.container.setStyleSheet("""
            QFrame#eWinContainer {
                background-color: rgba(28, 28, 28, 235);
                border: 1px solid #666666;
                border-radius: 12px;
            }
        """)

        self.center_button.setStyleSheet("""
            QPushButton#eWinCenterButton {
                min-width: 150px;
                padding: 5px 10px;
                color: #dddddd;
                background-color: #353535;
                border: 1px solid #666666;
                border-radius: 5px;
                font-size: 11px;
            }

            QPushButton#eWinCenterButton:hover {
                color: white;
                border-color: #888888;
                background-color: #454545;
            }

            QPushButton#eWinCenterButton:checked {
                color: white;
                border-color: #78b7ff;
                background-color: #3d6fa8;
            }
        """)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(14, 10, 14, 0)
        header_layout.addStretch()
        header_layout.addWidget(self.center_button)

        self.card_layout = QtWidgets.QHBoxLayout()
        self.card_layout.setContentsMargins(14, 10, 14, 14)
        self.card_layout.setSpacing(10)

        container_layout = QtWidgets.QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addLayout(header_layout)
        container_layout.addLayout(self.card_layout)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(SCROLLBAR_OFF)
        self.scroll_area.setVerticalScrollBarPolicy(SCROLLBAR_OFF)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area.setWidget(self.container)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area)

    def show_session(self):
        self.update_center_button()
        self.rebuild()
        self.update_selection()
        self.resize_overlay()
        self.center_on_maya()
        self.show()
        self.raise_()

    def rebuild(self):
        self.clear_cards()

        for candidate in eWin_windows.get_candidates():
            card = WindowCard(candidate)
            card.close_requested.connect(self.close_candidate)
            self.cards.append(card)
            self.card_layout.addWidget(card)

    def update_selection(self):
        selected_index = eWin_windows.get_selected_index()

        for index, card in enumerate(self.cards):
            card.set_selected(index == selected_index)

        if 0 <= selected_index < len(self.cards):
            self.scroll_area.ensureWidgetVisible(
                self.cards[selected_index],
                24,
                0,
            )

    def close_candidate(self, candidate):
        eWin_windows.close_candidate(candidate)

        if not eWin_windows.get_candidates():
            log("No candidate windows remain.")
            self.close_session()
            return

        self.rebuild()
        self.resize_overlay()
        self.center_on_maya()
        self.update_selection()

    def resize_overlay(self):
        card_count = max(1, len(self.cards))
        content_width = card_count * 210 + max(0, card_count - 1) * 10 + 28

        main_window = eWin_windows.get_maya_main_window()
        maximum_width = 1100

        if main_window:
            maximum_width = max(300, main_window.width() - 100)

        self.resize(min(content_width, maximum_width), 158)

    def center_on_maya(self):
        main_window = eWin_windows.get_maya_main_window()

        if not main_window:
            return

        geometry = self.frameGeometry()
        geometry.moveCenter(main_window.frameGeometry().center())
        self.move(geometry.topLeft())

    def close_session(self):
        self.hide()
        self.clear_cards()

    def clear_cards(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()

            if widget:
                widget.deleteLater()

        self.cards = []

    def toggle_centering(self, enabled):
        eWin_windows.set_center_on_activate(enabled)
        self.update_center_button()

    def update_center_button(self):
        enabled = eWin_windows.center_on_activate_enabled()
        self.center_button.setChecked(enabled)

        if enabled:
            self.center_button.setText("Center Window: ON")
            self.center_button.setToolTip(
                "Selected windows will be moved to the center."
            )
        else:
            self.center_button.setText("Center Window: OFF")
            self.center_button.setToolTip(
                "Selected windows will keep their existing position."
            )


_OVERLAY = None


def get_overlay():
    global _OVERLAY

    if _OVERLAY is None:
        _OVERLAY = EWinOverlay(parent=eWin_windows.get_maya_main_window())

    return _OVERLAY


def show_overlay():
    get_overlay().show_session()


def update_overlay():
    if _OVERLAY and _OVERLAY.isVisible():
        _OVERLAY.update_selection()


def hide_overlay():
    if _OVERLAY:
        _OVERLAY.close_session()


def destroy_overlay():
    global _OVERLAY

    if _OVERLAY:
        _OVERLAY.hide()
        _OVERLAY.deleteLater()
        _OVERLAY = None