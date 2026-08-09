"""Application entry point for MediaDock."""

import sys
from PySide6.QtWidgets import QApplication

from src.media.gsmtc_provider import GSMTCProvider
from src.core.media_core import MediaCore
from src.ui.main_window import MainWindow


def main() -> int:
    """Initialize QApplication, create main widget window, and start event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName("MediaDock")
    app.setOrganizationName("KrishnaOS")

    # Instantiate media infrastructure and application coordinator
    provider = GSMTCProvider()
    media_core = MediaCore(provider=provider)

    # Instantiate GUI window with MediaCore reference
    window = MainWindow(media_core=media_core)
    window.show()

    # Start media detection
    media_core.start()

    # Ensure clean provider shutdown on application exit
    app.aboutToQuit.connect(media_core.stop)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
