"""
Automated Unit Tests for all ConfTune FC GUI Views, Tabs, and MainWindow.
Executes under headless offscreen Qt platform.
"""

import logging
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from conftune.core.autostart_tuner import AutostartTuner
from conftune.core.backup_manager import BackupManager
from conftune.core.detector import SystemDetector
from conftune.core.dnf_tuner import DNFTuner
from conftune.core.fedy_tuner import FedyTuner
from conftune.core.power_tuner import PowerTuner
from conftune.core.preset_manager import PresetManager
from conftune.core.privacy_tuner import PrivacyTuner
from conftune.core.process_tuner import ProcessTuner
from conftune.core.safety import SafetyEngine
from conftune.core.server_tuner import ServerTuner
from conftune.core.storage_tuner import StorageTuner
from conftune.core.sysctl_tuner import SysctlTuner
from conftune.core.systemd_tuner import SystemdTuner
from conftune.gui.app import MainWindow
from conftune.gui.auth import is_root, prompt_root_required
from conftune.gui.tab_autostart import AutostartTab
from conftune.gui.tab_backups import BackupsTab
from conftune.gui.tab_dnf import DNFTab
from conftune.gui.tab_fedy import FedyTab
from conftune.gui.tab_logs import LogsTab
from conftune.gui.tab_overview import OverviewTab
from conftune.gui.tab_power import PowerTab
from conftune.gui.tab_presets import PresetsTab
from conftune.gui.tab_privacy import PrivacyTab
from conftune.gui.tab_process import ProcessTab
from conftune.gui.tab_profiles import ProfilesTab
from conftune.gui.tab_server import ServerTab
from conftune.gui.tab_specialized import SpecializedTab
from conftune.gui.tab_storage import StorageTab
from conftune.gui.tab_sysctl import SysctlTab
from conftune.gui.tab_systemd import SystemdTab


class TestGUITabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_gui_test_")
        self.safety = SafetyEngine(dry_run=True)
        self.backup_mgr = BackupManager(backup_dir=self.test_dir)
        self.detector = SystemDetector(refresh_on_init=True)
        self.sysctl_tuner = SysctlTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.dnf_tuner = DNFTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.systemd_tuner = SystemdTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.storage_tuner = StorageTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.server_tuner = ServerTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.fedy_tuner = FedyTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.power_tuner = PowerTuner(safety=self.safety)
        self.process_tuner = ProcessTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.autostart_tuner = AutostartTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.privacy_tuner = PrivacyTuner(safety=self.safety)
        self.preset_mgr = PresetManager(safety=self.safety, backup_mgr=self.backup_mgr)

        # Dialog mocks to avoid blocking headless Qt runs
        self.q_patcher = patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel)
        self.mock_q = self.q_patcher.start()
        self.info_patcher = patch.object(QMessageBox, "information")
        self.mock_info = self.info_patcher.start()
        self.warn_patcher = patch.object(QMessageBox, "warning")
        self.mock_warn = self.warn_patcher.start()
        self.crit_patcher = patch.object(QMessageBox, "critical")
        self.mock_crit = self.crit_patcher.start()

    def tearDown(self):
        from conftune.gui.workers import _ACTIVE_WORKERS
        for w in list(_ACTIVE_WORKERS):
            w.wait(1000)
        QCoreApplication.processEvents()

        self.q_patcher.stop()
        self.info_patcher.stop()
        self.warn_patcher.stop()
        self.crit_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_auth_module(self):
        from conftune.gui.auth import SudoAuthDialog
        self.assertIsInstance(is_root(), bool)

        # 1. When safety is in dry-run, prompt_root_required allows action
        safety_dry = SafetyEngine(dry_run=True)
        res_dry = prompt_root_required(None, "Test Action", safety_dry)
        self.assertTrue(res_dry)

        # 2. When safety is unprivileged and user enters sudo password successfully
        safety_user = SafetyEngine(dry_run=False)
        safety_user.is_root = False
        with patch.object(SudoAuthDialog, "exec", return_value=1), \
             patch.object(safety_user, "authenticate_sudo", return_value=(True, "OK")):
            dialog = SudoAuthDialog(None, "Test Privileged Operation", safety_user)
            dialog.txt_password.setText("correct_pass")
            dialog._handle_auth()
            self.assertTrue(dialog.authenticated)

        # 3. When authentication fails, dialog displays error and stays open
        safety_fail = SafetyEngine(dry_run=False)
        safety_fail.is_root = False
        with patch.object(safety_fail, "authenticate_sudo", return_value=(False, "Incorrect password")):
            dialog = SudoAuthDialog(None, "Test Privileged Operation", safety_fail)
            dialog.txt_password.setText("wrong_pass")
            dialog._handle_auth()
            self.assertFalse(dialog.authenticated)
            self.assertFalse(dialog.lbl_error.isHidden())
            self.assertIn("Incorrect password", dialog.lbl_error.text())

        # 4. Fallback warning when no safety engine attached
        res_fallback = prompt_root_required(None, "Test Action")
        self.assertFalse(res_fallback)
        self.mock_warn.assert_called()

    def test_root_locked_offerings_when_unprivileged(self):
        safety_user = SafetyEngine(dry_run=True)
        safety_user.is_root = False

        tab_prof = ProfilesTab(self.sysctl_tuner, self.dnf_tuner, self.systemd_tuner, self.server_tuner, safety_user)
        self.assertIn("🔒", tab_prof.btn_apply.text())
        self.assertNotIn("🔒", tab_prof.btn_apply_dry.text())

        tab_sysctl = SysctlTab(self.sysctl_tuner, safety_user)
        self.assertIn("🔒", tab_sysctl.btn_save.text())

        tab_dnf = DNFTab(self.dnf_tuner, safety_user)
        self.assertIn("🔒", tab_dnf.btn_apply.text())

        tab_storage = StorageTab(self.storage_tuner, safety_user)
        self.assertIn("🔒", tab_storage.btn_enable_trim.text())
        self.assertIn("🔒", tab_storage.btn_run_trim.text())
        self.assertIn("🔒", tab_storage.btn_apply_zram.text())

        tab_fedy = FedyTab(self.fedy_tuner, safety_user)
        self.assertIn("🔒", tab_fedy.btn_install_rf.text())
        self.assertIn("🔒", tab_fedy.btn_install_codecs.text())

        tab_power = PowerTab(self.power_tuner, safety_user)
        self.assertIn("🔒", tab_power.btn_set_gov.text())
        self.assertIn("🔒", tab_power.btn_set_epp.text())
        self.assertIn("🔒", tab_power.btn_set_thp.text())
        self.assertIn("🔒", tab_power.btn_auto_power.text())

        tab_proc = ProcessTab(self.process_tuner, safety_user)
        self.assertIn("🔒", tab_proc.btn_apply_oomd.text())
        self.assertIn("🔒", tab_proc.btn_protect.text())

        tab_serv = ServerTab(self.server_tuner, safety_user)
        self.assertIn("🔒", tab_serv.btn_switch.text())

        tab_back = BackupsTab(self.backup_mgr, safety_user)
        self.assertIn("🔒", tab_back.btn_rollback.text())

        tab_spec = SpecializedTab(self.detector, self.server_tuner, self.sysctl_tuner, safety_user)
        self.assertIn("🔒", tab_spec.btn_opt_vm.text())
        self.assertIn("🔒", tab_spec.btn_opt_c.text())
        self.assertIn("🔒", tab_spec.btn_opt_v.text())

    def test_root_unlocked_offerings_when_privileged(self):
        safety_root = SafetyEngine(dry_run=False)
        safety_root.is_root = True

        tab_prof = ProfilesTab(self.sysctl_tuner, self.dnf_tuner, self.systemd_tuner, self.server_tuner, safety_root)
        self.assertNotIn("🔒", tab_prof.btn_apply.text())

        tab_sysctl = SysctlTab(self.sysctl_tuner, safety_root)
        self.assertNotIn("🔒", tab_sysctl.btn_save.text())

        tab_dnf = DNFTab(self.dnf_tuner, safety_root)
        self.assertNotIn("🔒", tab_dnf.btn_apply.text())

        tab_storage = StorageTab(self.storage_tuner, safety_root)
        self.assertNotIn("🔒", tab_storage.btn_enable_trim.text())
        self.assertNotIn("🔒", tab_storage.btn_run_trim.text())
        self.assertNotIn("🔒", tab_storage.btn_apply_zram.text())

        tab_fedy = FedyTab(self.fedy_tuner, safety_root)
        self.assertNotIn("🔒", tab_fedy.btn_install_rf.text())
        self.assertNotIn("🔒", tab_fedy.btn_install_codecs.text())

        tab_power = PowerTab(self.power_tuner, safety_root)
        self.assertNotIn("🔒", tab_power.btn_set_gov.text())
        self.assertNotIn("🔒", tab_power.btn_auto_power.text())

        tab_proc = ProcessTab(self.process_tuner, safety_root)
        self.assertNotIn("🔒", tab_proc.btn_apply_oomd.text())

        tab_serv = ServerTab(self.server_tuner, safety_root)
        self.assertNotIn("🔒", tab_serv.btn_switch.text())

        tab_back = BackupsTab(self.backup_mgr, safety_root)
        self.assertNotIn("🔒", tab_back.btn_rollback.text())

        tab_spec = SpecializedTab(self.detector, self.server_tuner, self.sysctl_tuner, safety_root)
        self.assertNotIn("🔒", tab_spec.btn_opt_vm.text())
        self.assertNotIn("🔒", tab_spec.btn_opt_c.text())
        self.assertNotIn("🔒", tab_spec.btn_opt_v.text())

    def test_overview_tab(self):
        tab = OverviewTab(self.detector, self.server_tuner, self.storage_tuner)
        self.assertIsNotNone(tab)
        tab.refresh_data()
        self.assertGreater(tab.grid.count(), 0)

    def test_profiles_tab(self):
        tab = ProfilesTab(
            self.sysctl_tuner,
            self.dnf_tuner,
            self.systemd_tuner,
            self.server_tuner,
            self.safety,
        )
        self.assertIsNotNone(tab)
        tab._select_profile("balanced")
        self.assertEqual(tab.selected_profile_id, "balanced")
        tab._select_profile("workstation")
        self.assertEqual(tab.selected_profile_id, "workstation")

        # Test dry run apply
        tab._apply_current_profile(dry_run=True)
        if hasattr(tab, "_current_worker") and tab._current_worker:
            tab._current_worker.wait(2000)
            QCoreApplication.processEvents()

        # Test privileged apply
        self.safety.is_root = True
        tab._apply_current_profile(dry_run=False)
        if hasattr(tab, "_current_worker") and tab._current_worker:
            tab._current_worker.wait(2000)
            QCoreApplication.processEvents()

    def test_sysctl_tab(self):
        tab = SysctlTab(self.sysctl_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._reload_table()
        self.assertGreater(tab.table.rowCount(), 10)
        tab.cat_filter.setCurrentText("Memory & VM")
        self.assertEqual(tab.cat_filter.currentText(), "Memory & VM")

        # Test save unprivileged (triggers prompt)
        self.safety.is_root = False
        tab._save_changes()

        # Test save privileged
        self.safety.is_root = True
        tab._save_changes()

    def test_dnf_tab(self):
        tab = DNFTab(self.dnf_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._load_current()
        tab.spin_dl.setValue(8)
        tab.chk_fastest.setChecked(True)

        # Unprivileged
        self.safety.is_root = False
        tab._apply_dnf()
        tab._clean_dnf_cache()

        # Privileged
        self.safety.is_root = True
        tab._apply_dnf()
        tab._clean_dnf_cache()

    def test_systemd_tab(self):
        tab = SystemdTab(self.systemd_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._refresh()

        # Unprivileged
        self.safety.is_root = False
        tab._toggle_service("bluetooth.service", False)
        tab._apply_journald()

        # Privileged
        self.safety.is_root = True
        tab._toggle_service("bluetooth.service", False)
        tab._apply_journald()

    def test_storage_tab(self):
        tab = StorageTab(self.storage_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._refresh()

        # Unprivileged
        self.safety.is_root = False
        tab._enable_trim()
        tab._run_trim_now()
        tab._configure_zram()

        # Privileged
        self.safety.is_root = True
        tab._enable_trim()
        with patch("conftune.gui.tab_storage.run_async_task") as mock_run:
            tab._run_trim_now()
            mock_run.assert_called()
        tab._configure_zram()

    def test_specialized_tab(self):
        tab = SpecializedTab(
            self.detector,
            self.server_tuner,
            self.sysctl_tuner,
            self.safety,
        )
        self.assertIsNotNone(tab)

        # Unprivileged
        self.safety.is_root = False
        tab._optimize_containers()
        tab._optimize_virtualization()
        tab._optimize_virtualmin()

        # Privileged
        self.safety.is_root = True
        tab._optimize_containers()
        tab._optimize_virtualization()
        tab._optimize_virtualmin()

    def test_fedy_tab(self):
        tab = FedyTab(self.fedy_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._refresh()

        # Unprivileged (root actions trigger prompt, user actions execute)
        self.safety.is_root = False
        tab._install_rpmfusion()
        tab._install_codecs()
        tab._optimize_fonts()
        tab._apply_gnome_tweaks()

        # Privileged
        self.safety.is_root = True
        with patch("conftune.gui.tab_fedy.run_async_task") as mock_fedy_task:
            tab._install_rpmfusion()
            mock_fedy_task.assert_called()
            tab._install_codecs()

    def test_power_tab(self):
        tab = PowerTab(self.power_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._refresh()

        # Unprivileged
        self.safety.is_root = False
        tab._apply_governor()
        tab._apply_epp()
        tab._apply_thp()
        tab._apply_auto_power()

        # Privileged
        self.safety.is_root = True
        tab._apply_governor()
        tab._apply_epp()
        tab._apply_thp()
        tab._apply_auto_power()

    def test_process_tab(self):
        tab = ProcessTab(self.process_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._refresh()

        # Unprivileged
        self.safety.is_root = False
        tab._apply_oomd()
        tab.txt_pname.setText("test_app")
        tab._protect_process()

        # Privileged
        self.safety.is_root = True
        tab._apply_oomd()
        tab.txt_pname.setText("test_app")
        tab._protect_process()

    def test_autostart_tab(self):
        tab = AutostartTab(self.autostart_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._refresh()

        # Unprivileged
        self.safety.is_root = False
        tab._apply_coredump()
        tab._toggle_abrt()
        tab._toggle_entry("/etc/xdg/autostart/test.desktop", False)

        # Privileged
        self.safety.is_root = True
        tab._apply_coredump()
        tab._toggle_abrt()

    def test_privacy_tab(self):
        tab = PrivacyTab(self.privacy_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._disable_all()

    def test_server_tab(self):
        tab = ServerTab(self.server_tuner, self.safety)
        self.assertIsNotNone(tab)
        tab._refresh()

        # Unprivileged
        self.safety.is_root = False
        tab._switch_tuned_profile()

        # Privileged
        self.safety.is_root = True
        tab._switch_tuned_profile()

    def test_presets_tab(self):
        tab = PresetsTab(self.preset_mgr, self.safety)
        self.assertIsNotNone(tab)

        # Export
        out_f = os.path.join(self.test_dir, "export.conftune.tar.gz")
        with patch.object(QFileDialog, "getSaveFileName", return_value=(out_f, "All Files (*)")):
            tab.txt_exp_name.setText("UI Test Preset")
            tab.txt_exp_desc.setText("Testing PresetsTab")
            tab._export_preset()

        self.assertTrue(os.path.isfile(out_f))

        # Import & Preview
        with patch.object(QFileDialog, "getOpenFileName", return_value=(out_f, "All Files (*)")):
            tab._select_import_file()
            self.assertIsNotNone(tab.loaded_preset_data)
            self.assertTrue(tab.btn_apply_preset.isEnabled())

        # Apply Loaded Preset (Unprivileged vs Privileged)
        self.safety.is_root = False
        tab._apply_loaded_preset()
        self.safety.is_root = True
        tab._apply_loaded_preset()

        # Standalone Script
        out_sh = os.path.join(self.test_dir, "deploy_test.sh")
        with patch.object(QFileDialog, "getSaveFileName", return_value=(out_sh, "All Files (*)")):
            tab._generate_deploy_script()
        self.assertTrue(os.path.isfile(out_sh))

        # Kickstart
        out_ks = os.path.join(self.test_dir, "kickstart_test.ks")
        with patch.object(QFileDialog, "getSaveFileName", return_value=(out_ks, "All Files (*)")):
            tab._generate_kickstart()
        self.assertTrue(os.path.isfile(out_ks))

        # Ansible Playbook
        out_yml = os.path.join(self.test_dir, "playbook_test.yml")
        with patch.object(QFileDialog, "getSaveFileName", return_value=(out_yml, "All Files (*)")):
            tab._generate_ansible_playbook()
        self.assertTrue(os.path.isfile(out_yml))

        # Build ISO
        with patch("conftune.gui.tab_presets.run_async_task") as mock_iso_task:
            with patch.object(QFileDialog, "getOpenFileName", return_value=(out_sh, "All Files (*)")):
                with patch.object(QFileDialog, "getSaveFileName", return_value=(os.path.join(self.test_dir, "out.iso"), "All Files (*)")):
                    tab._build_custom_iso()
                    mock_iso_task.assert_called()

    def test_backups_tab(self):
        # Create a mock target and snapshot first
        test_file = os.path.join(self.test_dir, "test.conf")
        with open(test_file, "w") as f:
            f.write("test = 1\n")
        snap_id = self.backup_mgr.create_snapshot("ui_test", [test_file], "UI Test")

        tab = BackupsTab(self.backup_mgr, self.safety)
        self.assertIsNotNone(tab)
        tab._reload_snapshots()
        self.assertGreaterEqual(tab.table.rowCount(), 1)
        tab.table.selectRow(0)
        tab._on_selection_changed()
        self.assertIsNotNone(tab.selected_snap_id)

        # Rollback unprivileged
        self.safety.is_root = False
        tab._perform_rollback()

        # Rollback privileged
        self.safety.is_root = True
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            tab._perform_rollback()

    def test_logs_tab(self):
        tab = LogsTab()
        self.assertIsNotNone(tab)
        tab._on_log_message("Info message test", logging.INFO)
        tab._on_log_message("Warning message test", logging.WARNING)
        tab._on_log_message("Error message test", logging.ERROR)
        self.assertIn("Info message test", tab.log_text.toPlainText())
        self.assertIn("Warning message test", tab.log_text.toPlainText())
        self.assertIn("Error message test", tab.log_text.toPlainText())
        tab._clear_logs()
        self.assertEqual(tab.log_text.toPlainText(), "")

    def test_main_window_full_initialization_and_navigation(self):
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.windowTitle(), "ConfTune FC - Fedora & RPM Performance Tuner")

        # Verify sidebar count and stack count
        self.assertEqual(window.sidebar.count(), 16)
        self.assertEqual(window.stack.count(), 16)

        # Iterate all 16 views
        for i in range(16):
            window.sidebar.setCurrentRow(i)
            self.assertEqual(window.stack.currentIndex(), i)

        # Test elevation method handler
        with patch("conftune.gui.app.prompt_root_required", return_value=True):
            window._elevate_root()
            self.mock_info.assert_called()


if __name__ == "__main__":
    unittest.main()
