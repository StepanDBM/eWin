# eWin_startup.py

import sys

from maya import utils


TOOL_PATH = r"E:\Work\3D\my_3D\KANEDA\Projects\Scripting\eWin_SDBM"


def log(message):
    print("[eWin] {}".format(message))


def install():
    if TOOL_PATH not in sys.path:
        sys.path.insert(0, TOOL_PATH)

    try:
        import eWin_launcher

        if eWin_launcher.is_installed():
            log("Startup listener is already installed.")
            return True

        if eWin_launcher.install():
            log("Startup installation completed.")
            return True

        log("ERROR: Startup installation failed.")
        return False

    except Exception as error:
        log("ERROR: Startup installation failed: {}".format(error))
        return False


def install_deferred():
    utils.executeDeferred(install)