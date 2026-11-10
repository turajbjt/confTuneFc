"""
Systemd Boot and Daemon Optimizer Tab for ConfTune FC.
Analyzes boot bottlenecks with systemd-analyze blame and manages service states.
"""

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from conftune.core.safety import SafetyEngine
from conftune.core.systemd_tuner import SystemdTuner
from conftune.gui.auth import prompt_root_required


class SystemdTab(QWidget):
    """Boot speed analyzer and systemd service management."""

    def __init__(self, systemd_tuner: SystemdTuner, safety: SafetyEngine):
        super().__init__()
        self.systemd_tuner = systemd_tuner
        self.safety = safety
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Card
        header = QFrame()
        header.setProperty("class", "card")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 12, 16, 12)

        v_box = QVBoxLayout()
        lbl_title = QLabel("Systemd Boot Performance & Service Optimizer")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        self.lbl_boot_time = QLabel("Analyzing boot time...")
        self.lbl_boot_time.setStyleSheet("color: #99c1f1; font-size: 12px; font-weight: 500;")
        v_box.addWidget(lbl_title)
        v_box.addWidget(self.lbl_boot_time)
        h_lay.addLayout(v_box)
        h_lay.addStretch()

        # Journald size cap selector
        v_j = QVBoxLayout()
        self.lbl_j_status = QLabel("Checking journald...")
        self.lbl_j_status.setStyleSheet("font-size: 11px; font-weight: 500;")
        v_j.addWidget(self.lbl_j_status)

        h_j = QHBoxLayout()
        lbl_j = QLabel("Journald Max Size:")
        lbl_j.setStyleSheet("color: #dedede; font-size: 12px;")
        self.combo_j = QComboBox()
        self.combo_j.addItems(["200M", "300M", "500M", "1G"])
        self.combo_j.setCurrentText("300M")
        btn_apply_j = QPushButton("Apply Limit" if self.safety.is_root else "🔒 Apply Limit (Requires Root)")
        btn_apply_j.setProperty("class", "primary")
        btn_apply_j.clicked.connect(self._apply_journald)

        reset_j_lbl = "↺ Reset to Default (Undo)" if self.safety.is_root else "🔒 ↺ Reset (Root)"
        self.btn_reset_j = QPushButton(reset_j_lbl)
        self.btn_reset_j.setToolTip("Remove /etc/systemd/journald.conf.d/99-conftune.conf and restore system default limits")
        self.btn_reset_j.clicked.connect(self._reset_journald)

        if not self.safety.is_root:
            self.combo_j.setEnabled(False)
            btn_apply_j.setEnabled(False)
            btn_apply_j.setToolTip("Root privileges required to set journald size limits")
            self.btn_reset_j.setEnabled(False)
            self.btn_reset_j.setToolTip("Root privileges required to restore journald limits in /etc/systemd/")

        h_j.addWidget(lbl_j)
        h_j.addWidget(self.combo_j)
        h_j.addWidget(btn_apply_j)
        h_j.addWidget(self.btn_reset_j)
        v_j.addLayout(h_j)
        h_lay.addLayout(v_j)

        layout.addWidget(header)

        # Blame Table
        lbl_table_header = QLabel("Top Boot Delay Services (systemd-analyze blame)")
        lbl_table_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_table_header)

        self.table_blame = QTableWidget()
        self.table_blame.setColumnCount(2)
        self.table_blame.setHorizontalHeaderLabels(["Startup Time", "Service / Unit Name"])
        self.table_blame.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_blame.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_blame.setAlternatingRowColors(True)
        self.table_blame.setMinimumHeight(240)
        self.table_blame.verticalHeader().setDefaultSectionSize(30)
        self.table_blame.verticalHeader().setVisible(False)
        layout.addWidget(self.table_blame)

        # Server Daemon Recommendations
        lbl_rec_header = QLabel("Recommended Server Service Optimizations")
        lbl_rec_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff; margin-top: 6px;")
        layout.addWidget(lbl_rec_header)

        self.table_rec = QTableWidget()
        self.table_rec.setColumnCount(4)
        self.table_rec.setHorizontalHeaderLabels(["Service", "State", "Description", "Action"])
        self.table_rec.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_rec.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_rec.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_rec.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table_rec.setColumnWidth(3, 195)
        self.table_rec.setMinimumHeight(260)
        self.table_rec.verticalHeader().setDefaultSectionSize(44)
        self.table_rec.verticalHeader().setVisible(False)
        self.table_rec.setAlternatingRowColors(True)
        layout.addWidget(self.table_rec)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._refresh()

    def _refresh(self):
        self.lbl_boot_time.setText(f"Boot Duration: {self.systemd_tuner.get_boot_time_summary()}")

        # Journald status
        if self.systemd_tuner.is_journald_configured():
            self.lbl_j_status.setText("Status: 🟢 Custom journald cap active (/etc/systemd/journald.conf.d/99-conftune.conf)")
            self.lbl_j_status.setStyleSheet("color: #57e389; font-size: 11px; font-weight: 500;")
        else:
            self.lbl_j_status.setText("Status: ⚪ Fedora default journald limits active")
            self.lbl_j_status.setStyleSheet("color: #99c1f1; font-size: 11px; font-weight: 500;")

        # Blame
        items = self.systemd_tuner.get_boot_blame(top_n=15)
        self.table_blame.setRowCount(len(items))
        for row, it in enumerate(items):
            dur_item = QTableWidgetItem(it["duration"])
            unit_item = QTableWidgetItem(it["unit"])
            self.table_blame.setItem(row, 0, dur_item)
            self.table_blame.setItem(row, 1, unit_item)

        # Recs
        recs = self.systemd_tuner.get_server_removable_services()
        self.table_rec.clearContents()
        self.table_rec.setRowCount(len(recs))
        for row, r in enumerate(recs):
            it_name = QTableWidgetItem(r["service"])
            state_str = "Active" if r["active"] else "Inactive"
            it_state = QTableWidgetItem(state_str)
            it_desc = QTableWidgetItem(r["description"])

            action_text = "Disable" if r["active"] else "Enable"
            btn_label = action_text if self.safety.is_root else f"🔒 {action_text} (Root)"
            btn_toggle = QPushButton(btn_label)
            btn_toggle.setFixedHeight(32)
            btn_toggle.setMinimumWidth(160)
            btn_toggle.setEnabled(self.safety.is_root)
            if not self.safety.is_root:
                btn_toggle.setToolTip("Root privileges required to enable/disable system services")
            if r["active"]:
                btn_toggle.setProperty("class", "destructive")
                btn_toggle.style().unpolish(btn_toggle)
                btn_toggle.style().polish(btn_toggle)
            btn_toggle.clicked.connect(lambda ch, s=r["service"], act=r["active"]: self._toggle_service(s, not act))

            self.table_rec.setItem(row, 0, it_name)
            self.table_rec.setItem(row, 1, it_state)
            self.table_rec.setItem(row, 2, it_desc)
            self.table_rec.setCellWidget(row, 3, btn_toggle)

    def _toggle_service(self, service: str, enable: bool):
        if not self.safety.is_root:
            if not prompt_root_required(self, f"Modifying system service '{service}'", self.safety):
                return

        ok, msg = self.systemd_tuner.set_service_state(service, enable)
        QMessageBox.information(self, "Service Updated", msg)
        self._refresh()

    def _apply_journald(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Configuring systemd-journald limits in /etc/systemd/journald.conf.d", self.safety):
                return

        size = self.combo_j.currentText()
        ok, msg = self.systemd_tuner.configure_journald_limit(size)
        self._refresh()
        QMessageBox.information(self, "Journald Limit Applied", msg)

    def _reset_journald(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Restore default systemd-journald limits", self.safety):
                return

        reply = QMessageBox.question(
            self,
            "Reset Journald Limits",
            "Are you sure you want to remove /etc/systemd/journald.conf.d/99-conftune.conf and restore system default log size caps?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.systemd_tuner.restore_default_journald()
        self._refresh()
        QMessageBox.information(self, "Journald Defaults Restored", msg)
