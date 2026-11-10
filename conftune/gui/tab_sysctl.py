"""
Kernel Sysctl Tuning Tab for ConfTune FC.
Interactive inspection and fine-grained editing of kernel and network parameters.
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
from conftune.core.sysctl_tuner import PARAMETER_CATALOG, SysctlTuner
from conftune.gui.auth import prompt_root_required
from conftune.gui.workers import run_async_task


class SysctlTab(QWidget):
    """Fine-grained kernel parameter editor."""

    def __init__(self, sysctl_tuner: SysctlTuner, safety: SafetyEngine):
        super().__init__()
        self.sysctl_tuner = sysctl_tuner
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
        lbl_title = QLabel("Kernel & Network Sysctl Fine-Tuning")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_desc = QLabel("Inspect runtime values, verify documentation, and apply customized /etc/sysctl.d overrides.")
        lbl_desc.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        self.lbl_status = QLabel("Checking sysctl overrides...")
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 500;")
        v_box.addWidget(lbl_title)
        v_box.addWidget(lbl_desc)
        v_box.addWidget(self.lbl_status)
        h_lay.addLayout(v_box)
        h_lay.addStretch()

        # Category Filter
        self.cat_filter = QComboBox()
        self.cat_filter.addItem("All Categories")
        cats = sorted(list(set(m["category"] for m in PARAMETER_CATALOG.values())))
        for c in cats:
            self.cat_filter.addItem(c)
        self.cat_filter.currentTextChanged.connect(self._reload_table)
        h_lay.addWidget(self.cat_filter)

        btn_refresh = QPushButton("🔄 Refresh Live")
        btn_refresh.clicked.connect(self._reload_table)
        h_lay.addWidget(btn_refresh)

        reset_lbl = "↺ Reset to Kernel Defaults (Undo)" if self.safety.is_root else "🔒 ↺ Reset Defaults (Root)"
        self.btn_reset_defaults = QPushButton(reset_lbl)
        self.btn_reset_defaults.setToolTip("Remove /etc/sysctl.d/99-conftune.conf and reload kernel defaults" if self.safety.is_root else "Root privileges required to remove sysctl overrides")
        self.btn_reset_defaults.setEnabled(self.safety.is_root)
        self.btn_reset_defaults.clicked.connect(self._reset_defaults)
        h_lay.addWidget(self.btn_reset_defaults)

        self.btn_save = QPushButton("💾 Save Overrides" if self.safety.is_root else "🔒 Save Overrides (Requires Root)")
        self.btn_save.setProperty("class", "primary")
        self.btn_save.setEnabled(self.safety.is_root)
        self.btn_save.setToolTip("Save and apply kernel parameters" if self.safety.is_root else "Root privileges required to write /etc/sysctl.d/99-conftune.conf")
        self.btn_save.clicked.connect(self._save_changes)
        h_lay.addWidget(self.btn_save)

        layout.addWidget(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Parameter", "Current Live", "Recommended", "Impact", "Description", "Reset"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self._reload_table()

    def _reload_table(self):
        # Update override status badge
        has_custom = self.sysctl_tuner.has_custom_overrides()
        if has_custom:
            self.lbl_status.setText("Status: 🟢 Custom Overrides Active (/etc/sysctl.d/99-conftune.conf)")
            self.lbl_status.setStyleSheet("color: #57e389; font-size: 12px; font-weight: 500;")
        else:
            self.lbl_status.setText("Status: ⚪ Kernel Defaults Active (No ConfTune overrides)")
            self.lbl_status.setStyleSheet("color: #99c1f1; font-size: 12px; font-weight: 500;")

        cat_filter = self.cat_filter.currentText()
        items = self.sysctl_tuner.get_all_live_status()

        if cat_filter != "All Categories":
            items = [i for i in items if i["category"] == cat_filter]

        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            # Param
            it_key = QTableWidgetItem(item["key"])
            it_key.setFlags(it_key.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Current Live
            it_cur = QTableWidgetItem(item["current"])
            if not self.safety.is_root:
                it_cur.setFlags(it_cur.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Recommended
            it_rec = QTableWidgetItem(item["default"])
            it_rec.setFlags(it_rec.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Impact
            it_imp = QTableWidgetItem(item["impact"])
            it_imp.setFlags(it_imp.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if item["impact"] == "High":
                it_imp.setForeground(Qt.GlobalColor.yellow)

            # Description
            it_desc = QTableWidgetItem(item["description"])
            it_desc.setFlags(it_desc.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Reset Button for this specific row
            btn_row_reset = QPushButton("↺ Default")
            btn_row_reset.setToolTip(f"Reset {item['key']} value to recommended default: {item['default']}" if self.safety.is_root else "Root privileges required to modify kernel parameters")
            btn_row_reset.setEnabled(self.safety.is_root)
            btn_row_reset.setFixedHeight(24)
            btn_row_reset.clicked.connect(lambda ch, r=row, d=item["default"]: self._reset_row(r, d))

            self.table.setItem(row, 0, it_key)
            self.table.setItem(row, 1, it_cur)
            self.table.setItem(row, 2, it_rec)
            self.table.setItem(row, 3, it_imp)
            self.table.setItem(row, 4, it_desc)
            self.table.setCellWidget(row, 5, btn_row_reset)

    def _reset_row(self, row: int, default_val: str):
        item = self.table.item(row, 1)
        if item:
            item.setText(default_val)

    def _reset_defaults(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Restore default kernel sysctl configuration", self.safety):
                return

        reply = QMessageBox.question(
            self,
            "Reset Sysctl to Defaults",
            "Are you sure you want to remove all custom sysctl overrides in /etc/sysctl.d/99-conftune.conf and reload kernel defaults (sysctl --system)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.sysctl_tuner.restore_system_defaults()
        self._reload_table()
        QMessageBox.information(self, "Sysctl Defaults Restored", msg)

    def _save_changes(self):
        params = {}
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            val_item = self.table.item(row, 1)
            if key_item and val_item:
                val = val_item.text().strip()
                if val and val != "N/A":
                    params[key_item.text()] = val

        if not params:
            QMessageBox.warning(self, "No Parameters", "No valid parameters to apply.")
            return

        if not self.safety.is_root:
            if not prompt_root_required(self, "Saving kernel sysctl overrides to /etc/sysctl.d/99-conftune.conf", self.safety):
                return

        ok, msg = self.sysctl_tuner.apply_parameters(params, profile_name="custom_gui")
        QMessageBox.information(self, "Parameters Saved", msg)
        self._reload_table()
