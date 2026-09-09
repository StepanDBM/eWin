# eWin_listener.py

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

import eWin_overlay
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


KEY_TAB = enum_value(QtCore.Qt, "Key_Tab", ("Key",))
KEY_BACKTAB = enum_value(QtCore.Qt, "Key_Backtab", ("Key",))
KEY_ESCAPE = enum_value(QtCore.Qt, "Key_Escape", ("Key",))
KEY_CONTROL = enum_value(QtCore.Qt, "Key_Control", ("Key",))

# Search bar controls
KEY_F = enum_value(QtCore.Qt, "Key_F", ("Key",))
KEY_ENTER = enum_value(QtCore.Qt, "Key_Enter", ("Key",))
KEY_RETURN = enum_value(QtCore.Qt, "Key_Return", ("Key",))

# ISOLATE WITH I (isolate) or X (extract),
# CLOSE ALL WITH C (close),
# MINIMIZE ALL WITH U (unsee) or Q (quit),
# OPEN ALL WITH O (open) or E (expand)
KEY_I = enum_value(QtCore.Qt, "Key_I", ("Key",))
KEY_X = enum_value(QtCore.Qt, "Key_X", ("Key",))
KEY_C = enum_value(QtCore.Qt, "Key_C", ("Key",))

KEY_U = enum_value(QtCore.Qt, "Key_U", ("Key",))
KEY_Q = enum_value(QtCore.Qt, "Key_Q", ("Key",))
KEY_O = enum_value(QtCore.Qt, "Key_O", ("Key",))
KEY_E = enum_value(QtCore.Qt, "Key_E", ("Key",))

# W-A-S-D + UP-DOWN-LEFT-RIGHT miniWindow user Movement
KEY_W = enum_value(QtCore.Qt, "Key_W", ("Key",))
KEY_A = enum_value(QtCore.Qt, "Key_A", ("Key",))
KEY_S = enum_value(QtCore.Qt, "Key_S", ("Key",))
KEY_D = enum_value(QtCore.Qt, "Key_D", ("Key",))

KEY_UP = enum_value(QtCore.Qt, "Key_Up", ("Key",))
KEY_LEFT = enum_value(QtCore.Qt, "Key_Left", ("Key",))
KEY_DOWN = enum_value(QtCore.Qt, "Key_Down", ("Key",))
KEY_RIGHT = enum_value(QtCore.Qt, "Key_Right", ("Key",))

CONTROL_MODIFIER = enum_value(
    QtCore.Qt,
    "ControlModifier",
    ("KeyboardModifier",),
)

SHIFT_MODIFIER = enum_value(
    QtCore.Qt,
    "ShiftModifier",
    ("KeyboardModifier",),
)

KEY_PRESS = enum_value(QtCore.QEvent, "KeyPress", ("Type",))
KEY_RELEASE = enum_value(QtCore.QEvent, "KeyRelease", ("Type",))


