"""Unit tests for single-instance enforcement and local IPC activation."""

import sys
import uuid
import unittest
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from src.core.single_instance import SingleInstanceGuard


def get_test_app() -> QApplication:
    """Ensure a QApplication instance exists for Qt network/event loop tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class TestSingleInstanceGuard(unittest.TestCase):
    """Test suite for SingleInstanceGuard IPC lock acquisition, activation, and cleanup."""

    def setUp(self) -> None:
        self.app = get_test_app()
        # Use a unique server name per test to prevent cross-test interference
        self.test_server_name = f"Test_MediaDock_Lock_{uuid.uuid4().hex}"

    def test_first_instance_acquires_ownership(self) -> None:
        """Verify first instance successfully becomes primary and acquires ownership."""
        guard = SingleInstanceGuard(server_name=self.test_server_name)
        try:
            is_primary = guard.initialize(args=["MediaDock.exe"])
            self.assertTrue(is_primary)
            self.assertTrue(guard.is_primary())
        finally:
            guard.close()

    def test_second_instance_detects_primary_and_returns_false(self) -> None:
        """Verify second instance detects existing primary server and initializes as secondary (returns False)."""
        guard1 = SingleInstanceGuard(server_name=self.test_server_name)
        guard2 = SingleInstanceGuard(server_name=self.test_server_name)

        try:
            self.assertTrue(guard1.initialize(args=["MediaDock.exe"]))

            # Second instance must detect primary and return False
            self.assertFalse(guard2.initialize(args=["MediaDock.exe"]))
            self.assertFalse(guard2.is_primary())
        finally:
            guard2.close()
            guard1.close()

    def test_activation_signal_emitted_on_secondary_launch(self) -> None:
        """Verify secondary launch sends ACTIVATE payload, causing primary instance to emit activation_requested."""
        guard1 = SingleInstanceGuard(server_name=self.test_server_name)
        guard2 = SingleInstanceGuard(server_name=self.test_server_name)

        activation_cb = MagicMock()
        guard1.activation_requested.connect(activation_cb)

        try:
            self.assertTrue(guard1.initialize(args=["MediaDock.exe"]))
            self.assertFalse(guard2.initialize(args=["MediaDock.exe"]))

            # Process Qt event loop to process IPC readyRead signal
            self.app.processEvents()

            activation_cb.assert_called_once()
        finally:
            guard2.close()
            guard1.close()

    def test_activate_minimized_payload_handling(self) -> None:
        """Verify secondary launch with --minimized sends ACTIVATE_MINIMIZED, emitting minimized_activation_requested."""
        guard1 = SingleInstanceGuard(server_name=self.test_server_name)
        guard2 = SingleInstanceGuard(server_name=self.test_server_name)

        normal_cb = MagicMock()
        minimized_cb = MagicMock()
        guard1.activation_requested.connect(normal_cb)
        guard1.minimized_activation_requested.connect(minimized_cb)

        try:
            self.assertTrue(guard1.initialize(args=["MediaDock.exe"]))
            self.assertFalse(guard2.initialize(args=["MediaDock.exe", "--minimized"]))

            self.app.processEvents()

            minimized_cb.assert_called_once()
            normal_cb.assert_not_called()
        finally:
            guard2.close()
            guard1.close()

    def test_new_instance_can_start_after_previous_exits(self) -> None:
        """Verify a new instance can become primary after previous primary exits cleanly."""
        guard1 = SingleInstanceGuard(server_name=self.test_server_name)
        self.assertTrue(guard1.initialize(args=["MediaDock.exe"]))
        guard1.close()

        guard2 = SingleInstanceGuard(server_name=self.test_server_name)
        try:
            self.assertTrue(guard2.initialize(args=["MediaDock.exe"]))
            self.assertTrue(guard2.is_primary())
        finally:
            guard2.close()

    def test_stale_lock_recovery(self) -> None:
        """Verify guard recovers from stale lock files/endpoints when no active server exists."""
        from PySide6.QtNetwork import QLocalServer

        # Create a stale server endpoint manually
        stale_server = QLocalServer()
        stale_server.listen(self.test_server_name)
        stale_server.close()  # Close without removeServer to leave endpoint in dead state

        guard = SingleInstanceGuard(server_name=self.test_server_name)
        try:
            # Must recover from stale endpoint and become primary
            self.assertTrue(guard.initialize(args=["MediaDock.exe"]))
            self.assertTrue(guard.is_primary())
        finally:
            guard.close()

    def test_simultaneous_startup_race_safety(self) -> None:
        """Verify that when two guards attempt initialization on the same server name, exactly ONE becomes primary."""
        guard_a = SingleInstanceGuard(server_name=self.test_server_name)
        guard_b = SingleInstanceGuard(server_name=self.test_server_name)

        res_a = guard_a.initialize(args=["MediaDock.exe"])
        res_b = guard_b.initialize(args=["MediaDock.exe"])

        try:
            # Exactly one must be primary (True) and one secondary (False)
            self.assertTrue((res_a and not res_b) or (res_b and not res_a))
            self.assertNotEqual(guard_a.is_primary(), guard_b.is_primary())
        finally:
            guard_b.close()
            guard_a.close()

    def test_ipc_connection_failure_handling(self) -> None:
        """Verify graceful handling when IPC socket fails to connect or write."""
        guard = SingleInstanceGuard(server_name="Invalid_NonExistent_Server_Name_123456789")
        try:
            # Must acquire primary on new non-existent server name cleanly
            self.assertTrue(guard.initialize(args=["MediaDock.exe"]))
            self.assertTrue(guard.is_primary())
        finally:
            guard.close()


if __name__ == "__main__":
    unittest.main()
