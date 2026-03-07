import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk

from .app import TaskManagerApplication
from .debug import debug


def main():
    debug.log_event("MAIN", "=== STARTING TODO LIST APPLICATION ===")
    debug.log_event("MAIN", f"Python version: {sys.version}")
    debug.log_event("MAIN", f"GTK version: {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}")

    try:
        app = TaskManagerApplication()
        result = app.run(sys.argv)
        debug.log_event("MAIN", f"Application finished with code: {result}")
        debug.dump_recent_events(100)
        return result
    except Exception as exc:
        debug.log_event("MAIN", f"CRITICAL ERROR in main: {exc}", stack_info=True)
        debug.dump_recent_events(50)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