class EWinListener(QtCore.QObject):

    STATE_IDLE = 0
    STATE_ACTIVE = 1
    STATE_SEARCH = 2
    STATE_WAITING_FOR_CTRL_RELEASE = 3

    def __init__(self, parent=None):
        super(EWinListener, self).__init__(parent)

        self.state = self.STATE_IDLE

        overlay = eWin_overlay.get_overlay()
        overlay.candidate_activated.connect(self._accept_candidate)
        overlay.candidate_isolated.connect(self._isolate_candidate)

        log("Listener created.")

    def eventFilter(self, watched, event):
        event_type = event.type()

        if event_type not in (KEY_PRESS, KEY_RELEASE):
            return False

        if event.isAutoRepeat():
            return self._handle_auto_repeat(event)

        if event_type == KEY_PRESS:
            return self._handle_key_press(event.key(), event.modifiers())

        return self._handle_key_release(event.key())

    def _handle_key_press(self, key, modifiers):
        ctrl_pressed = bool(modifiers & CONTROL_MODIFIER)
        shift_pressed = bool(modifiers & SHIFT_MODIFIER)

        if self.state == self.STATE_WAITING_FOR_CTRL_RELEASE:
            return key in (KEY_TAB, KEY_BACKTAB, KEY_ESCAPE)

        if self.state == self.STATE_IDLE:
            if not ctrl_pressed:
                return False

            if key == KEY_BACKTAB or (key == KEY_TAB and shift_pressed):
                self.state = self.STATE_ACTIVE
                log("OPEN PREVIOUS: Ctrl+Shift+Tab detected.")

                if eWin_windows.begin_session(direction=-1):
                    eWin_overlay.show_overlay()
                else:
                    self.state = self.STATE_WAITING_FOR_CTRL_RELEASE

                return True

            if key == KEY_TAB:
                self.state = self.STATE_ACTIVE
                log("OPEN NEXT: Ctrl+Tab detected.")

                if eWin_windows.begin_session(direction=1):
                    eWin_overlay.show_overlay()
                else:
                    self.state = self.STATE_WAITING_FOR_CTRL_RELEASE

                return True

            return False

        if self.state == self.STATE_ACTIVE:
            if key == KEY_ESCAPE:
                self.state = self.STATE_WAITING_FOR_CTRL_RELEASE
                log("CANCEL: Escape detected. Waiting for Ctrl release.")

                eWin_windows.cancel_session()
                eWin_overlay.hide_overlay()
                return True

            if ctrl_pressed and key == KEY_F:
                self.state = self.STATE_SEARCH
                log("SEARCH: Search mode activated.")
                eWin_overlay.focus_search()
                return True

            if ctrl_pressed and key in (KEY_I, KEY_X):
                candidate = eWin_windows.get_selected_candidate()

                if candidate:
                    self._isolate_candidate(candidate)

                return True

            if key in (KEY_Q, KEY_U):
                self._minimize_all_candidates()
                return True
            
            if key in (KEY_E, KEY_O):
                self._open_all_candidates()
                return True
            
            if ctrl_pressed and key == KEY_C:
                self._close_all_candidates()
                return True

            if key in (KEY_W, KEY_UP):
                log("MOVE: Up.")
                eWin_windows.move_up()
                eWin_overlay.update_overlay()
                return True

            if key in (KEY_A, KEY_LEFT):
                log("MOVE: Left.")
                eWin_windows.move_left()
                eWin_overlay.update_overlay()
                return True

            if key in (KEY_S, KEY_DOWN):
                log("MOVE: Down.")
                eWin_windows.move_down()
                eWin_overlay.update_overlay()
                return True

            if key in (KEY_D, KEY_RIGHT):
                log("MOVE: Right.")
                eWin_windows.move_right()
                eWin_overlay.update_overlay()
                return True

            if key == KEY_BACKTAB or (key == KEY_TAB and shift_pressed):
                log("PREVIOUS: Ctrl+Shift+Tab detected.")
                eWin_windows.select_previous()
                eWin_overlay.update_overlay()
                return True

            if key == KEY_TAB:
                log("NEXT: Ctrl+Tab detected.")
                eWin_windows.select_next()
                eWin_overlay.update_overlay()
                return True

        return False

    def _isolate_candidate(self, candidate):
        if self.state != self.STATE_ACTIVE:
            return

        candidates = eWin_windows.get_candidates()

        log("ISOLATE: Keeping '{}' open.".format(candidate.title))
        self._finish_interaction()

        QtCore.QTimer.singleShot(
            0,
            lambda candidate=candidate, candidates=candidates:
                eWin_windows.isolate_candidate(candidate, candidates),
        )

    def _accept_candidate(self, candidate):
        if self.state not in (self.STATE_ACTIVE, self.STATE_SEARCH):
            return

        log("ACCEPT: Activating '{}'.".format(candidate.title))

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        ctrl_held = bool(modifiers & CONTROL_MODIFIER)

        if ctrl_held:
            self.state = self.STATE_WAITING_FOR_CTRL_RELEASE
        else:
            self.state = self.STATE_IDLE

        eWin_overlay.hide_overlay()
        eWin_windows.clear_session()

        QtCore.QTimer.singleShot(
            0,
            lambda candidate=candidate:
                eWin_windows.activate_candidate(candidate),
        )

    def _close_candidates(self, candidates):
        closed_count = 0

        for candidate in candidates:
            if eWin_windows.close_candidate(candidate):
                closed_count += 1

        log("CLOSE ALL: Closed {} window(s).".format(closed_count))

    def _open_all_candidates(self):
        if self.state != self.STATE_ACTIVE:
            return

        candidates = eWin_windows.get_candidates()

        log("OPEN ALL: Requested from overlay.")
        self._finish_interaction()

        QtCore.QTimer.singleShot(
            0,
            lambda candidates=candidates:
                eWin_windows.open_all_candidates(candidates),
        )

    def _minimize_all_candidates(self):
        if self.state != self.STATE_ACTIVE:
            return

        candidates = eWin_windows.get_candidates()

        log("MINIMIZE ALL: Requested from overlay.")
        self._finish_interaction()

        QtCore.QTimer.singleShot(
            0,
            lambda candidates=candidates:
                eWin_windows.minimize_all_candidates(candidates),
        )

    def _close_all_candidates(self):
        if self.state != self.STATE_ACTIVE:
            return

        log("CLOSE ALL: Requested from overlay.")
        candidates = eWin_windows.get_candidates()

        self._finish_interaction()

        QtCore.QTimer.singleShot(
            0,
            lambda candidates=candidates:
                self._close_candidates(candidates),
        )

    def _finish_interaction(self):
        self.state = self.STATE_WAITING_FOR_CTRL_RELEASE
        eWin_overlay.hide_overlay()
        eWin_windows.clear_session()

    def _handle_key_release(self, key):
        if key == KEY_CONTROL:
            if self.state == self.STATE_SEARCH:
                log("SEARCH: Ctrl released. Search mode remains active.")
                return True
            
            if self.state == self.STATE_ACTIVE:
                self.state = self.STATE_IDLE

                candidate = eWin_windows.accept_session()

                eWin_overlay.hide_overlay()
                eWin_windows.clear_session()

                if candidate:
                    QtCore.QTimer.singleShot(
                        0,
                        lambda candidate=candidate:
                            eWin_windows.activate_candidate(candidate),
                    )

                return True

            if self.state == self.STATE_WAITING_FOR_CTRL_RELEASE:
                self.state = self.STATE_IDLE
                eWin_overlay.hide_overlay()
                eWin_windows.clear_session()

                log("RESET: Ctrl released.")
                return True

            return False

        if self.state in (
            self.STATE_ACTIVE,
            self.STATE_WAITING_FOR_CTRL_RELEASE,
        ) and key in (
            KEY_TAB,
            KEY_BACKTAB,
            KEY_ESCAPE,
        ):
            return True

        return False

    def _handle_auto_repeat(self, event):
        if self.state == self.STATE_SEARCH:
            return False

        if self.state != self.STATE_ACTIVE:
            return False

        key = event.key()

        if key in (KEY_W, KEY_UP):
            eWin_windows.move_up()
            eWin_overlay.update_overlay()
            return True

        if key in (KEY_A, KEY_LEFT):
            eWin_windows.move_left()
            eWin_overlay.update_overlay()
            return True

        if key in (KEY_S, KEY_DOWN):
            eWin_windows.move_down()
            eWin_overlay.update_overlay()
            return True

        if key in (KEY_D, KEY_RIGHT):
            eWin_windows.move_right()
            eWin_overlay.update_overlay()
            return True

        return key in (
            KEY_TAB,
            KEY_BACKTAB,
            KEY_ESCAPE,
            KEY_I,
            KEY_X,
            KEY_C,
            KEY_O,
            KEY_U,
            KEY_F,
        )

    def reset(self):
        self.state = self.STATE_IDLE

        eWin_overlay.hide_overlay()
        eWin_windows.clear_session()

        log("Listener state reset.")