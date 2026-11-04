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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from conftune.core.safety import SafetyEngine
from conftune.core.systemd_tuner import SystemdTuner


class SystemdTab(QWidget):
    """Boot speed analyzer and systemd service management."""

    def __init__(self, systemd_tuner: SystemdTuner, safety: SafetyEngine):
        super().__init__()
        self.systemd_tuner = systemd_tuner
        self.safety = safety
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
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
        h_j = QHBoxLayout()
        lbl_j = QLabel("Journald Max Size:")
        lbl_j.setStyleSheet("color: #dedede; font-size: 12px;")
        self.combo_j = QComboBox()
        self.combo_j.addItems(["200M", "300M", "500M", "1G"])
        self.combo_j.setCurrentText("300M")
        btn_apply_j = QPushButton("Apply Limit")
        btn_apply_j.clicked.connect(self._apply_journald)
        h_j.addWidget(lbl_j)
        h_j.addWidget(self.combo_j)
        h_j.addWidget(btn_apply_j)
        h_lay.addLayout(h_j)

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
        self.table_rec.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_rec.setAlternatingRowColors(True)
        layout.addWidget(self.table_rec)

        self._refresh()

    def _refresh(self):
        self.lbl_boot_time.setText(f"Boot Duration: {self.systemd_tuner.get_boot_time_summary()}")

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
        self.table_rec.setRowCount(len(recs))
        for row, r in enumerate(recs):
            it_name = QTableWidgetItem(r["service"])
            state_str = "Active" if r["active"] else "Inactive"
            it_state = QTableWidgetItem(state_str)
            it_desc = QTableWidgetItem(r["description"])

            btn_toggle = QPushButton("Disable" if r["active"] else "Enable")
            if r["active"]:
                btn_toggle.setProperty("class", "destructive")
            btn_toggle.clicked.connect(lambda ch, s=r["service"], act=r["active"]: self._toggle_service(s, not act))

            self.table_rec.setItem(row, 0, it_name)
            self.table_rec.setItem(row, 1, it_state)
            self.table_rec.setItem(row, 2, it_desc)
            self.table_rec.setCellWidget(row, 3, btn_toggle)

    def _toggle_service(self, service: str, enable: bool):
        dry_run = not self.safety.is_root
        ok, msg = self.systemd_tuner.set_service_state(service, enable)
        title = "Simulation Results" if dry_run else "Service Updated"
        QMessageBox.information(self, title, msg)
        self._refresh()

    def _apply_journald(self):
        size = self.combo_j.currentText()
        dry_run = not self.safety.is_root
        ok, msg = self.systemd_tuner.configure_journald_limit(size)
        title = "Simulation Results" if dry_run else "Journald Limit Applied"
        QMessageBox.information(self, title, msg)
