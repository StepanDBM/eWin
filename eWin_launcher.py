# eWin_launcher.py

try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets

import eWin_listener
import eWin_overlay
import eWin_windows


_LISTENER = None


def log(message):
    print("[eWin] {}".format(message))


def install():
    global _LISTENER

    app = QtWidgets.QApplication.instance()

    if app is None:
        log("ERROR: QApplication instance was not found.")
        return False

    uninstall()

    _LISTENER = eWin_listener.EWinListener(parent=app)
    app.installEventFilter(_LISTENER)

    log("Qt application event listener installed.")
    log("Window discovery and visual overlay are enabled.")
    log("Accept currently logs the selected window without activating it.")

    return True


def uninstall():
    global _LISTENER

    if _LISTENER is None:
        eWin_overlay.destroy_overlay()
        eWin_windows.clear_session()
        return False

    app = QtWidgets.QApplication.instance()

    if app is not None:
        app.removeEventFilter(_LISTENER)

    _LISTENER.reset()
    _LISTENER.deleteLater()
    _LISTENER = None

    eWin_overlay.destroy_overlay()
    eWin_windows.clear_session()

    log("Previous Qt application event listener removed.")
    return True


def reinstall():
    log("Reinstalling listener.")
    return install()


def is_installed():
    return _LISTENER is not None


def listener():
    return _LISTENER