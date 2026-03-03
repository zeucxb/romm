"""Entry point for running as module: python -m rommanager"""

import sys

from .monitor import setup_runtime_monitor, monitor_action
from .settings import load_settings, apply_runtime_settings


def main():
    """Open the PySide6 desktop app for module execution."""
    logger = setup_runtime_monitor()
    monitor_action("startup: module entry", logger=logger)
    monitor_action("mode selected: pyside6 (forced for python -m rommanager)", logger=logger)
    apply_runtime_settings(load_settings())

    try:
        from .gui_pyside6 import run_pyside6_gui
        raise SystemExit(run_pyside6_gui())
    except ImportError as exc:
        print(f"PySide6 interface unavailable: {exc}")
        print("Use python main.py --help for CLI usage.")
        sys.exit(1)


if __name__ == '__main__':
    main()
