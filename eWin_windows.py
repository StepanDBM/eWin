# eWin_windows.py

try:
    from PySide6 import QtCore, QtWidgets
    from shiboken6 import getCppPointer, isValid, wrapInstance
except ImportError:
    from PySide2 import QtCore, QtWidgets
    from shiboken2 import getCppPointer, isValid, wrapInstance

from maya import OpenMayaUI as omui
from maya import cmds


EWIN_OBJECT_PREFIX = "eWin"
_CENTER_ON_ACTIVATE = False


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

    def __init__(
        self,
        widget,
        title=None,
        workspace_control=None,
        source="qt",
    ):
        self.widget = widget
        self.custom_title = title
        self.workspace_control = workspace_control
        self.source = source

    @property
    def title(self):
        if self.custom_title:
            return self.custom_title.strip()

        if not self.is_valid():
            return "<Destroyed Window>"

        return self.widget.windowTitle().strip()

    @property
    def object_name(self):
        if not self.is_valid():
            return ""

        return self.widget.objectName()

    @property
    def identity(self):
        if self.is_valid():
            try:
                return ("qt", int(getCppPointer(self.widget)[0]))
            except (IndexError, RuntimeError, TypeError):
                pass

        if self.workspace_control:
            return ("workspaceControl", self.workspace_control)

        return ("python", id(self))

    @property
    def visible(self):
        if self.workspace_control_exists():
            try:
                return cmds.workspaceControl(
                    self.workspace_control,
                    query=True,
                    visible=True,
                )
            except RuntimeError:
                pass

        return self.is_valid() and self.widget.isVisible()

    @property
    def minimized(self):
        if not self.is_valid():
            return False

        try:
            return bool(self.widget.windowState() & WINDOW_MINIMIZED)
        except RuntimeError:
            return False

    @property
    def active(self):
        return self.is_valid() and self.widget.isActiveWindow()

    @property
    def is_workspace_control(self):
        return bool(self.workspace_control)

    def is_valid(self):
        try:
            if self.widget is not None and isValid(self.widget):
                return True
        except RuntimeError:
            pass

        return self.workspace_control_exists()

    def workspace_control_exists(self):
        if not self.workspace_control:
            return False

        try:
            return cmds.workspaceControl(
                self.workspace_control,
                query=True,
                exists=True,
            )
        except RuntimeError:
            return False

    def refresh_widget(self):
        if not self.workspace_control_exists():
            return self.widget

        widget = get_workspace_control_widget(self.workspace_control)

        if widget is not None:
            self.widget = widget

        return self.widget

    def description(self):
        return (
            "{} | source={} | workspaceControl={} | "
            "visible={} | minimized={} | active={}"
        ).format(
            self.title,
            self.source,
            self.workspace_control or "None",
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

        selected = self.selected

        if selected:
            log("SELECTED: {}".format(selected.title))

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
        selected_identity = None

        if 0 <= self.selected_index < len(self.candidates):
            selected_identity = self.candidates[self.selected_index].identity

        self.candidates = [
            candidate
            for candidate in self.candidates
            if candidate.is_valid()
        ]

        if not self.candidates:
            self.selected_index = -1
            return

        if selected_identity:
            for index, candidate in enumerate(self.candidates):
                if candidate.identity == selected_identity:
                    self.selected_index = index
                    return

        self.selected_index %= len(self.candidates)


_SESSION = WindowSession()


def discover_windows():
    qt_candidates = discover_qt_windows()
    workspace_candidates = discover_workspace_windows()

    candidates_by_identity = {}

    for candidate in qt_candidates:
        candidates_by_identity[candidate.identity] = candidate

    for candidate in workspace_candidates:
        identity = candidate.identity
        existing = candidates_by_identity.get(identity)

        if existing:
            existing.workspace_control = candidate.workspace_control
            existing.source = "qt+workspaceControl"

            if not existing.title and candidate.title:
                existing.custom_title = candidate.title
        else:
            candidates_by_identity[identity] = candidate

    candidates = list(candidates_by_identity.values())
    return order_candidates(candidates)


def discover_qt_windows():
    app = QtWidgets.QApplication.instance()

    if app is None:
        log("ERROR: QApplication instance was not found.")
        return []

    return [
        WindowCandidate(widget=widget, source="qt")
        for widget in app.topLevelWidgets()
        if is_candidate_qt_window(widget)
    ]


def discover_workspace_windows():
    candidates = []

    for control in cmds.lsUI(workspaceControls=True) or []:
        try:
            if not cmds.workspaceControl(control, query=True, exists=True):
                continue

            floating = cmds.workspaceControl(
                control,
                query=True,
                floating=True,
            )

            visible = cmds.workspaceControl(
                control,
                query=True,
                visible=True,
            )

            if not floating or not visible:
                continue

            label = cmds.workspaceControl(
                control,
                query=True,
                label=True,
            )

            widget = get_workspace_control_widget(control)

            if widget is None:
                log(
                    "WORKSPACE: Could not find Qt host for '{}'.".format(
                        control
                    )
                )
                continue

            if widget is get_maya_main_window():
                continue

            candidates.append(
                WindowCandidate(
                    widget=widget,
                    title=label or widget.windowTitle() or control,
                    workspace_control=control,
                    source="workspaceControl",
                )
            )

        except RuntimeError as error:
            log(
                "WORKSPACE: Could not inspect '{}': {}".format(
                    control,
                    error,
                )
            )

    return candidates


def get_workspace_control_widget(control):
    try:
        pointer = omui.MQtUtil.findControl(control)

        if not pointer:
            pointer = omui.MQtUtil.findLayout(control)

        if not pointer:
            return None

        widget = wrapInstance(int(pointer), QtWidgets.QWidget)

        if widget is None or not isValid(widget):
            return None

        host = widget.window()

        if host is not None and isValid(host):
            return host

        return widget

    except (RuntimeError, TypeError, ValueError):
        return None


def order_candidates(candidates):
    if not candidates:
        return []

    active_window = QtWidgets.QApplication.activeWindow()
    active_candidate = None
    remaining = []

    for candidate in candidates:
        if active_candidate is None and candidate_matches_active_window(
            candidate,
            active_window,
        ):
            active_candidate = candidate
        else:
            remaining.append(candidate)

    remaining.sort(key=lambda candidate: candidate.title.lower())

    if active_candidate:
        return [active_candidate] + remaining

    return remaining


def candidate_matches_active_window(candidate, active_window):
    if not candidate.is_valid():
        return False

    if candidate.active:
        return True

    if active_window is None or not isValid(active_window):
        return False

    try:
        candidate_pointer = int(getCppPointer(candidate.widget)[0])
        active_pointer = int(getCppPointer(active_window.window())[0])
        return candidate_pointer == active_pointer
    except (IndexError, RuntimeError, TypeError):
        return False


def is_candidate_qt_window(widget):
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
    pointer = omui.MQtUtil.mainWindow()

    if not pointer:
        return None

    try:
        return wrapInstance(int(pointer), QtWidgets.QWidget)
    except (RuntimeError, TypeError, ValueError):
        return None


def activate_candidate(candidate):
    if not candidate or not candidate.is_valid():
        log("ACTIVATE: Selected window is no longer valid.")
        return False

    title = candidate.title

    try:
        if candidate.workspace_control_exists():
            cmds.workspaceControl(
                candidate.workspace_control,
                edit=True,
                restore=True,
            )

            candidate.refresh_widget()
            log(
                "RESTORE: Workspace control '{}' restored.".format(
                    candidate.workspace_control
                )
            )

        widget = candidate.widget

        if widget is None or not isValid(widget):
            log("ACTIVATE: '{}' has no valid Qt host.".format(title))
            return False

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

    except RuntimeError as error:
        log("ACTIVATE: Could not activate '{}': {}".format(title, error))
        return False


def center_window(widget):
    if widget is None or not isValid(widget):
        return False

    maya_window = get_maya_main_window()

    if maya_window and maya_window.screen():
        available_geometry = maya_window.screen().availableGeometry()
        target_center = maya_window.frameGeometry().center()
    else:
        screen = QtWidgets.QApplication.screenAt(
            widget.frameGeometry().center()
        )

        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()

        if screen is None:
            return False

        available_geometry = screen.availableGeometry()
        target_center = available_geometry.center()

    geometry = widget.frameGeometry()
    geometry.moveCenter(target_center)

    maximum_x = available_geometry.right() - geometry.width() + 1
    maximum_y = available_geometry.bottom() - geometry.height() + 1

    x = max(
        available_geometry.left(),
        min(geometry.left(), maximum_x),
    )

    y = max(
        available_geometry.top(),
        min(geometry.top(), maximum_y),
    )

    widget.move(x, y)
    return True

def minimize_candidate(candidate):
    if not candidate or not candidate.is_valid():
        return False

    candidate.refresh_widget()
    widget = candidate.widget

    if widget is None or not isValid(widget):
        log("MINIMIZE: '{}' has no valid Qt host.".format(candidate.title))
        return False

    try:
        widget.showMinimized()
        log("MINIMIZE: '{}' minimized.".format(candidate.title))
        return True
    except RuntimeError as error:
        log("MINIMIZE: Could not minimize '{}': {}".format(
            candidate.title, error
        ))
        return False

def isolate_candidate(candidate, candidates=None):
    if not candidate or not candidate.is_valid():
        log("ISOLATE: Selected window is no longer valid.")
        return False

    if candidates is None:
        candidates = list(_SESSION.candidates)
    else:
        candidates = list(candidates)

    target_identity = candidate.identity
    minimized_count = 0

    for other in candidates:
        if other.identity == target_identity:
            continue

        if minimize_candidate(other):
            minimized_count += 1

    log(
        "ISOLATE: Kept '{}' and minimized {} other window(s).".format(
            candidate.title, minimized_count
        )
    )

    return activate_candidate(candidate)

def close_candidate(candidate):
    if not candidate:
        log("CLOSE: No window candidate was provided.")
        return False

    title = candidate.title

    try:
        if candidate.workspace_control_exists():
            cmds.workspaceControl(
                candidate.workspace_control,
                edit=True,
                close=True,
            )

            log(
                "CLOSE: Workspace control '{}' closed.".format(title)
            )

            _SESSION.remove_candidate(candidate)
            return True

        if not candidate.is_valid():
            log("CLOSE: '{}' is no longer valid.".format(title))
            _SESSION.remove_candidate(candidate)
            return False

        accepted = candidate.widget.close()

        if accepted:
            log("CLOSE: '{}' closed.".format(title))
            _SESSION.remove_candidate(candidate)
            return True

        log("CLOSE: '{}' rejected the close request.".format(title))
        return False

    except RuntimeError as error:
        log("CLOSE: Could not close '{}': {}".format(title, error))

        if not candidate.is_valid():
            _SESSION.remove_candidate(candidate)

        return False

def close_all_candidates():
    candidates = list(_SESSION.candidates)

    if not candidates:
        log("CLOSE ALL: No candidate windows found.")
        return 0

    closed_count = 0

    for candidate in candidates:
        if close_candidate(candidate):
            closed_count += 1

    log("CLOSE ALL: Closed {} window(s).".format(closed_count))
    return closed_count


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