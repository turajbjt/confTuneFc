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
        v_box.addWidget(lbl_title)
        v_box.addWidget(lbl_desc)
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

        self.btn_save = QPushButton("💾 Save Overrides" if self.safety.is_root else "🔒 Save Overrides (Requires Root)")
        self.btn_save.setProperty("class", "primary")
        self.btn_save.clicked.connect(self._save_changes)
        h_lay.addWidget(self.btn_save)

        layout.addWidget(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Parameter", "Current Live", "Recommended", "Impact", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self._reload_table()

    def _reload_table(self):
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

            self.table.setItem(row, 0, it_key)
            self.table.setItem(row, 1, it_cur)
            self.table.setItem(row, 2, it_rec)
            self.table.setItem(row, 3, it_imp)
            self.table.setItem(row, 4, it_desc)

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
