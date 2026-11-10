"""
Unit tests for Default and Undo functionality across all ConfTune FC tuners.
Verifies rollback to system defaults, override detection, and safety.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from conftune.core.backup_manager import BackupManager
from conftune.core.dnf_tuner import DNFTuner
from conftune.core.fedy_tuner import FedyTuner
from conftune.core.privacy_tuner import PrivacyTuner
from conftune.core.process_tuner import ProcessTuner
from conftune.core.safety import SafetyEngine
from conftune.core.storage_tuner import StorageTuner
from conftune.core.sysctl_tuner import SysctlTuner
from conftune.core.systemd_tuner import SystemdTuner


class TestDefaultsAndUndo(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=os.path.join(self.temp_dir, "snapshots"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dnf_customized_and_restore_defaults(self):
        tuner = DNFTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        # In dry-run mode, restore_defaults should succeed
        ok, msg = tuner.restore_defaults()
        self.assertTrue(ok)
        self.assertIn("standard Fedora defaults", msg)

        # Test is_customized logic
        with patch.object(tuner, "get_current_settings", return_value={"max_parallel_downloads": "10", "fastestmirror": "True"}):
            self.assertTrue(tuner.is_customized())

        with patch.object(tuner, "get_current_settings", return_value={"max_parallel_downloads": "3", "fastestmirror": "False", "defaultyes": "False", "keepcache": "False"}):
            self.assertFalse(tuner.is_customized())

    def test_fedy_font_and_gnome_undo(self):
        tuner = FedyTuner(safety=self.safety, backup_mgr=self.backup_mgr)

        # Test font restore
        dummy_font_file = os.path.join(self.temp_dir, "fonts.conf")
        with open(dummy_font_file, "w") as f:
            f.write("<fontconfig></fontconfig>")

        with patch("conftune.core.fedy_tuner.FONTCONFIG_USER_FILE", dummy_font_file):
            self.assertTrue(tuner.is_font_rendering_optimized())
            ok, msg = tuner.restore_default_fonts()
            self.assertTrue(ok)
            self.assertFalse(tuner.is_font_rendering_optimized())

        # Test GNOME defaults
        with patch("shutil.which", return_value="/usr/bin/gsettings"):
            with patch("subprocess.run") as mock_sub:
                mock_sub.return_value.returncode = 0
                ok, msg = tuner.restore_gnome_defaults()
                self.assertTrue(ok)
                self.assertIn("defaults", msg)

    def test_sysctl_has_overrides_and_restore(self):
        tuner = SysctlTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        dummy_sysctl = os.path.join(self.temp_dir, "99-conftune.conf")
        with open(dummy_sysctl, "w") as f:
            f.write("vm.swappiness = 10\n")

        with patch("conftune.core.sysctl_tuner.SYSCTL_CONF_PATH", dummy_sysctl):
            self.assertTrue(tuner.has_custom_overrides())
            ok, msg = tuner.restore_system_defaults()
            self.assertTrue(ok)
            self.assertIn("sysctl --system", msg)

    def test_storage_fstrim_disable_and_zram_restore(self):
        tuner = StorageTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        ok, msg = tuner.disable_fstrim_timer()
        self.assertTrue(ok)

        dummy_zram = os.path.join(self.temp_dir, "zram-generator.conf")
        with open(dummy_zram, "w") as f:
            f.write("[zram0]\n")

        with patch("conftune.core.storage_tuner.ZRAM_CONF_PATH", dummy_zram):
            self.assertTrue(tuner.is_zram_customized())
            ok, msg = tuner.restore_default_zram()
            self.assertTrue(ok)
            self.assertIn("restored Fedora default", msg)

    def test_systemd_journald_restore(self):
        tuner = SystemdTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        dummy_j = os.path.join(self.temp_dir, "99-conftune.conf")
        with open(dummy_j, "w") as f:
            f.write("[Journal]\nSystemMaxUse=200M\n")

        with patch("conftune.core.systemd_tuner.JOURNALD_CONF_PATH", dummy_j):
            self.assertTrue(tuner.is_journald_configured())
            ok, msg = tuner.restore_default_journald()
            self.assertTrue(ok)
            self.assertIn("restored default journal limits", msg)

    def test_process_oomd_restore(self):
        tuner = ProcessTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        dummy_oomd = os.path.join(self.temp_dir, "99-conftune.conf")
        with open(dummy_oomd, "w") as f:
            f.write("[OOM]\nDefaultMemoryPressureLimit=80%\n")

        with patch("conftune.core.process_tuner.OOMD_CONF_PATH", dummy_oomd):
            self.assertTrue(tuner.is_oomd_customized())
            ok, msg = tuner.restore_default_oomd()
            self.assertTrue(ok)
            self.assertIn("restored default systemd-oomd thresholds", msg)

    def test_privacy_restore_defaults(self):
        tuner = PrivacyTuner(safety=self.safety)
        with patch("shutil.which", return_value="/usr/bin/gsettings"):
            with patch("subprocess.run") as mock_sub:
                mock_sub.return_value.returncode = 0
                ok, msg = tuner.restore_telemetry_defaults()
                self.assertTrue(ok)
                self.assertIn("restored to default", msg)

    def test_autostart_coredump_and_abrt(self):
        from conftune.core.autostart_tuner import AutostartTuner
        tuner = AutostartTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        dummy_cd = os.path.join(self.temp_dir, "99-conftune.conf")
        with open(dummy_cd, "w") as f:
            f.write("[Coredump]\nStorage=external\nMaxUse=200M\n")

        with patch("conftune.core.autostart_tuner.COREDUMP_CONF_PATH", dummy_cd):
            self.assertTrue(tuner.is_coredump_configured())
            self.assertEqual(tuner.get_current_coredump_limit(), "200M")
            ok, msg = tuner.restore_default_coredump()
            self.assertTrue(ok)
            self.assertIn("restore", msg.lower())

        # Test ABRT active status
        with patch.object(tuner, "get_abrt_status", return_value={"abrt-journal-core.service": True, "abrt-oops.service": False}):
            self.assertTrue(tuner.is_abrt_active())
        with patch.object(tuner, "get_abrt_status", return_value={"abrt-journal-core.service": False, "abrt-oops.service": False}):
            self.assertFalse(tuner.is_abrt_active())


if __name__ == "__main__":
    unittest.main()
