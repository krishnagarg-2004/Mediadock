"""CI-safe unit tests for MediaDock PyInstaller spec, build system, and startup flags."""

import os
import sys
import unittest
from unittest.mock import patch

from src.utils.autostart import AutostartManager

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SPEC_PATH = os.path.join(PROJECT_ROOT, "MediaDock.spec")
BUILD_SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "build.py")
GITIGNORE_PATH = os.path.join(PROJECT_ROOT, ".gitignore")


class TestBuildSpec(unittest.TestCase):
    """Test packaging configuration, spec validity, build script structure, and startup flag handling."""

    def test_spec_file_exists(self) -> None:
        """Verify MediaDock.spec exists in project root."""
        self.assertTrue(os.path.exists(SPEC_PATH), f"MediaDock.spec not found at {SPEC_PATH}")

    def test_spec_file_configuration(self) -> None:
        """Verify MediaDock.spec contents for entry point, name, console setting, and hidden imports."""
        with open(SPEC_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("src/main.py", content, "MediaDock.spec must target src/main.py entry point")
        self.assertIn('name="MediaDock"', content, "MediaDock.spec must specify name='MediaDock'")
        self.assertIn("console=False", content, "MediaDock.spec must configure console=False (windowed GUI)")
        self.assertIn("winrt.windows.media.control", content, "MediaDock.spec missing winrt.windows.media.control hidden import")
        self.assertIn("winrt.windows.storage.streams", content, "MediaDock.spec missing winrt.windows.storage.streams hidden import")
        self.assertIn("winrt.windows.foundation", content, "MediaDock.spec missing winrt.windows.foundation hidden import")
        self.assertIn("winrt.system", content, "MediaDock.spec missing winrt.system hidden import")

    def test_build_script_exists(self) -> None:
        """Verify scripts/build.py orchestration script exists."""
        self.assertTrue(os.path.exists(BUILD_SCRIPT_PATH), f"scripts/build.py not found at {BUILD_SCRIPT_PATH}")

    def test_autostart_startup_command_frozen(self) -> None:
        """Verify AutostartManager generates proper command when sys.frozen is True."""
        mock_exe = os.path.abspath(os.path.join(PROJECT_ROOT, "dist", "MediaDock.exe"))
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", mock_exe):
            cmd = AutostartManager.get_startup_command()
            self.assertEqual(cmd, f'"{mock_exe}" --minimized')

    def test_gitignore_contains_build_artifacts(self) -> None:
        """Verify .gitignore contains build/ and dist/ rules."""
        self.assertTrue(os.path.exists(GITIGNORE_PATH), f".gitignore not found at {GITIGNORE_PATH}")
        with open(GITIGNORE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("build/", content, ".gitignore missing build/ entry")
        self.assertIn("dist/", content, ".gitignore missing dist/ entry")


if __name__ == "__main__":
    unittest.main()
