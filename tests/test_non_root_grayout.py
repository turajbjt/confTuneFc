"""
Unit tests verifying that all root-only controls are grayed out (disabled)
when ConfTune FC runs as a normal unprivileged user.
"""

import os
import unittest
from PyQt6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication([])

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
from conftune.gui.tab_backups import BackupsTab
from conftune.gui.tab_dnf import DNFTab
from conftune.gui.tab_fedy import FedyTab
from conftune.gui.tab_power import PowerTab
from conftune.gui.tab_presets import PresetsTab
from conftune.gui.tab_process import ProcessTab
from conftune.gui.tab_profiles import ProfilesTab
from conftune.gui.tab_server import ServerTab
from conftune.gui.tab_specialized import SpecializedTab
from conftune.gui.tab_storage import StorageTab
from conftune.gui.tab_sysctl import SysctlTab
from conftune.gui.tab_systemd import SystemdTab


class TestNonRootGrayout(unittest.TestCase):
    def setUp(self):
        self.safety_user = SafetyEngine(dry_run=False)
        self.safety_user.is_root = False
        self.backup_mgr = BackupManager()
        self.detector = SystemDetector()

    def test_profiles_tab_non_root(self):
        tab = ProfilesTab(
            sysctl_tuner=SysctlTuner(self.safety_user, self.backup_mgr),
            dnf_tuner=DNFTuner(self.safety_user, self.backup_mgr),
            systemd_tuner=SystemdTuner(self.safety_user, self.backup_mgr),
            server_tuner=ServerTuner(self.safety_user),
            safety=self.safety_user,
        )
        self.assertFalse(tab.btn_apply.isEnabled(), "Apply Profile must be disabled for non-root")

    def test_dnf_tab_non_root(self):
        tab = DNFTab(DNFTuner(self.safety_user, self.backup_mgr), self.safety_user)
        self.assertFalse(tab.spin_dl.isEnabled())
        self.assertFalse(tab.chk_fastest.isEnabled())
        self.assertFalse(tab.chk_defaultyes.isEnabled())
        self.assertFalse(tab.chk_keepcache.isEnabled())
        self.assertFalse(tab.btn_apply.isEnabled())
        self.assertFalse(tab.btn_reset.isEnabled())
        self.assertFalse(tab.btn_clean.isEnabled())
        # Refresh button should remain enabled
        self.assertTrue(tab.btn_reload.isEnabled())

    def test_fedy_tab_non_root(self):
        tab = FedyTab(FedyTuner(self.safety_user, self.backup_mgr), self.safety_user)
        self.assertFalse(tab.btn_install_rf.isEnabled(), "RPM Fusion toggle must be disabled for non-root")
        self.assertFalse(tab.btn_install_codecs.isEnabled(), "Codec installation must be disabled for non-root")
        # User-level tweaks must remain enabled
        self.assertTrue(tab.chk_min.isEnabled())
        self.assertTrue(tab.chk_max.isEnabled())
        self.assertTrue(tab.chk_bat.isEnabled())

    def test_sysctl_tab_non_root(self):
        tab = SysctlTab(SysctlTuner(self.safety_user, self.backup_mgr), self.safety_user)
        self.assertFalse(tab.btn_save.isEnabled(), "Save Overrides must be disabled for non-root")
        self.assertFalse(tab.btn_reset_defaults.isEnabled(), "Reset Defaults must be disabled for non-root")

    def test_storage_tab_non_root(self):
        tab = StorageTab(StorageTuner(self.safety_user, self.backup_mgr), self.safety_user)
        self.assertFalse(tab.btn_enable_trim.isEnabled(), "Enable TRIM must be disabled for non-root")
        self.assertFalse(tab.btn_run_trim.isEnabled(), "Run TRIM discard must be disabled for non-root")
        self.assertFalse(tab.btn_apply_zram.isEnabled(), "Configure ZRAM must be disabled for non-root")
        self.assertFalse(tab.btn_restore_zram.isEnabled(), "Restore ZRAM must be disabled for non-root")

    def test_systemd_tab_non_root(self):
        tab = SystemdTab(SystemdTuner(self.safety_user, self.backup_mgr), self.safety_user)
        self.assertFalse(tab.combo_j.isEnabled(), "Journald size selector must be disabled for non-root")
        self.assertFalse(tab.btn_reset_j.isEnabled(), "Reset Journald must be disabled for non-root")

    def test_process_tab_non_root(self):
        tab = ProcessTab(ProcessTuner(self.safety_user, self.backup_mgr), self.safety_user)
        self.assertFalse(tab.combo_press.isEnabled(), "Memory pressure selector must be disabled for non-root")
        self.assertFalse(tab.combo_swap.isEnabled(), "Swap limit selector must be disabled for non-root")
        self.assertFalse(tab.btn_apply_oomd.isEnabled(), "Apply oomd limits must be disabled for non-root")
        self.assertFalse(tab.btn_reset_oomd.isEnabled(), "Reset oomd must be disabled for non-root")
        self.assertFalse(tab.txt_pname.isEnabled(), "Process name input must be disabled for non-root")
        self.assertFalse(tab.spin_score.isEnabled(), "Score adjust must be disabled for non-root")
        self.assertFalse(tab.btn_protect.isEnabled(), "Protect process button must be disabled for non-root")

    def test_power_tab_non_root(self):
        tab = PowerTab(PowerTuner(self.safety_user), self.safety_user)
        self.assertFalse(tab.btn_auto_power.isEnabled(), "Auto power button must be disabled for non-root")
        self.assertFalse(tab.combo_gov.isEnabled(), "Governor combo must be disabled for non-root")
        self.assertFalse(tab.btn_set_gov.isEnabled(), "Apply governor button must be disabled for non-root")
        self.assertFalse(tab.combo_epp.isEnabled(), "EPP combo must be disabled for non-root")
        self.assertFalse(tab.btn_set_epp.isEnabled(), "Apply EPP button must be disabled for non-root")
        self.assertFalse(tab.combo_thp.isEnabled(), "THP combo must be disabled for non-root")
        self.assertFalse(tab.btn_set_thp.isEnabled(), "Apply THP button must be disabled for non-root")

    def test_server_tab_non_root(self):
        tab = ServerTab(ServerTuner(self.safety_user), self.safety_user)
        self.assertFalse(tab.combo_tuned.isEnabled(), "Tuned combo must be disabled for non-root")
        self.assertFalse(tab.btn_switch.isEnabled(), "Switch tuned button must be disabled for non-root")

    def test_specialized_tab_non_root(self):
        tab = SpecializedTab(
            self.detector,
            ServerTuner(self.safety_user),
            SysctlTuner(self.safety_user, self.backup_mgr),
            self.safety_user,
        )
        self.assertFalse(tab.btn_opt_vm.isEnabled(), "Virtualmin optimization must be disabled for non-root")
        self.assertFalse(tab.btn_opt_c.isEnabled(), "Container host optimization must be disabled for non-root")
        self.assertFalse(tab.btn_opt_v.isEnabled(), "Virtualization optimization must be disabled for non-root")

    def test_backups_tab_non_root(self):
        tab = BackupsTab(self.backup_mgr, self.safety_user)
        self.assertFalse(tab.btn_rollback.isEnabled(), "Rollback to snapshot must be disabled for non-root")

    def test_presets_tab_non_root(self):
        tab = PresetsTab(PresetManager(), self.safety_user)
        self.assertFalse(tab.btn_apply_preset.isEnabled(), "Apply preset must be disabled for non-root")


if __name__ == "__main__":
    unittest.main()
