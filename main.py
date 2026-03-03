#!/usr/bin/env python3
"""
R0MM
A tool for organizing ROM collections using DAT files.

Usage:
    PySide6:  python main.py           (default)
    PySide6:  python main.py --pyside6
    CLI Mode: python main.py --dat <file> --roms <folder> --output <folder>

For CLI help: python main.py --help
"""

import sys
import os

# Add package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rommanager import __version__
from rommanager.monitor import setup_runtime_monitor, monitor_action
from rommanager.settings import load_settings, apply_runtime_settings


def main():
    """Main entry point"""
    logger = setup_runtime_monitor()
    monitor_action("startup: main.py entry", logger=logger)
    apply_runtime_settings(load_settings())
    archived_flags = [flag for flag in ("--web", "--gui", "--flet") if flag in sys.argv]
    if archived_flags:
        monitor_action(f"mode rejected: archived frontend {' '.join(archived_flags)}", logger=logger)
        print("This checkout now targets the PySide6 desktop release only.")
        print("Archived frontends were moved to _OLD/.")
        print("Use: py -3.14 -m main --pyside6")
        sys.exit(1)

    # Check for --pyside6 flag or default desktop launch
    if '--pyside6' in sys.argv or len(sys.argv) == 1:
        monitor_action('mode selected: pyside6', logger=logger)
        try:
            from rommanager.gui_pyside6 import run_pyside6_gui
            sys.exit(run_pyside6_gui())
        except ImportError as e:
            print("Error: PySide6 is required for the desktop interface")
            print("Install it with: pip install PySide6")
            print(f"\nDetails: {e}")
            sys.exit(1)
        return

    if len(sys.argv) > 1 and sys.argv[1] not in ('-h', '--help'):
        monitor_action('mode selected: cli', logger=logger)
        # CLI mode
        from rommanager.cli import run_cli
        sys.exit(run_cli())
    else:
        # Show help
        from rommanager.cli import run_cli
        sys.exit(run_cli())


if __name__ == '__main__':
    main()
