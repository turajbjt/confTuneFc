"""
Automated Unit Tests for ConfTune FC.
Tests system detector, profiles catalog, sysctl generator, and backup manager.
"""

import os
import shutil
import tempfile
import unittest

from conftune.core.autostart_tuner import AutostartTuner
from conftune.core.backup_manager import BackupManager
from conftune.core.detector import SystemDetector
from conftune.core.dnf_tuner import DNFTuner
from conftune.core.fedy_tuner import FedyTuner
from conftune.core.power_tuner import PowerTuner
from conftune.core.privacy_tuner import PrivacyTuner
from conftune.core.process_tuner import ProcessTuner
from conftune.core.profiles import PROFILES, get_profile, list_profiles
from conftune.core.safety import SafetyEngine
from conftune.core.server_tuner import ServerTuner
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

    def test_fedy_tuner(self):
        fedy = FedyTuner(safety=self.safety)
        rf = fedy.is_rpmfusion_installed()
        self.assertIn("free", rf)
        self.assertIn("nonfree", rf)
        nv = fedy.check_nvidia_status()
        self.assertIn("has_hardware", nv)

    def test_power_tuner(self):
        power = PowerTuner(safety=self.safety)
        govs = power.get_available_governors()
        self.assertGreaterEqual(len(govs), 1)
        ok, msg = power.set_governor_all_cores("powersave")
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_process_and_oomd_tuner(self):
        proc = ProcessTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        stat = proc.get_oomd_status()
        self.assertIn("memory_pressure_limit", stat)
        ok, msg = proc.configure_oomd_limits("75%", "90%")
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_autostart_and_privacy_tuner(self):
        auto = AutostartTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        entries = auto.list_autostart_entries()
        self.assertIsInstance(entries, list)
        ok, msg = auto.configure_coredump_limit("150M")
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

        privacy = PrivacyTuner(safety=self.safety)
        p_stat = privacy.get_telemetry_status()
        self.assertIn("gnome_privacy_recent", p_stat)

    def test_server_tuner_smart_and_selinux(self):
        server = ServerTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        se = server.get_selinux_status()
        self.assertIsInstance(se, str)
        drives = server.get_drive_health_summary()
        self.assertGreaterEqual(len(drives), 1)


if __name__ == "__main__":
    unittest.main()
