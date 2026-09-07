# eWin_listener.py

try:
    from PySide6 import QtCore
except ImportError:
    from PySide2 import QtCore

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
    STATE_WAITING_FOR_CTRL_RELEASE = 2

    def __init__(self, parent=None):
        super(EWinListener, self).__init__(parent)

        self.state = self.STATE_IDLE
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

    def _handle_key_release(self, key):
        if key == KEY_CONTROL:
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

                log("RESET: Ctrl released after cancellation.")
                return True

            return False

        if self.state != self.STATE_IDLE and key in (
            KEY_TAB,
            KEY_BACKTAB,
            KEY_ESCAPE,
        ):
            return True

        return False

    def _handle_auto_repeat(self, event):
        if self.state != self.STATE_ACTIVE:
            return False

        return event.key() in (KEY_TAB, KEY_BACKTAB, KEY_ESCAPE)

    def reset(self):
        self.state = self.STATE_IDLE

        eWin_overlay.hide_overlay()
        eWin_windows.clear_session()

        log("Listener state reset.")