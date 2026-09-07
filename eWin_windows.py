# eWin_windows.py

try:
    from PySide6 import QtCore, QtWidgets
    from shiboken6 import isValid
except ImportError:
    from PySide2 import QtCore, QtWidgets
    from shiboken2 import isValid


EWIN_OBJECT_PREFIX = "eWin"

_CENTER_ON_ACTIVATE = True

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


WINDOW_MINIMIZED = enum_value(
    QtCore.Qt,
    "WindowMinimized",
    ("WindowState",),
)

EXCLUDED_WINDOW_TYPES = {
    enum_value(QtCore.Qt, "Popup", ("WindowType",)),
    enum_value(QtCore.Qt, "ToolTip", ("WindowType",)),
    enum_value(QtCore.Qt, "SplashScreen", ("WindowType",)),
}


class WindowCandidate:

    def __init__(self, widget):
        self.widget = widget

    @property
    def title(self):
        if not self.is_valid():
            return "<Destroyed Window>"

        return self.widget.windowTitle().strip()

    @property
    def object_name(self):
        if not self.is_valid():
            return ""

        return self.widget.objectName()

    @property
    def visible(self):
        return self.is_valid() and self.widget.isVisible()

    @property
    def minimized(self):
        if not self.is_valid():
            return False

        return bool(self.widget.windowState() & WINDOW_MINIMIZED)

    @property
    def active(self):
        return self.is_valid() and self.widget.isActiveWindow()

    def is_valid(self):
        try:
            return self.widget is not None and isValid(self.widget)
        except RuntimeError:
            return False

    def description(self):
        return "{} | visible={} | minimized={} | active={}".format(
            self.title,
            self.visible,
            self.minimized,
            self.active,
        )


class WindowSession:

    def __init__(self):
        self.candidates = []
        self.selected_index = -1

    def begin(self, direction=1):
        self.candidates = discover_windows()
        self.selected_index = -1

        log("Discovered {} candidate window(s).".format(len(self.candidates)))

        for index, candidate in enumerate(self.candidates):
            log("{}: {}".format(index, candidate.description()))

        if not self.candidates:
            log("SELECTED: No candidate windows found.")
            return False

        if len(self.candidates) == 1:
            self.selected_index = 0
        elif direction < 0:
            self.selected_index = len(self.candidates) - 1
        else:
            self.selected_index = 1

        log("CURRENT: {}".format(self.candidates[0].title))
        log("SELECTED: {}".format(self.selected.title))
        return True

    @property
    def selected(self):
        self._remove_invalid_candidates()

        if not self.candidates:
            self.selected_index = -1
            return None

        self.selected_index %= len(self.candidates)
        return self.candidates[self.selected_index]

    def select_next(self):
        if not self._prepare_selection():
            return None

        self.selected_index = (self.selected_index + 1) % len(self.candidates)
        candidate = self.selected

        log("SELECTED NEXT: {}".format(candidate.title))
        return candidate

    def select_previous(self):
        if not self._prepare_selection():
            return None

        self.selected_index = (self.selected_index - 1) % len(self.candidates)
        candidate = self.selected

        log("SELECTED PREVIOUS: {}".format(candidate.title))
        return candidate

    def accept(self):
        candidate = self.selected

        if candidate:
            log("ACCEPT: Activating '{}'.".format(candidate.title))
        else:
            log("ACCEPT: No valid window selected.")

        return candidate

    def cancel(self):
        log("CANCEL: Window selection discarded.")

    def remove_candidate(self, candidate):
        if candidate not in self.candidates:
            return False

        removed_index = self.candidates.index(candidate)
        self.candidates.remove(candidate)

        if not self.candidates:
            self.selected_index = -1
            return True

        if removed_index < self.selected_index:
            self.selected_index -= 1
        elif self.selected_index >= len(self.candidates):
            self.selected_index = 0

        log("SELECTED: {}".format(self.selected.title))
        return True

    def clear(self):
        self.candidates = []
        self.selected_index = -1

    def _prepare_selection(self):
        self._remove_invalid_candidates()

        if not self.candidates:
            self.selected_index = -1
            log("No valid candidate windows remain.")
            return False

        if self.selected_index < 0:
            self.selected_index = 0

        return True

    def _remove_invalid_candidates(self):
        selected_widget = None

        if 0 <= self.selected_index < len(self.candidates):
            selected_widget = self.candidates[self.selected_index].widget

        self.candidates = [
            candidate for candidate in self.candidates if candidate.is_valid()
        ]

        if not self.candidates:
            self.selected_index = -1
            return

        if selected_widget:
            for index, candidate in enumerate(self.candidates):
                if candidate.widget is selected_widget:
                    self.selected_index = index
                    return

        self.selected_index %= len(self.candidates)


_SESSION = WindowSession()


