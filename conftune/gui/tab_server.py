"""
Server, Security & Tuned Profiles Tab for ConfTune FC.
Manages Red Hat tuned-adm daemon profiles, firewalld zones, SELinux enforcement,
and audits SSH server security parameters.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from conftune.core.safety import SafetyEngine
from conftune.core.server_tuner import ServerTuner
from conftune.gui.auth import prompt_root_required


class ServerTab(QWidget):
    """Server tuning, security posture, and tuned daemon interface."""

    def __init__(self, server_tuner: ServerTuner, safety: SafetyEngine):
        super().__init__()
        self.server_tuner = server_tuner
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
        lbl_title = QLabel("Enterprise Server & Security Configuration")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Manage Red Hat tuned daemon profiles, firewall policies, SELinux, and SSH daemon security.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header)

        # Tuned Card
        tuned_card = QFrame()
        tuned_card.setProperty("class", "card")
        t_lay = QVBoxLayout(tuned_card)
        t_lay.setSpacing(10)

        lbl_t_head = QLabel("Red Hat Tuned Dynamic Tuning Daemon (tuned-adm)")
        lbl_t_head.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        t_lay.addWidget(lbl_t_head)

        h_ts = QHBoxLayout()
        self.lbl_active_tuned = QLabel("Active Profile: Querying...")
        self.lbl_active_tuned.setStyleSheet("color: #dedede; font-weight: 500;")
        h_ts.addWidget(self.lbl_active_tuned)
        h_ts.addStretch()

        lbl_sw = QLabel("Switch Profile:")
        self.combo_tuned = QComboBox()
        sw_btn_lbl = "Switch Profile" if self.safety.is_root else "🔒 Switch Profile (Requires Root)"
        self.btn_switch = QPushButton(sw_btn_lbl)
        self.btn_switch.clicked.connect(self._switch_tuned_profile)
        h_ts.addWidget(lbl_sw)
        h_ts.addWidget(self.combo_tuned)
        h_ts.addWidget(self.btn_switch)
        t_lay.addLayout(h_ts)

        layout.addWidget(tuned_card)

        # Security Overview: SELinux & Firewalld
        sec_card = QFrame()
        sec_card.setProperty("class", "card")
        s_lay = QVBoxLayout(sec_card)
        s_lay.setSpacing(8)

        lbl_s_head = QLabel("Security Baselines: SELinux & Firewalld")
        lbl_s_head.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        s_lay.addWidget(lbl_s_head)

        self.lbl_sec_info = QLabel("Checking security state...")
        self.lbl_sec_info.setStyleSheet("color: #dedede; font-size: 13px; line-height: 1.4;")
        s_lay.addWidget(self.lbl_sec_info)
        layout.addWidget(sec_card)

        # SSH Audit Table
        lbl_ssh = QLabel("SSH Server Configuration Security Audit (/etc/ssh/sshd_config)")
        lbl_ssh.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_ssh)

        self.table_ssh = QTableWidget()
        self.table_ssh.setColumnCount(4)
        self.table_ssh.setHorizontalHeaderLabels(["Directive", "Current Setting", "Recommended", "Status"])
        self.table_ssh.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_ssh.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_ssh.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_ssh.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_ssh.setAlternatingRowColors(True)
        layout.addWidget(self.table_ssh)

        layout.addStretch()
        self._refresh()

    def _refresh(self):
        # Tuned
        t_info = self.server_tuner.get_tuned_status()
        self.lbl_active_tuned.setText(f"Active Profile: {t_info.get('active_profile')}")
        self.combo_tuned.clear()
        for p in t_info.get("available_profiles", []):
            self.combo_tuned.addItem(p)
        if t_info.get("active_profile") in t_info.get("available_profiles", []):
            self.combo_tuned.setCurrentText(t_info.get("active_profile"))

        # Security
        se = self.server_tuner.get_selinux_status()
        fw = self.server_tuner.get_firewalld_status()
        fw_status = "Running" if fw.get("running") else "Stopped"
        open_s = ", ".join(fw.get("open_services", [])) or "None"
        open_p = ", ".join(fw.get("open_ports", [])) or "None"

        sec_text = (
            f"• <b>SELinux Mode:</b> {se}<br>"
            f"• <b>Firewalld:</b> {fw_status} (Zone: {fw.get('default_zone')})<br>"
            f"• <b>Allowed Services:</b> {open_s}<br>"
            f"• <b>Explicit Ports:</b> {open_p}"
        )
        self.lbl_sec_info.setText(sec_text)

        # SSH Audit
        audit = self.server_tuner.audit_ssh_config()
        self.table_ssh.setRowCount(len(audit))
        for row, item in enumerate(audit):
            self.table_ssh.setItem(row, 0, QTableWidgetItem(item["param"]))
            self.table_ssh.setItem(row, 1, QTableWidgetItem(item["current"]))
            self.table_ssh.setItem(row, 2, QTableWidgetItem(item["recommendation"]))
            it_st = QTableWidgetItem(item["status"])
            if item["status"] == "OK":
                it_st.setForeground(Qt.GlobalColor.green)
            else:
                it_st.setForeground(Qt.GlobalColor.yellow)
            self.table_ssh.setItem(row, 3, it_st)

    def _switch_tuned_profile(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Switch Red Hat Tuned Profile", self.safety):
                return
        new_prof = self.combo_tuned.currentText()
        if not new_prof:
            return
        ok, msg = self.server_tuner.set_tuned_profile(new_prof)
        QMessageBox.information(self, "Tuned Profile Switched", msg)
        self._refresh()
