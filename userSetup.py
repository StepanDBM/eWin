# eWin startup

import sys

EWIN_PATH = r""

if EWIN_PATH not in sys.path:
    sys.path.insert(0, EWIN_PATH)

import eWin_startup

eWin_startup.install_deferred()