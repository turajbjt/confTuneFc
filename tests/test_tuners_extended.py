"""
Extended Unit Tests for ConfTune FC Tuners and Subsystems.
Covers Storage, Systemd, DNF, Power, Fedy, Privacy, Process, Autostart, Server,
Safety, Logger, and Backup Manager.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from conftune.core.autostart_tuner import AutostartTuner, USER_AUTOSTART_DIR
from conftune.core.backup_manager import BackupManager
from conftune.core.detector import SystemDetector
from conftune.core.dnf_tuner import DNFTuner
from conftune.core.fedy_tuner import FedyTuner
from conftune.core.logger import SignalHandler, add_log_listener, get_log_dir, get_logger, remove_log_listener, setup_logger
from conftune.core.power_tuner import PowerTuner
from conftune.core.preset_manager import PresetManager
from conftune.core.privacy_tuner import PrivacyTuner
from conftune.core.process_tuner import ProcessTuner
from conftune.core.profiles import PROFILES, get_profile, list_profiles
from conftune.core.safety import SafetyEngine
from conftune.core.server_tuner import ServerTuner
from conftune.core.storage_tuner import StorageTuner
from conftune.core.sysctl_tuner import SysctlTuner
from conftune.core.systemd_tuner import SystemdTuner


class TestSafetyEngineExtended(unittest.TestCase):
    def test_safety_properties(self):
        engine = SafetyEngine(dry_run=True)
        self.assertTrue(engine.dry_run)
        self.assertIsInstance(engine.is_root, bool)
        self.assertIsInstance(engine.has_pkexec, bool)
        self.assertIsInstance(engine.has_sudo, bool)

    def test_verify_privilege_dry_run(self):
        engine = SafetyEngine(dry_run=True)
        ok, msg = engine.verify_privilege("Test action")
        self.assertTrue(ok)
        self.assertIn("dry-run", msg)

    def test_verify_privilege_non_root(self):
        engine = SafetyEngine(dry_run=False)
        with patch.object(SafetyEngine, "is_root", False):
            ok, msg = engine.verify_privilege("Test action")
            self.assertFalse(ok)
            self.assertIn("requires root privileges", msg)

    def test_verify_privilege_root(self):
        engine = SafetyEngine(dry_run=False)
        with patch.object(SafetyEngine, "is_root", True):
            ok, msg = engine.verify_privilege("Test action")
            self.assertTrue(ok)
            self.assertIn("Root privileges verified", msg)

    def test_sanitize_sysctl_value(self):
        engine = SafetyEngine()
        self.assertTrue(engine.sanitize_sysctl_value("vm.swappiness", "10"))
        self.assertTrue(engine.sanitize_sysctl_value("net.ipv4.ip_forward", "1"))
        self.assertFalse(engine.sanitize_sysctl_value("", "10"))
        self.assertFalse(engine.sanitize_sysctl_value("bad;key", "10"))
        self.assertFalse(engine.sanitize_sysctl_value("key", "10; rm -rf /"))
        self.assertFalse(engine.sanitize_sysctl_value("key", "10 && echo bad"))
        self.assertFalse(engine.sanitize_sysctl_value("key", "10 | echo bad"))
        self.assertFalse(engine.sanitize_sysctl_value("key", "10 `whoami`"))
        self.assertFalse(engine.sanitize_sysctl_value("key", "10 $VAR"))
        self.assertFalse(engine.sanitize_sysctl_value("key", "10\nevil=1"))


class TestLoggerSubsystem(unittest.TestCase):
    def test_logger_listeners(self):
        received = []

        def listener(msg, level):
            received.append((msg, level))

        add_log_listener(listener)
        logger = get_logger()
        logger.info("Test logger message 12345")

        self.assertTrue(any("Test logger message 12345" in m[0] for m in received))
        remove_log_listener(listener)

        count_before = len(received)
        logger.info("Another message")
        self.assertEqual(len(received), count_before)

    def test_get_log_dir(self):
        log_dir = get_log_dir()
        self.assertTrue(os.path.isdir(log_dir) or "/tmp" in log_dir)


class TestStorageTunerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_storage_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.tuner = StorageTuner(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_fstrim_status(self):
        status = self.tuner.get_fstrim_status()
        self.assertIn("active", status)
        self.assertIn("enabled", status)

    def test_enable_fstrim_timer_dry_run(self):
        ok, msg = self.tuner.enable_fstrim_timer()
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_enable_fstrim_timer_privilege_fail(self):
        self.tuner.safety.dry_run = False
        with patch.object(SafetyEngine, "is_root", False):
            ok, msg = self.tuner.enable_fstrim_timer()
            self.assertFalse(ok)
            self.assertIn("requires root", msg)

    def test_run_fstrim_now_dry_run(self):
        ok, msg = self.tuner.run_fstrim_now()
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_parse_active_scheduler(self):
        self.assertEqual(self.tuner._parse_active_scheduler("none [mq-deadline] kyber bfq"), "mq-deadline")
        self.assertEqual(self.tuner._parse_active_scheduler("[none] mq-deadline"), "none")
        self.assertEqual(self.tuner._parse_active_scheduler("none mq-deadline"), "default")

    def test_get_disk_schedulers(self):
        scheds = self.tuner.get_disk_schedulers()
        self.assertIsInstance(scheds, list)

    def test_set_disk_scheduler_nonexistent_device(self):
        ok, msg = self.tuner.set_disk_scheduler("nonexistent_disk_xyz", "none")
        self.assertFalse(ok)
        self.assertIn("not found", msg)

    def test_configure_zram_dry_run(self):
        ok, msg = self.tuner.configure_zram(size_percent=50, max_size_mb=4096)
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)


class TestSystemdTunerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_systemd_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.tuner = SystemdTuner(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_boot_blame(self):
        blame = self.tuner.get_boot_blame(top_n=5)
        self.assertIsInstance(blame, list)

    def test_get_boot_time_summary(self):
        summary = self.tuner.get_boot_time_summary()
        self.assertIsInstance(summary, str)

    def test_get_server_removable_services(self):
        services = self.tuner.get_server_removable_services()
        self.assertIsInstance(services, list)
        self.assertGreaterEqual(len(services), 1)
        for s in services:
            self.assertIn("service", s)
            self.assertIn("active", s)
            self.assertIn("enabled", s)

    def test_set_service_state_dry_run(self):
        ok, msg = self.tuner.set_service_state("bluetooth.service", enable=False)
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_configure_journald_limit_dry_run(self):
        ok, msg = self.tuner.configure_journald_limit(max_size="250M")
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)


class TestDNFTunerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_dnf_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.tuner = DNFTuner(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_current_settings(self):
        settings = self.tuner.get_current_settings()
        self.assertIn("max_parallel_downloads", settings)
        self.assertIn("fastestmirror", settings)
        self.assertIn("keepcache", settings)

    def test_apply_optimizations_dry_run(self):
        ok, msg = self.tuner.apply_optimizations(
            max_parallel_downloads=12,
            fastestmirror=True,
            defaultyes=True,
            keepcache=True,
        )
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_clean_cache_dry_run(self):
        ok, msg = self.tuner.clean_cache()
        self.assertIsInstance(ok, bool)


class TestPowerTunerExtended(unittest.TestCase):
    def setUp(self):
        self.safety = SafetyEngine(dry_run=True)
        self.tuner = PowerTuner(safety=self.safety)

    def test_governors(self):
        govs = self.tuner.get_available_governors()
        self.assertIsInstance(govs, list)
        self.assertGreaterEqual(len(govs), 1)

        curr = self.tuner.get_current_governor()
        self.assertIsInstance(curr, str)

        ok, msg = self.tuner.set_governor_all_cores("performance")
        self.assertIsInstance(ok, bool)

    def test_epp_support_and_mode(self):
        has_epp = self.tuner.has_epp_support()
        self.assertIsInstance(has_epp, bool)
        epp = self.tuner.get_current_epp()
        self.assertIsInstance(epp, str)
        ok, msg = self.tuner.set_epp_all_cores("performance")
        self.assertIsInstance(ok, bool)

    def test_power_profiles(self):
        status = self.tuner.get_power_profiles_status()
        self.assertIn("installed", status)
        self.assertIn("active", status)

    def test_thp(self):
        thp = self.tuner.get_thp_status()
        self.assertIn("active", thp)
        ok, msg = self.tuner.set_thp_mode("always")
        self.assertIsInstance(ok, bool)

    def test_gamemode(self):
        stat = self.tuner.get_gamemode_status()
        self.assertIn("installed", stat)
        self.assertIn("active", stat)


class TestFedyTunerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_fedy_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.tuner = FedyTuner(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rpmfusion_install_dry_run(self):
        ok, msg = self.tuner.install_rpmfusion()
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_multimedia_codecs_install_dry_run(self):
        ok, msg = self.tuner.install_multimedia_codecs()
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_configure_font_rendering(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("conftune.core.fedy_tuner.FONTCONFIG_USER_DIR", td):
                with patch("conftune.core.fedy_tuner.FONTCONFIG_USER_FILE", os.path.join(td, "fonts.conf")):
                    ok, msg = self.tuner.configure_font_rendering()
                    self.assertTrue(ok)
                    self.assertTrue(os.path.isfile(os.path.join(td, "fonts.conf")))

    def test_gnome_tweaks(self):
        stat = self.tuner.get_gnome_tweaks_status()
        self.assertIn("is_gnome", stat)
        self.assertIn("show_maximize", stat)
        self.assertIn("show_minimize", stat)


class TestPrivacyTunerExtended(unittest.TestCase):
    def setUp(self):
        self.safety = SafetyEngine(dry_run=True)
        self.tuner = PrivacyTuner(safety=self.safety)

    def test_telemetry_status(self):
        stat = self.tuner.get_telemetry_status()
        self.assertIn("gnome_software_metrics", stat)
        self.assertIn("gnome_privacy_recent", stat)

    def test_disable_all_telemetry(self):
        ok, msg = self.tuner.disable_all_telemetry()
        self.assertTrue(ok)


class TestProcessTunerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_proc_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.tuner = ProcessTuner(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_oomd_status_and_config_dry_run(self):
        stat = self.tuner.get_oomd_status()
        self.assertIn("installed", stat)
        self.assertIn("active", stat)
        ok, msg = self.tuner.configure_oomd_limits(memory_pressure="65%", swap_limit="85%")
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_protect_process_dry_run(self):
        # Even if process not found, returns false or dry run if found
        ok, msg = self.tuner.protect_process_by_name("systemd", score_adjust=-500)
        self.assertIsInstance(ok, bool)


class TestAutostartTunerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_auto_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.tuner = AutostartTuner(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_toggle_autostart_entry(self):
        # Create a mock .desktop file
        desktop_file = os.path.join(self.test_dir, "test_app.desktop")
        with open(desktop_file, "w", encoding="utf-8") as f:
            f.write("[Desktop Entry]\nName=TestApp\nExec=testapp\nType=Application\n")

        # Disable it
        ok, msg = self.tuner.toggle_autostart_entry(desktop_file, enable=False)
        self.assertTrue(ok)
        with open(desktop_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hidden=true", content)

        # Enable it back
        ok, msg = self.tuner.toggle_autostart_entry(desktop_file, enable=True)
        self.assertTrue(ok)
        with open(desktop_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("Hidden=true", content)

    def test_coredump_limit_dry_run(self):
        ok, msg = self.tuner.configure_coredump_limit(max_use="100M")
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_abrt_services(self):
        stat = self.tuner.get_abrt_status()
        self.assertIsInstance(stat, dict)
        ok, msg = self.tuner.toggle_abrt_services(enable=False)
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)


class TestServerTunerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_server_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.tuner = ServerTuner(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tuned_status_and_switch_dry_run(self):
        stat = self.tuner.get_tuned_status()
        self.assertIn("installed", stat)
        self.assertIn("active_profile", stat)
        ok, msg = self.tuner.set_tuned_profile("throughput-performance")
        self.assertIsInstance(ok, bool)

    def test_selinux_booleans_and_toggle_dry_run(self):
        bools = self.tuner.get_selinux_booleans()
        self.assertIsInstance(bools, list)
        ok, msg = self.tuner.set_selinux_boolean("httpd_can_network_connect", enable=True)
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_firewalld_status(self):
        f_stat = self.tuner.get_firewalld_status()
        self.assertIn("installed", f_stat)
        self.assertIn("running", f_stat)

    def test_audit_ssh_config(self):
        checks = self.tuner.audit_ssh_config()
        self.assertIsInstance(checks, list)
        self.assertGreaterEqual(len(checks), 3)
        params = [c["param"] for c in checks]
        self.assertIn("PermitRootLogin", params)
        self.assertIn("PasswordAuthentication", params)

    def test_specialized_stacks_dry_run(self):
        # Virtualmin
        ok_vm, msg_vm = self.tuner.optimize_virtualmin_stack()
        self.assertTrue(ok_vm)
        self.assertIn("[DRY RUN]", msg_vm)

        # Containers
        ok_c, msg_c = self.tuner.optimize_containers_stack()
        self.assertTrue(ok_c)
        self.assertIn("[DRY RUN]", msg_c)

        # Virt host
        ok_v, msg_v = self.tuner.optimize_virtualization_host()
        self.assertTrue(ok_v)
        self.assertIn("[DRY RUN]", msg_v)


class TestSysctlTunerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_sysctl_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.tuner = SysctlTuner(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_live_value(self):
        val = self.tuner.get_live_value("kernel.pid_max")
        self.assertIsInstance(val, str)

    def test_get_all_live_status(self):
        status = self.tuner.get_all_live_status()
        self.assertGreaterEqual(len(status), 15)
        for item in status:
            self.assertIn("key", item)
            self.assertIn("category", item)
            self.assertIn("current", item)

    def test_apply_parameters_skips_injections(self):
        params = {
            "vm.swappiness": "10",
            "malicious.param; injection": "10",
            "net.ipv4.ip_forward": "1; rm -rf /",
        }
        ok, msg = self.tuner.apply_parameters(params, profile_name="sanitize_test")
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)


class TestDNFTunerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_dnf_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.tuner = DNFTuner(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_current_settings_dnf(self):
        settings = self.tuner.get_current_settings()
        self.assertIn("max_parallel_downloads", settings)
        self.assertIn("fastestmirror", settings)
        self.assertIn("is_dnf5", settings)

    def test_apply_optimizations_dry_run(self):
        ok, msg = self.tuner.apply_optimizations(max_parallel_downloads=12, fastestmirror=True)
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)

    def test_clean_cache_dry_run(self):
        ok, msg = self.tuner.clean_cache()
        self.assertTrue(ok)
        self.assertIn("[DRY RUN]", msg)


class TestPresetManagerExtended(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_preset_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.preset_mgr = PresetManager(safety=self.safety, backup_mgr=self.backup_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_ansible_playbook(self):
        sample_preset = {
            "name": "Fleet Playbook Test",
            "sysctl": {"vm.swappiness": "10", "net.core.somaxconn": "32768"},
            "dnf": {"max_parallel_downloads": 10, "fastestmirror": "True"},
            "journald_max": "200M",
            "tuned_profile": "throughput-performance",
        }
        out_playbook = os.path.join(self.test_dir, "playbook.yml")
        ok, msg = self.preset_mgr.generate_ansible_playbook(sample_preset, out_playbook)
        self.assertTrue(ok)
        self.assertTrue(os.path.isfile(out_playbook))
        with open(out_playbook, "r") as f:
            content = f.read()
        self.assertIn("Apply ConfTune FC Performance Tuning", content)
        self.assertIn("vm.swappiness", content)
        self.assertIn("max_parallel_downloads", content)
        self.assertIn("SystemMaxUse=200M", content)
        self.assertIn("throughput-performance", content)


class TestPowerDaemonExtended(unittest.TestCase):
    def setUp(self):
        self.safety = SafetyEngine(dry_run=True)
        self.power_tuner = PowerTuner(safety=self.safety)

    def test_power_daemon_lifecycle(self):
        from conftune.core.power_daemon import PowerDaemon
        daemon = PowerDaemon(power_tuner=self.power_tuner, safety=self.safety)
        state_info = daemon.detect_power_state()
        self.assertIn("state", state_info)
        self.assertIn(state_info["state"], ["ac", "battery"])

        # Test profile applications
        ok_ac, msg_ac = daemon.apply_profile("ac")
        self.assertTrue(ok_ac)
        self.assertIn("AC", msg_ac)

        ok_bat, msg_bat = daemon.apply_profile("battery")
        self.assertTrue(ok_bat)
        self.assertIn("BATTERY", msg_bat)

        # Test run_once
        ok_once, msg_once, info = daemon.run_once()
        self.assertTrue(ok_once)
        self.assertIn("state", info)


if __name__ == "__main__":
    unittest.main()
