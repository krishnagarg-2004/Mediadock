"""Application entry point for MediaDock."""

import sys
from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def main() -> int:
    """Initialize QApplication, create main widget window, and start event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName("MediaDock")
    app.setOrganizationName("KrishnaOS")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
