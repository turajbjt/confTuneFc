"""
Automated Unit Tests for ConfTune FC.
Tests system detector, profiles catalog, sysctl generator, and backup manager.
"""

import os
import shutil
import tempfile
import unittest

from conftune.core.backup_manager import BackupManager
from conftune.core.detector import SystemDetector
from conftune.core.dnf_tuner import DNFTuner
from conftune.core.profiles import PROFILES, get_profile, list_profiles
from conftune.core.safety import SafetyEngine
from conftune.core.sysctl_tuner import SysctlTuner


class TestConfTuneCore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_test_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_detector_os_and_hw(self):
        detector = SystemDetector(refresh_on_init=True)
        self.assertIn("arch", detector.os_info)
        self.assertIn("cpu_cores", detector.hardware_info)
        self.assertGreaterEqual(detector.hardware_info["cpu_cores"], 1)
        self.assertIn("is_desktop", detector.role_info)
        self.assertIn("virtualmin", detector.specialized_stacks)
        self.assertIn("containers", detector.specialized_stacks)

    def test_profiles_catalog(self):
        profiles = list_profiles()
        self.assertGreaterEqual(len(profiles), 8)
        self.assertIsNotNone(get_profile("workstation"))
        self.assertIsNotNone(get_profile("server"))
        self.assertIsNotNone(get_profile("gaming"))
        self.assertIsNotNone(get_profile("container_host"))
        self.assertIsNotNone(get_profile("virtualization_host"))
        self.assertIsNotNone(get_profile("virtualmin"))

        # Verify workstation has essential parameters
        ws = get_profile("workstation")
        self.assertIn("vm.swappiness", ws["sysctl"])
        self.assertIn("net.ipv4.tcp_congestion_control", ws["sysctl"])

    def test_sysctl_simulation(self):
        tuner = SysctlTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        ok, msg = tuner.apply_parameters({"vm.swappiness": "15"}, profile_name="test_ws")
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_backup_and_rollback(self):
        # Create a mock target file
        mock_file = os.path.join(self.test_dir, "sysctl_dummy.conf")
        with open(mock_file, "w") as f:
            f.write("vm.swappiness = 60\n")

        snap_id = self.backup_mgr.create_snapshot(
            profile_name="unit_test",
            target_paths=[mock_file],
            notes="Snapshot test",
        )
        self.assertIsNotNone(snap_id)

        # Modify mock file
        with open(mock_file, "w") as f:
            f.write("vm.swappiness = 10\n")

        # Rollback
        ok, msg = self.backup_mgr.rollback_snapshot(snap_id, dry_run=False)
        self.assertTrue(ok)

        # Verify content was restored
        with open(mock_file, "r") as f:
            content = f.read()
        self.assertEqual(content, "vm.swappiness = 60\n")

    def test_safety_sanitization(self):
        self.assertTrue(self.safety.sanitize_sysctl_value("vm.swappiness", "15"))
        self.assertFalse(self.safety.sanitize_sysctl_value("bad;injection", "10"))
        self.assertFalse(self.safety.sanitize_sysctl_value("vm.swappiness", "15; rm -rf /"))


if __name__ == "__main__":
    unittest.main()
