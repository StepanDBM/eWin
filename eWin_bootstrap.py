# eWin_bootstrap.py

import importlib

import eWin_launcher


eWin_launcher.uninstall()

MODULE_NAMES = [
    "eWin_windows",
    "eWin_overlay",
    "eWin_listener",
    "eWin_launcher",
]

modules = {}

for module_name in MODULE_NAMES:
    module = importlib.import_module(module_name)
    modules[module_name] = importlib.reload(module)

modules["eWin_launcher"].install()