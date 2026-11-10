"""
Tuning Profiles Tab for ConfTune FC.
Displays profile cards with diff preview and 1-click optimization application.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from conftune.core.dnf_tuner import DNFTuner
from conftune.core.profiles import PROFILES, list_profiles
from conftune.core.safety import SafetyEngine
from conftune.core.server_tuner import ServerTuner
from conftune.core.sysctl_tuner import SysctlTuner
from conftune.core.systemd_tuner import SystemdTuner
from conftune.gui.auth import prompt_root_required
from conftune.gui.workers import run_async_task


class ProfilesTab(QWidget):
    """Preset Profiles View with live diff and 1-click execution."""

    profile_applied = pyqtSignal(str)

    def __init__(
        self,
        sysctl_tuner: SysctlTuner,
        dnf_tuner: DNFTuner,
        systemd_tuner: SystemdTuner,
        server_tuner: ServerTuner,
        safety: SafetyEngine,
    ):
        super().__init__()
        self.sysctl_tuner = sysctl_tuner
        self.dnf_tuner = dnf_tuner
        self.systemd_tuner = systemd_tuner
        self.server_tuner = server_tuner
        self.safety = safety
        self.selected_profile_id = "balanced"
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(10)

        # Header Card - compact sizing to prevent unnecessary vertical expansion
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(16, 8, 16, 8)

        v_text = QVBoxLayout()
        v_text.setSpacing(2)
        lbl_title = QLabel("Tuning Profiles & Workload Presets")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Select a tailored profile for your Fedora desktop or Rocky / CentOS server workloads.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        v_text.addWidget(lbl_title)
        v_text.addWidget(lbl_sub)
        h_layout.addLayout(v_text)
        h_layout.addStretch()

        self.btn_apply_dry = QPushButton("Simulate (Dry Run)")
        self.btn_apply_dry.clicked.connect(lambda: self._apply_current_profile(dry_run=True))
        h_layout.addWidget(self.btn_apply_dry)

        self.btn_apply = QPushButton("🚀 Apply Profile" if self.safety.is_root else "🔒 Apply Profile (Requires Root)")
        self.btn_apply.setProperty("class", "primary")
        if not self.safety.is_root:
            self.btn_apply.setEnabled(False)
            self.btn_apply.setToolTip("Root privileges required to apply system tuning profiles. Use Elevate or run with sudo.")
        self.btn_apply.clicked.connect(lambda: self._apply_current_profile(dry_run=False))
        h_layout.addWidget(self.btn_apply)

        main_layout.addWidget(header_card)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        main_layout.addWidget(self.progress)

        # Splitter: Left Profile Cards, Right Details/Diff
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Profiles List
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)

        left_widget = QWidget()
        self.cards_layout = QVBoxLayout(left_widget)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)

        self.profile_buttons = {}
        for p in list_profiles():
            card = self._create_profile_card(p)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)

        # Right: Details / Diff Preview
        right_card = QFrame()
        right_card.setProperty("class", "card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(8)

        lbl_det = QLabel("Profile Parameter Details & Preview")
        lbl_det.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        right_layout.addWidget(lbl_det)

        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setStyleSheet("font-family: monospace; font-size: 12px; line-height: 1.4;")
        right_layout.addWidget(self.txt_details)

        splitter.addWidget(right_card)
        splitter.setSizes([380, 520])

        main_layout.addWidget(splitter, 1)

        self._select_profile("balanced")

    def _create_profile_card(self, prof: dict) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet("QFrame:hover { border-color: #3584e4; background-color: #2b2b2b; }")
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(12, 8, 12, 8)
        c_lay.setSpacing(3)

        h_box = QHBoxLayout()
        lbl_name = QLabel(f"{prof['icon']} {prof['name']}")
        lbl_name.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        h_box.addWidget(lbl_name)
        h_box.addStretch()

        badge = QLabel(prof.get("category", "General"))
        badge.setStyleSheet("background-color: #383838; color: #99c1f1; border-radius: 8px; padding: 2px 6px; font-size: 10px;")
        h_box.addWidget(badge)
        c_lay.addLayout(h_box)

        lbl_desc = QLabel(prof.get("description", ""))
        lbl_desc.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        c_lay.addWidget(lbl_desc)

        card.mousePressEvent = lambda event, pid=prof["id"]: self._select_profile(pid)
        self.profile_buttons[prof["id"]] = card
        return card

    def _select_profile(self, profile_id: str):
        self.selected_profile_id = profile_id
        for pid, card in self.profile_buttons.items():
            if pid == profile_id:
                card.setStyleSheet("border: 2px solid #3584e4; background-color: #2e353f;")
            else:
                card.setStyleSheet("QFrame:hover { border-color: #3584e4; background-color: #2b2b2b; }")

        prof = PROFILES.get(profile_id, {})
        details = [
            f"# Profile: {prof.get('name')}",
            f"# Category: {prof.get('category')}",
            f"# Purpose: {prof.get('description')}",
            f"# Rationale: {prof.get('notes')}",
            "",
            "--- Red Hat Tuned Daemon ---",
            f"tuned-adm profile: {prof.get('tuned_profile', 'None')}",
            "",
            "--- Systemd Journal Storage Cap ---",
            f"journald SystemMaxUse: {prof.get('journald_max', 'Default')}",
            "",
            "--- Kernel & Network Sysctl Settings ---",
        ]
        for k, v in prof.get("sysctl", {}).items():
            live = self.sysctl_tuner.get_live_value(k)
            details.append(f"{k} = {v:<20} # (Current live value: {live})")

        details.append("")
        details.append("--- DNF Package Manager Acceleration ---")
        for k, v in prof.get("dnf_settings", {}).items():
            details.append(f"{k} = {v}")

        self.txt_details.setText("\n".join(details))

    def _apply_current_profile(self, dry_run: bool):
        prof = PROFILES.get(self.selected_profile_id)
        if not prof:
            return

        if not dry_run and not self.safety.is_root:
            if not prompt_root_required(self, "Applying this tuning profile to system configuration files", self.safety):
                return

        self.progress.setVisible(True)
        self.btn_apply.setEnabled(False)
        self.btn_apply_dry.setEnabled(False)

        def task():
            old_sysctl_dry = self.sysctl_tuner.safety.dry_run
            old_dnf_dry = self.dnf_tuner.safety.dry_run
            old_systemd_dry = self.systemd_tuner.safety.dry_run
            old_server_dry = self.server_tuner.safety.dry_run

            self.sysctl_tuner.safety.dry_run = dry_run
            self.dnf_tuner.safety.dry_run = dry_run
            self.systemd_tuner.safety.dry_run = dry_run
            self.server_tuner.safety.dry_run = dry_run

            try:
                results = []
                # 1. Sysctl
                ok_s, msg_s = self.sysctl_tuner.apply_parameters(prof["sysctl"], profile_name=prof["name"])
                results.append(msg_s)

                # 2. DNF
                dnf_cfg = prof.get("dnf_settings", {})
                ok_d, msg_d = self.dnf_tuner.apply_optimizations(
                    max_parallel_downloads=dnf_cfg.get("max_parallel_downloads", 10),
                    fastestmirror=dnf_cfg.get("fastestmirror", True),
                )
                results.append(msg_d)

                # 3. Journald
                ok_j, msg_j = self.systemd_tuner.configure_journald_limit(prof.get("journald_max", "300M"))
                results.append(msg_j)

                # 4. Tuned
                if prof.get("tuned_profile"):
                    ok_t, msg_t = self.server_tuner.set_tuned_profile(prof["tuned_profile"])
                    results.append(msg_t)

                return True, "\n".join(results)
            except Exception as e:
                return False, f"Error during profile execution: {e}"
            finally:
                self.sysctl_tuner.safety.dry_run = old_sysctl_dry
                self.dnf_tuner.safety.dry_run = old_dnf_dry
                self.systemd_tuner.safety.dry_run = old_systemd_dry
                self.server_tuner.safety.dry_run = old_server_dry

        def on_done(success: bool, message: str, payload):
            self.progress.setVisible(False)
            self.btn_apply.setEnabled(True)
            self.btn_apply_dry.setEnabled(True)
            self._select_profile(self.selected_profile_id)
            self.profile_applied.emit(self.selected_profile_id)

            title = "Simulation Results" if dry_run else "Profile Applied Successfully"
            if success:
                QMessageBox.information(self, title, message)
            else:
                QMessageBox.warning(self, "Tuning Alert", message)

        self._current_worker = run_async_task(task, on_done, parent=self)
