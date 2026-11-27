"""Unit tests for EqualizerAPOManager system-wide audio boost and equalizer integration."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.media.equalizer_apo import (
    EqualizerAPOManager,
    MEDIADOCK_CONFIG_FILENAME,
    MASTER_CONFIG_FILENAME,
    EQUALIZER_APO_DOWNLOAD_URL,
)


class TestEqualizerAPOManager(unittest.TestCase):
    """Test suite for EqualizerAPOManager detection, config generation, and file synchronization."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.config_dir = self.tmp_dir.name
        self.manager = EqualizerAPOManager(config_dir=self.config_dir)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_installation_detection_directory(self) -> None:
        """Verify is_installed returns True when config directory exists."""
        self.assertTrue(self.manager.is_installed())

        non_existent = EqualizerAPOManager(config_dir=os.path.join(self.config_dir, "missing_subdir"))
        with patch("sys.platform", "linux"):
            self.assertFalse(non_existent.is_installed())

    def test_installer_url(self) -> None:
        """Verify get_installer_url returns valid https URL."""
        url = EqualizerAPOManager.get_installer_url()
        self.assertTrue(url.startswith("https://"))
        self.assertEqual(url, EQUALIZER_APO_DOWNLOAD_URL)

    def test_generate_config_text_default_flat(self) -> None:
        """Verify generated config text for flat 0 dB settings."""
        text = EqualizerAPOManager.generate_config_text(
            preamp_boost_db=0.0,
            bass_db=0.0,
            clarity_db=0.0,
            treble_db=0.0,
            eq_bands=[0.0, 0.0, 0.0, 0.0, 0.0],
            eq_enabled=True,
        )
        self.assertIn("Preamp: +0.0 dB", text)
        self.assertIn("GraphicEQ: 60 +0.0; 250 +0.0; 1000 +0.0; 4000 +0.0; 16000 +0.0", text)
        self.assertNotIn("Filter: ON LSC", text)
        self.assertNotIn("Filter: ON PK", text)
        self.assertNotIn("Filter: ON HSC", text)

    def test_generate_config_text_with_boost_and_tones(self) -> None:
        """Verify generated config includes preamp boost, bass low-shelf, clarity peaking, and treble high-shelf."""
        text = EqualizerAPOManager.generate_config_text(
            preamp_boost_db=4.5,
            bass_db=5.0,
            clarity_db=3.0,
            treble_db=-2.0,
            eq_bands=[3.0, 2.0, 0.0, 1.0, 2.0],
            eq_enabled=True,
        )
        self.assertIn("Preamp: +4.5 dB", text)
        self.assertIn("GraphicEQ: 60 +3.0; 250 +2.0; 1000 +0.0; 4000 +1.0; 16000 +2.0", text)
        self.assertIn("Filter: ON LSC Fc 100 Hz Gain +5.0 dB", text)
        self.assertIn("Filter: ON PK Fc 2500 Hz Gain +3.0 dB Q 1.4", text)
        self.assertIn("Filter: ON HSC Fc 10000 Hz Gain -2.0 dB", text)

    def test_generate_config_text_bypassed(self) -> None:
        """Verify bypassed config produces 0 dB preamp and no active filters."""
        text = EqualizerAPOManager.generate_config_text(
            preamp_boost_db=6.0,
            bass_db=4.0,
            eq_enabled=False,
        )
        self.assertIn("Preamp: 0 dB", text)
        self.assertIn("# Master Equalizer Bypassed", text)
        self.assertNotIn("GraphicEQ", text)

    def test_apply_eq_writes_files_and_appends_include(self) -> None:
        """Verify apply_eq creates mediadock_eq.txt and adds Include directive to config.txt."""
        master_path = os.path.join(self.config_dir, MASTER_CONFIG_FILENAME)
        with open(master_path, "w", encoding="utf-8") as f:
            f.write("# Existing user config\nPreamp: -1 dB\n")

        success = self.manager.apply_eq(
            preamp_boost_db=3.0,
            bass_db=4.0,
            clarity_db=2.0,
            treble_db=1.0,
            eq_bands=[1.0, 2.0, 0.0, 0.0, 1.0],
            eq_enabled=True,
        )
        self.assertTrue(success)

        # Check mediadock_eq.txt was created
        mediadock_path = os.path.join(self.config_dir, MEDIADOCK_CONFIG_FILENAME)
        self.assertTrue(os.path.isfile(mediadock_path))
        with open(mediadock_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Preamp: +3.0 dB", content)

        # Check master config.txt contains Include directive
        with open(master_path, "r", encoding="utf-8") as f:
            master_content = f.read()
        self.assertIn(f"Include: {MEDIADOCK_CONFIG_FILENAME}", master_content)

    def test_apply_eq_creates_master_config_if_missing(self) -> None:
        """Verify apply_eq creates master config.txt with Include directive if it did not exist."""
        master_path = os.path.join(self.config_dir, MASTER_CONFIG_FILENAME)
        self.assertFalse(os.path.exists(master_path))

        success = self.manager.apply_eq(preamp_boost_db=0.0)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(master_path))
        with open(master_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(f"Include: {MEDIADOCK_CONFIG_FILENAME}", content)

    def test_apply_eq_fails_gracefully_when_dir_missing(self) -> None:
        """Verify apply_eq returns False when directory does not exist."""
        missing_mgr = EqualizerAPOManager(config_dir=os.path.join(self.config_dir, "non_existent"))
        self.assertFalse(missing_mgr.apply_eq(preamp_boost_db=2.0))

    def test_connection_status_missing_vs_connected(self) -> None:
        """Verify get_connection_status distinguishes missing dir, unlinked Include, and live connected."""
        missing = EqualizerAPOManager(config_dir=os.path.join(self.config_dir, "missing"))
        with patch("sys.platform", "linux"):
            st_missing = missing.get_connection_status()
            self.assertFalse(st_missing["installed"])
            self.assertFalse(st_missing["connected"])

        # Installed directory before apply_eq has no Include link yet
        st_pre = self.manager.get_connection_status()
        self.assertTrue(st_pre["installed"])
        self.assertTrue(st_pre["writable"])
        self.assertFalse(st_pre["include_configured"])
        self.assertFalse(st_pre["connected"])

        # After apply_eq, config.txt Include link exists -> connected is True
        self.assertTrue(self.manager.apply_eq(preamp_boost_db=2.0))
        st_post = self.manager.get_connection_status()
        self.assertTrue(st_post["connected"])

    def test_configure_permissions_elevated_and_connect_flow(self) -> None:
        """Verify UAC elevation fallback path invokes installer and permission setup when missing."""
        missing_dir = os.path.join(self.config_dir, "new_apo", "config")
        mgr = EqualizerAPOManager(config_dir=missing_dir)

        def fake_elevated(exe: str, params: str, wait: bool = True, timeout_ms: int = 120000):
            if params == "/S":
                os.makedirs(missing_dir, exist_ok=True)
            return (True, 0)

        with patch("sys.platform", "win32"):
            with patch("winreg.OpenKey", side_effect=OSError("Key not found")):
                with patch.object(mgr, "download_installer", return_value=("C:\\Temp\\Setup.exe", "")):
                    with patch.object(mgr, "_run_elevated", side_effect=fake_elevated):
                        ok, msg, newly_installed = mgr.connect_system_audio(preamp_boost_db=4.0)

        self.assertTrue(ok)
        self.assertTrue(newly_installed)
        self.assertTrue(mgr.get_connection_status()["connected"])


if __name__ == "__main__":
    unittest.main()
