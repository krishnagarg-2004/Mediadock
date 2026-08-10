"""Single-instance application enforcement and local IPC mechanism for MediaDock."""

import sys
import logging
from typing import List, Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

logger = logging.getLogger(__name__)

DEFAULT_SERVER_NAME = "MediaDock_SingleInstance_Lock_v1"


class SingleInstanceGuard(QObject):
    """Enforces single-instance execution via PySide6 QLocalServer / QLocalSocket IPC."""

    activation_requested = Signal()
    minimized_activation_requested = Signal()

    def __init__(
        self,
        server_name: str = DEFAULT_SERVER_NAME,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._server_name = server_name
        self._server: Optional[QLocalServer] = None
        self._is_primary: bool = False

    def is_primary(self) -> bool:
        """Return True if this instance successfully acquired primary ownership."""
        return self._is_primary

    def initialize(self, args: Optional[List[str]] = None) -> bool:
        """
        Attempt to acquire primary ownership via QLocalServer.
        Returns True if this is the primary instance, False if a secondary instance was detected and signaled.
        """
        if args is None:
            args = sys.argv

        # 1. Check if an active primary instance is currently running and accepting connections
        socket = QLocalSocket(self)
        socket.connectToServer(self._server_name)
        if socket.waitForConnected(500):
            # Active primary instance exists. Send activation payload and return False (secondary instance)
            start_hidden = "--minimized" in args or "--start-hidden" in args
            payload = b"ACTIVATE_MINIMIZED" if start_hidden else b"ACTIVATE"
            socket.write(payload)
            socket.flush()
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            self._is_primary = False
            return False

        # 2. No active primary instance responding: acquire primary server ownership
        QLocalServer.removeServer(self._server_name)
        server = QLocalServer(self)
        if server.listen(self._server_name):
            self._server = server
            self._is_primary = True
            self._server.newConnection.connect(self._on_new_connection)
            return True

        self._is_primary = False
        return False

    def _on_new_connection(self) -> None:
        """Handle incoming IPC connection from a secondary launch."""
        if not self._server:
            return
        socket = self._server.nextPendingConnection()
        if not socket:
            return

        if socket.waitForReadyRead(500):
            data = bytes(socket.readAll()).strip()
            if data == b"ACTIVATE":
                self.activation_requested.emit()
            elif data == b"ACTIVATE_MINIMIZED":
                self.minimized_activation_requested.emit()
            else:
                self.activation_requested.emit()
        else:
            self.activation_requested.emit()

        socket.disconnectFromServer()

    def close(self) -> None:
        """Release QLocalServer and remove server endpoint on clean exit."""
        if self._server:
            self._server.close()
            QLocalServer.removeServer(self._server_name)
            self._server = None
        self._is_primary = False
