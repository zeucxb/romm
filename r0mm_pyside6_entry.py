from __future__ import annotations

from rommanager.gui_pyside6 import run_pyside6_gui
from rommanager.monitor import monitor_action, setup_runtime_monitor
from rommanager.settings import apply_runtime_settings, load_settings


def main() -> int:
    logger = setup_runtime_monitor()
    monitor_action("startup: r0mm_pyside6_entry", logger=logger)
    apply_runtime_settings(load_settings())
    return run_pyside6_gui()


if __name__ == "__main__":
    raise SystemExit(main())
