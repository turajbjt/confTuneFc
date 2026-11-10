"""
Privacy & Telemetry Opt-Out Tab for ConfTune FC.
Inspired by O&O ShutUp. Manages desktop metrics, problem reporting, and privacy baselines.
"""

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from conftune.core.privacy_tuner import PrivacyTuner
from conftune.core.safety import SafetyEngine


class PrivacyTab(QWidget):
    """Privacy baselines and telemetry opt-out interface."""

    def __init__(self, privacy_tuner: PrivacyTuner, safety: SafetyEngine):
        super().__init__()
        self.privacy_tuner = privacy_tuner
        self.safety = safety
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header Card
        header = QFrame()
        header.setProperty("class", "card")
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(16, 12, 16, 12)
        lbl_title = QLabel("Privacy, Telemetry & Background Metrics")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("One-click privacy enforcement: opt out of GNOME software usage statistics, automated bug reporting, and telemetry.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header)

        # Privacy Card
        priv_card = QFrame()
        priv_card.setProperty("class", "card")
        p_lay = QVBoxLayout(priv_card)
        p_lay.setSpacing(12)
        p_lay.setContentsMargins(16, 16, 16, 16)

        lbl_p_h = QLabel("🛡️ 1-Click Strict Privacy Enforcement")
        lbl_p_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        p_lay.addWidget(lbl_p_h)

        self.lbl_status = QLabel("Checking telemetry status...")
        self.lbl_status.setStyleSheet("color: #dedede; font-size: 12px; font-weight: 500;")
        p_lay.addWidget(self.lbl_status)

        lbl_desc = QLabel(
            "• Disables GNOME Software usage statistics and metrics collection.<br>"
            "• Disables automatic transmission of technical problem reports and crash logs.<br>"
            "• Configures systemd-coredump to prevent external crash transmission.<br>"
            "• Minimizes background network telemetry wakeups."
        )
        lbl_desc.setStyleSheet("color: #dedede; font-size: 13px; line-height: 1.5;")
        p_lay.addWidget(lbl_desc)

        h_btn = QHBoxLayout()
        self.btn_disable_all = QPushButton("🚫 Disable All Telemetry & Reporting")
        self.btn_disable_all.setProperty("class", "primary")
        self.btn_disable_all.clicked.connect(self._disable_all)
        h_btn.addWidget(self.btn_disable_all)

        self.btn_restore = QPushButton("↺ Restore Default Telemetry & Reporting (Undo)")
        self.btn_restore.setToolTip("Re-enable standard Fedora automatic bug reporting and GNOME usage statistics")
        self.btn_restore.clicked.connect(self._restore_defaults)
        h_btn.addWidget(self.btn_restore)

        h_btn.addStretch()
        p_lay.addLayout(h_btn)

        layout.addWidget(priv_card)
        layout.addStretch()
        self._refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _refresh(self):
        is_hardened = self.privacy_tuner.is_telemetry_disabled()
        if is_hardened:
            self.lbl_status.setText("Status: 🟢 Strict Privacy Mode Active (Telemetry, Metrics & Crash Reporting disabled)")
            self.lbl_status.setStyleSheet("color: #57e389; font-size: 12px; font-weight: 500;")
        else:
            self.lbl_status.setText("Status: ⚪ Standard Fedora Telemetry Settings Active (Default)")
            self.lbl_status.setStyleSheet("color: #99c1f1; font-size: 12px; font-weight: 500;")

    def _disable_all(self):
        ok, msg = self.privacy_tuner.disable_all_telemetry()
        self._refresh()
        QMessageBox.information(self, "Privacy Configured", msg)

    def _restore_defaults(self):
        reply = QMessageBox.question(
            self,
            "Restore Telemetry Defaults",
            "Restore standard Fedora defaults for automatic problem reporting and GNOME metrics?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.privacy_tuner.restore_telemetry_defaults()
        self._refresh()
        QMessageBox.information(self, "Telemetry Defaults Restored", msg)