def discover_windows():
    app = QtWidgets.QApplication.instance()

    if app is None:
        log("ERROR: QApplication instance was not found.")
        return []

    candidates = [
        WindowCandidate(widget)
        for widget in app.topLevelWidgets()
        if is_candidate_window(widget)
    ]

    active_candidate = None
    other_candidates = []

    for candidate in candidates:
        if candidate.active and active_candidate is None:
            active_candidate = candidate
        else:
            other_candidates.append(candidate)

    other_candidates.sort(key=lambda candidate: candidate.title.lower())

    if active_candidate:
        return [active_candidate] + other_candidates

    return other_candidates


def is_candidate_window(widget):
    try:
        if widget is None or not isValid(widget) or not widget.isWindow():
            return False

        title = widget.windowTitle().strip()
        object_name = widget.objectName()

        if not title:
            return False

        if object_name.startswith(EWIN_OBJECT_PREFIX):
            return False

        if widget.windowType() in EXCLUDED_WINDOW_TYPES:
            return False

        if widget is get_maya_main_window():
            return False

        if not widget.isVisible() and not widget.isMinimized():
            return False

        return True

    except RuntimeError:
        return False


def get_maya_main_window():
    app = QtWidgets.QApplication.instance()

    if app is None:
        return None

    for widget in app.topLevelWidgets():
        try:
            if isValid(widget) and widget.objectName() == "MayaWindow":
                return widget
        except RuntimeError:
            continue

    return None


def activate_candidate(candidate):
    if not candidate or not candidate.is_valid():
        log("ACTIVATE: Selected window is no longer valid.")
        return False

    widget = candidate.widget
    title = candidate.title

    try:
        if widget.isMinimized():
            widget.showNormal()
            log("RESTORE: '{}' was un-minimized.".format(title))
        elif not widget.isVisible():
            widget.show()

        if center_on_activate_enabled():
            center_window(widget)
            log("CENTER: '{}' moved into the Maya workspace.".format(title))

        widget.raise_()
        widget.activateWindow()

        QtCore.QTimer.singleShot(0, widget.raise_)
        QtCore.QTimer.singleShot(0, widget.activateWindow)

        log("FOCUS: '{}' raised and activated.".format(title))
        return True

    except RuntimeError:
        log("ACTIVATE: '{}' was destroyed during activation.".format(title))
        return False


def center_window(widget):
    if widget is None or not isValid(widget):
        return False

    maya_window = get_maya_main_window()

    if maya_window:
        available_geometry = maya_window.screen().availableGeometry()
        target_center = maya_window.frameGeometry().center()
    else:
        screen = QtWidgets.QApplication.screenAt(widget.frameGeometry().center())

        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()

        if screen is None:
            return False

        available_geometry = screen.availableGeometry()
        target_center = available_geometry.center()

    geometry = widget.frameGeometry()
    geometry.moveCenter(target_center)

    x = max(
        available_geometry.left(),
        min(geometry.left(), available_geometry.right() - geometry.width() + 1),
    )

    y = max(
        available_geometry.top(),
        min(geometry.top(), available_geometry.bottom() - geometry.height() + 1),
    )

    widget.move(x, y)
    return True


def close_candidate(candidate):
    if not candidate or not candidate.is_valid():
        log("CLOSE: Window is no longer valid.")
        _SESSION.remove_candidate(candidate)
        return False

    title = candidate.title

    try:
        accepted = candidate.widget.close()

        if accepted:
            log("CLOSE: '{}' closed.".format(title))
            _SESSION.remove_candidate(candidate)
            return True

        log("CLOSE: '{}' rejected the close request.".format(title))
        return False

    except RuntimeError:
        log("CLOSE: '{}' was destroyed during closing.".format(title))
        _SESSION.remove_candidate(candidate)
        return False


def begin_session(direction=1):
    return _SESSION.begin(direction)


def select_next():
    return _SESSION.select_next()


def select_previous():
    return _SESSION.select_previous()


def accept_session():
    return _SESSION.accept()


def cancel_session():
    _SESSION.cancel()


def clear_session():
    _SESSION.clear()


def get_candidates():
    return list(_SESSION.candidates)


def get_selected_candidate():
    return _SESSION.selected


def get_selected_index():
    return _SESSION.selected_index

def center_on_activate_enabled():
    return _CENTER_ON_ACTIVATE


def set_center_on_activate(enabled):
    global _CENTER_ON_ACTIVATE

    _CENTER_ON_ACTIVATE = bool(enabled)
    state = "enabled" if _CENTER_ON_ACTIVATE else "disabled"

    log("Center selected window {}.".format(state))
    return _CENTER_ON_ACTIVATE


def toggle_center_on_activate():
    return set_center_on_activate(not _CENTER_ON_ACTIVATE)