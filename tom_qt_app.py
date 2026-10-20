"""Launch TOM's PySide6 desktop interface (the Tkinter app, tom_desktop_app.py, stays available)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tom_core.interfaces.qt_app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
