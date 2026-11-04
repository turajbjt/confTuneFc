"""
Autostart Applications & Crash Dump Limiter Tab for ConfTune FC.
Inspired by Stacer. Manages autostart launchers, core dump storage, and ABRT services.
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

from conftune.core.autostart_tuner import AutostartTuner
from conftune.core.safety import SafetyEngine


class AutostartTab(QWidget):
    """Autostart manager, systemd-coredump limits, and ABRT daemon controls."""

    def __init__(self, autostart_tuner: AutostartTuner, safety: SafetyEngine):
        super().__init__()
        self.autostart_tuner = autostart_tuner
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
        lbl_title = QLabel("Autostart Applications & Crash Dump Limiter")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Control apps launching on login, cap core dump disk consumption, and manage ABRT daemons.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        v_box.addWidget(lbl_title)
        v_box.addWidget(lbl_sub)
        h_lay.addLayout(v_box)
        h_lay.addStretch()

        btn_ref = QPushButton("🔄 Refresh")
        btn_ref.clicked.connect(self._refresh)
        h_lay.addWidget(btn_ref)
        layout.addWidget(header)

        # Autostart Table
        lbl_table = QLabel("Discovered Login Autostart Applications")
        lbl_table.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_table)

        self.table_auto = QTableWidget()
        self.table_auto.setColumnCount(4)
        self.table_auto.setHorizontalHeaderLabels(["Application Name", "Scope", "Command Exec", "Action"])
        self.table_auto.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_auto.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_auto.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_auto.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_auto.setAlternatingRowColors(True)
        layout.addWidget(self.table_auto)

        # Bottom Utilities: Core Dump Limit & ABRT
        h_util = QHBoxLayout()

        # Core dump card
        cd_card = QFrame()
        cd_card.setProperty("class", "card")
        cd_lay = QVBoxLayout(cd_card)
        lbl_cd = QLabel("💾 systemd-coredump Disk Storage Ceiling")
        lbl_cd.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        cd_lay.addWidget(lbl_cd)

        h_cdc = QHBoxLayout()
        self.combo_cd = QComboBox()
        self.combo_cd.addItems(["50M", "100M", "200M", "500M", "1G"])
        self.combo_cd.setCurrentText("200M")
        btn_apply_cd = QPushButton("Apply Ceiling")
        btn_apply_cd.clicked.connect(self._apply_coredump)
        h_cdc.addWidget(self.combo_cd)
        h_cdc.addWidget(btn_apply_cd)
        cd_lay.addLayout(h_cdc)
        h_util.addWidget(cd_card)

        # ABRT card
        abrt_card = QFrame()
        abrt_card.setProperty("class", "card")
        ab_lay = QVBoxLayout(abrt_card)
        lbl_ab = QLabel("🐞 ABRT Bug Reporting Daemons")
        lbl_ab.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        ab_lay.addWidget(lbl_ab)

        h_abc = QHBoxLayout()
        self.btn_toggle_abrt = QPushButton("Disable ABRT Daemons")
        self.btn_toggle_abrt.clicked.connect(self._toggle_abrt)
        h_abc.addWidget(self.btn_toggle_abrt)
        ab_lay.addLayout(h_abc)
        h_util.addWidget(abrt_card)

        layout.addLayout(h_util)
        self._refresh()

    def _refresh(self):
        entries = self.autostart_tuner.list_autostart_entries()
        self.table_auto.setRowCount(len(entries))
        for row, e in enumerate(entries):
            self.table_auto.setItem(row, 0, QTableWidgetItem(e["name"]))
            self.table_auto.setItem(row, 1, QTableWidgetItem(e["scope"].capitalize()))
            self.table_auto.setItem(row, 2, QTableWidgetItem(e["exec"]))

            btn_tog = QPushButton("Disable" if e["enabled"] else "Enable")
            if e["enabled"]:
                btn_tog.setProperty("class", "destructive")
            btn_tog.clicked.connect(lambda ch, p=e["path"], en=e["enabled"]: self._toggle_entry(p, not en))
            self.table_auto.setCellWidget(row, 3, btn_tog)

    def _toggle_entry(self, path: str, enable: bool):
        ok, msg = self.autostart_tuner.toggle_autostart_entry(path, enable)
        QMessageBox.information(self, "Autostart Updated", msg)
        self._refresh()

    def _apply_coredump(self):
        val = self.combo_cd.currentText()
        dry_run = not self.safety.is_root
        ok, msg = self.autostart_tuner.configure_coredump_limit(val)
        title = "Simulation Results" if dry_run else "Core Dump Limit Applied"
        QMessageBox.information(self, title, msg)

    def _toggle_abrt(self):
        dry_run = not self.safety.is_root
        ok, msg = self.autostart_tuner.toggle_abrt_services(False)
        title = "Simulation Results" if dry_run else "ABRT Daemons Updated"
        QMessageBox.information(self, title, msg)
