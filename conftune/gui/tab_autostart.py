"""
Autostart Applications & Crash Dump Limiter Tab for ConfTune FC.
Inspired by Stacer. Manages autostart launchers, core dump storage, and ABRT services.
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

from conftune.core.autostart_tuner import AutostartTuner
from conftune.core.safety import SafetyEngine
from conftune.gui.auth import prompt_root_required


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
        self.table_auto.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table_auto.setColumnWidth(3, 195)
        self.table_auto.verticalHeader().setDefaultSectionSize(44)
        self.table_auto.verticalHeader().setVisible(False)
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

        self.lbl_cd_status = QLabel("Status: Checking...")
        self.lbl_cd_status.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        cd_lay.addWidget(self.lbl_cd_status)

        h_cdc = QHBoxLayout()
        self.combo_cd = QComboBox()
        self.combo_cd.addItems(["50M", "100M", "200M", "500M", "1G"])
        self.combo_cd.setCurrentText("200M")
        cd_btn_lbl = "Apply Ceiling" if self.safety.is_root else "🔒 Apply Ceiling (Requires Root)"
        self.btn_apply_cd = QPushButton(cd_btn_lbl)
        self.btn_apply_cd.clicked.connect(self._apply_coredump)

        reset_cd_lbl = "↺ Default (Undo)" if self.safety.is_root else "🔒 Default (Requires Root)"
        self.btn_reset_cd = QPushButton(reset_cd_lbl)
        self.btn_reset_cd.clicked.connect(self._reset_coredump)

        h_cdc.addWidget(self.combo_cd)
        h_cdc.addWidget(self.btn_apply_cd)
        h_cdc.addWidget(self.btn_reset_cd)
        cd_lay.addLayout(h_cdc)
        h_util.addWidget(cd_card)

        # ABRT card
        abrt_card = QFrame()
        abrt_card.setProperty("class", "card")
        ab_lay = QVBoxLayout(abrt_card)
        lbl_ab = QLabel("🐞 ABRT Bug Reporting Daemons")
        lbl_ab.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        ab_lay.addWidget(lbl_ab)

        self.lbl_abrt_status = QLabel("Status: Checking...")
        self.lbl_abrt_status.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        ab_lay.addWidget(self.lbl_abrt_status)

        h_abc = QHBoxLayout()
        abrt_btn_lbl = "Disable ABRT Daemons" if self.safety.is_root else "🔒 Disable ABRT Daemons (Requires Root)"
        self.btn_toggle_abrt = QPushButton(abrt_btn_lbl)
        self.btn_toggle_abrt.clicked.connect(self._toggle_abrt)
        h_abc.addWidget(self.btn_toggle_abrt)
        ab_lay.addLayout(h_abc)
        h_util.addWidget(abrt_card)

        layout.addLayout(h_util)
        self._refresh()

    def _refresh(self):
        entries = self.autostart_tuner.list_autostart_entries()
        self.table_auto.clearContents()
        self.table_auto.setRowCount(len(entries))
        for row, e in enumerate(entries):
            self.table_auto.setItem(row, 0, QTableWidgetItem(e["name"]))
            self.table_auto.setItem(row, 1, QTableWidgetItem(e["scope"].capitalize()))
            self.table_auto.setItem(row, 2, QTableWidgetItem(e["exec"]))

            is_system = e.get("scope") == "system" or str(e.get("path", "")).startswith("/etc/")
            btn_txt = "Disable" if e["enabled"] else "Enable"
            if is_system and not self.safety.is_root:
                btn_txt = f"🔒 {btn_txt} (Root)"

            btn_tog = QPushButton(btn_txt)
            btn_tog.setFixedHeight(30)
            btn_tog.setFixedWidth(160)
            if e["enabled"]:
                btn_tog.setProperty("class", "destructive")
                btn_tog.style().unpolish(btn_tog)
                btn_tog.style().polish(btn_tog)
            btn_tog.clicked.connect(lambda ch, p=e["path"], en=e["enabled"]: self._toggle_entry(p, not en))

            # Action button container (centered and aligned in column 3)
            cell_container = QWidget()
            cell_layout = QHBoxLayout(cell_container)
            cell_layout.setContentsMargins(8, 4, 8, 4)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.addWidget(btn_tog)

            it_action = QTableWidgetItem()
            it_action.setFlags(it_action.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.table_auto.setItem(row, 0, QTableWidgetItem(e["name"]))
            self.table_auto.setItem(row, 1, QTableWidgetItem(e["scope"].capitalize()))
            self.table_auto.setItem(row, 2, QTableWidgetItem(e["exec"]))
            self.table_auto.setItem(row, 3, it_action)
            self.table_auto.setCellWidget(row, 3, cell_container)

        # Update coredump status & undo controls
        is_cd_custom = self.autostart_tuner.is_coredump_configured()
        active_cd_limit = self.autostart_tuner.get_current_coredump_limit()
        if is_cd_custom and active_cd_limit:
            self.lbl_cd_status.setText(f"Status: 🟢 Custom ceiling active ({active_cd_limit})")
            self.lbl_cd_status.setStyleSheet("color: #2ecc71; font-size: 11px; font-weight: bold;")
            idx = self.combo_cd.findText(active_cd_limit)
            if idx >= 0:
                self.combo_cd.setCurrentIndex(idx)
        else:
            self.lbl_cd_status.setText("Status: ⚪ System default storage ceiling active (unlimited / 10% root)")
            self.lbl_cd_status.setStyleSheet("color: #a0a0a0; font-size: 11px;")

        self.btn_apply_cd.setEnabled(self.safety.is_root)
        self.btn_reset_cd.setEnabled(self.safety.is_root and is_cd_custom)
        if not self.safety.is_root:
            self.btn_apply_cd.setText("🔒 Apply Ceiling (Requires Root)")
            self.btn_reset_cd.setText("🔒 Default (Requires Root)")
            self.combo_cd.setEnabled(False)
        else:
            self.btn_apply_cd.setText("Apply Ceiling")
            self.btn_reset_cd.setText("↺ Default (Undo)")
            self.combo_cd.setEnabled(True)

        # Update ABRT status & toggle button
        abrt_active = self.autostart_tuner.is_abrt_active()
        if abrt_active:
            self.lbl_abrt_status.setText("Status: 🟢 ABRT Services Active / Running")
            self.lbl_abrt_status.setStyleSheet("color: #2ecc71; font-size: 11px; font-weight: bold;")
            abrt_txt = "Disable ABRT Daemons" if self.safety.is_root else "🔒 Disable ABRT Daemons (Root)"
            self.btn_toggle_abrt.setText(abrt_txt)
            self.btn_toggle_abrt.setProperty("class", "destructive")
        else:
            self.lbl_abrt_status.setText("Status: ⚪ ABRT Services Inactive / Disabled")
            self.lbl_abrt_status.setStyleSheet("color: #a0a0a0; font-size: 11px;")
            abrt_txt = "Enable ABRT Daemons" if self.safety.is_root else "🔒 Enable ABRT Daemons (Root)"
            self.btn_toggle_abrt.setText(abrt_txt)
            self.btn_toggle_abrt.setProperty("class", "")

        self.btn_toggle_abrt.style().unpolish(self.btn_toggle_abrt)
        self.btn_toggle_abrt.style().polish(self.btn_toggle_abrt)
        self.btn_toggle_abrt.setEnabled(self.safety.is_root)

    def _toggle_entry(self, path: str, enable: bool):
        if path.startswith("/etc/") and not self.safety.is_root:
            if not prompt_root_required(self, f"{'Enable' if enable else 'Disable'} System Autostart Application", self.safety):
                return
        ok, msg = self.autostart_tuner.toggle_autostart_entry(path, enable)
        QMessageBox.information(self, "Autostart Updated", msg)
        self._refresh()

    def _apply_coredump(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Configure systemd-coredump Storage Ceiling", self.safety):
                return
        val = self.combo_cd.currentText()
        ok, msg = self.autostart_tuner.configure_coredump_limit(val)
        QMessageBox.information(self, "Core Dump Limit Applied", msg)
        self._refresh()

    def _reset_coredump(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Restore Default systemd-coredump Ceiling", self.safety):
                return
        ok, msg = self.autostart_tuner.restore_default_coredump()
        QMessageBox.information(self, "Core Dump Limit Restored", msg)
        self._refresh()

    def _toggle_abrt(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Manage ABRT Bug Reporting Daemons", self.safety):
                return
        is_active = self.autostart_tuner.is_abrt_active()
        target_enable = not is_active
        ok, msg = self.autostart_tuner.toggle_abrt_services(target_enable)
        QMessageBox.information(self, "ABRT Daemons Updated", msg)
        self._refresh()
