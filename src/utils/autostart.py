"""Windows Registry autostart manager for MediaDock."""

import sys
import os
import logging

logger = logging.getLogger(__name__)

# winreg is Windows-only; fallback safely on non-Windows platforms
try:
    import winreg
except ImportError:
    winreg = None

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "MediaDock"


class AutostartManager:
    """Manages Windows Registry autostart settings under HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run."""

    @staticmethod
    def get_startup_command() -> str:
        """Construct the appropriate startup command based on execution environment (packaged vs dev)."""
        if getattr(sys, "frozen", False):
            # Executable created by PyInstaller
            exe_path = os.path.abspath(sys.executable)
            return f'"{exe_path}" --minimized'
        # Development script execution: resolve src/main.py reliably regardless of working directory
        python_exe = os.path.abspath(sys.executable)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidate_main = os.path.join(project_root, "src", "main.py")
        main_script = candidate_main if os.path.exists(candidate_main) else os.path.abspath(sys.argv[0])
        return f'"{python_exe}" "{main_script}" --minimized'

    @staticmethod
    def reconcile(enabled: bool) -> bool:
        """Synchronize Windows Run registry entry with the persisted autostart preference."""
        if enabled:
            return AutostartManager.enable_autostart()
        return True

    @classmethod
    def is_autostart_enabled(cls) -> bool:
        """Return True if MediaDock autostart registry entry exists and is valid."""
        if winreg is None:
            return False

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                REG_KEY_PATH,
                0,
                winreg.KEY_READ,
            ) as key:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(value)
        except (OSError, FileNotFoundError):
            return False
        except Exception as e:
            logger.error("Failed to query Windows autostart registry key: %s", e)
            return False

    @classmethod
    def enable_autostart(cls) -> bool:
        """Create or update MediaDock autostart value in Windows Registry."""
        if winreg is None:
            logger.error("winreg module not available; autostart disabled.")
            return False

        command = cls.get_startup_command()
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                REG_KEY_PATH,
                0,
                winreg.KEY_WRITE,
            ) as key:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
            return True
        except OSError as e:
            logger.error("Failed to write MediaDock autostart registry key: %s", e)
            return False



    @classmethod
    def disable_autostart(cls) -> bool:
        """Remove MediaDock autostart value from Windows Registry if present."""
        if winreg is None:
            return False

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                REG_KEY_PATH,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, APP_NAME)
            return True
        except FileNotFoundError:
            # Already disabled/removed
            return True
        except OSError as e:
            logger.error("Failed to remove MediaDock autostart registry key: %s", e)
            return False
