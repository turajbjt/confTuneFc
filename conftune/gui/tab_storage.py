"""
Storage, I/O Scheduler, and ZRAM Tuning Tab for ConfTune FC.
Manages NVMe/SSD background TRIM, block schedulers, and ZRAM generator configuration.
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
from conftune.core.storage_tuner import StorageTuner
from conftune.gui.auth import prompt_root_required
from conftune.gui.workers import run_async_task


class StorageTab(QWidget):
    """Storage discard, I/O scheduler, and ZRAM configuration view."""

    def __init__(self, storage_tuner: StorageTuner, safety: SafetyEngine):
        super().__init__()
        self.storage_tuner = storage_tuner
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
        lbl_title = QLabel("Storage I/O, NVMe Discard & ZRAM Swap")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Optimize flash storage endurance, queue scheduling algorithms, and compressed RAM swap.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header)

        # TRIM Card
        trim_card = QFrame()
        trim_card.setProperty("class", "card")
        t_lay = QVBoxLayout(trim_card)
        t_lay.setSpacing(10)

        lbl_t_head = QLabel("SSD & NVMe Discard Maintenance (fstrim.timer)")
        lbl_t_head.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        t_lay.addWidget(lbl_t_head)

        self.lbl_trim_status = QLabel("Checking fstrim status...")
        self.lbl_trim_status.setStyleSheet("color: #dedede; font-size: 12px;")
        t_lay.addWidget(self.lbl_trim_status)

        h_tb = QHBoxLayout()
        trim_lbl = "⏱️ Enable Weekly TRIM Timer" if self.safety.is_root else "🔒 Enable Weekly TRIM Timer (Requires Root)"
        self.btn_enable_trim = QPushButton(trim_lbl)
        self.btn_enable_trim.setProperty("class", "primary")
        self.btn_enable_trim.clicked.connect(self._enable_trim)
        h_tb.addWidget(self.btn_enable_trim)

        run_lbl = "🧹 Run TRIM Discard Now" if self.safety.is_root else "🔒 Run TRIM Discard Now (Requires Root)"
        self.btn_run_trim = QPushButton(run_lbl)
        self.btn_run_trim.clicked.connect(self._run_trim_now)
        h_tb.addWidget(self.btn_run_trim)
        h_tb.addStretch()
        t_lay.addLayout(h_tb)
        layout.addWidget(trim_card)

        # I/O Scheduler Table
        lbl_sched = QLabel("Storage Devices & Active I/O Schedulers")
        lbl_sched.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_sched)

        self.table_sched = QTableWidget()
        self.table_sched.setColumnCount(3)
        self.table_sched.setHorizontalHeaderLabels(["Block Device", "Active Scheduler", "Available Schedulers"])
        self.table_sched.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_sched.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_sched.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_sched.setAlternatingRowColors(True)
        layout.addWidget(self.table_sched)

        # ZRAM Card
        zram_card = QFrame()
        zram_card.setProperty("class", "card")
        z_lay = QVBoxLayout(zram_card)
        z_lay.setSpacing(8)

        lbl_z_head = QLabel("ZRAM Compressed Swap Engine")
        lbl_z_head.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        z_lay.addWidget(lbl_z_head)

        self.lbl_zram_status = QLabel("Checking ZRAM configuration...")
        self.lbl_zram_status.setStyleSheet("color: #dedede; font-size: 12px;")
        z_lay.addWidget(self.lbl_zram_status)

        lbl_z_desc = QLabel("Configures /etc/systemd/zram-generator.conf using modern zstd compression and optimal size ceilings.")
        lbl_z_desc.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        z_lay.addWidget(lbl_z_desc)

        h_zb = QHBoxLayout()
        zram_lbl = "⚡ Configure Optimized ZRAM" if self.safety.is_root else "🔒 Configure Optimized ZRAM (Requires Root)"
        self.btn_apply_zram = QPushButton(zram_lbl)
        self.btn_apply_zram.setProperty("class", "primary")
        self.btn_apply_zram.clicked.connect(self._configure_zram)
        h_zb.addWidget(self.btn_apply_zram)

        undo_zram_lbl = "↺ Restore Default ZRAM (Undo)" if self.safety.is_root else "🔒 ↺ Restore Default ZRAM (Root)"
        self.btn_restore_zram = QPushButton(undo_zram_lbl)
        self.btn_restore_zram.setToolTip("Remove /etc/systemd/zram-generator.conf and restore Fedora system defaults")
        self.btn_restore_zram.clicked.connect(self._restore_zram)
        h_zb.addWidget(self.btn_restore_zram)

        h_zb.addStretch()
        z_lay.addLayout(h_zb)

        # Gray out root-only storage controls if unprivileged
        if not self.safety.is_root:
            self.btn_run_trim.setEnabled(False)
            self.btn_run_trim.setToolTip("Root privileges required to run filesystem TRIM discard")
            self.btn_apply_zram.setEnabled(False)
            self.btn_apply_zram.setToolTip("Root privileges required to configure ZRAM in /etc/systemd/")
            self.btn_restore_zram.setEnabled(False)
            self.btn_restore_zram.setToolTip("Root privileges required to restore ZRAM settings in /etc/systemd/")

        layout.addWidget(zram_card)

        layout.addStretch()
        self._refresh()

    def _refresh(self):
        f_stat = self.storage_tuner.get_fstrim_status()
        is_active = f_stat["active"] or f_stat["enabled"]
        if is_active:
            self.lbl_trim_status.setText("Status: 🟢 Active (Weekly background TRIM timer enabled)")
            self.lbl_trim_status.setStyleSheet("color: #57e389; font-size: 12px; font-weight: 500;")
            btn_txt = "🛑 Disable TRIM Timer (Default)" if self.safety.is_root else "🔒 Disable TRIM Timer (Root)"
            self.btn_enable_trim.setText(btn_txt)
            self.btn_enable_trim.setProperty("class", "destructive")
        else:
            self.lbl_trim_status.setText("Status: ⚪ Disabled (Timer inactive)")
            self.lbl_trim_status.setStyleSheet("color: #99c1f1; font-size: 12px; font-weight: 500;")
            btn_txt = "⏱️ Enable Weekly TRIM Timer" if self.safety.is_root else "🔒 Enable Weekly TRIM Timer (Root)"
            self.btn_enable_trim.setText(btn_txt)
            self.btn_enable_trim.setProperty("class", "primary")

        self.btn_enable_trim.setEnabled(self.safety.is_root)
        if not self.safety.is_root:
            self.btn_enable_trim.setToolTip("Root privileges required to enable/disable weekly TRIM timer")

        self.btn_enable_trim.style().unpolish(self.btn_enable_trim)
        self.btn_enable_trim.style().polish(self.btn_enable_trim)

        # ZRAM status
        if self.storage_tuner.is_zram_customized():
            self.lbl_zram_status.setText("Status: 🟢 Custom ZRAM configuration active (/etc/systemd/zram-generator.conf)")
            self.lbl_zram_status.setStyleSheet("color: #57e389; font-size: 12px; font-weight: 500;")
        else:
            self.lbl_zram_status.setText("Status: ⚪ Fedora default ZRAM settings active (/usr/lib/systemd/zram-generator.conf)")
            self.lbl_zram_status.setStyleSheet("color: #99c1f1; font-size: 12px; font-weight: 500;")

        # Schedulers
        devs = self.storage_tuner.get_disk_schedulers()
        self.table_sched.setRowCount(len(devs))
        for row, d in enumerate(devs):
            it_dev = QTableWidgetItem(d["device"])
            it_act = QTableWidgetItem(d["active"])
            it_act.setForeground(Qt.GlobalColor.cyan)
            it_avail = QTableWidgetItem(d["available"])
            self.table_sched.setItem(row, 0, it_dev)
            self.table_sched.setItem(row, 1, it_act)
            self.table_sched.setItem(row, 2, it_avail)

    def _enable_trim(self):
        f_stat = self.storage_tuner.get_fstrim_status()
        is_active = f_stat["active"] or f_stat["enabled"]

        if is_active:
            if not self.safety.is_root:
                if not prompt_root_required(self, "Disable Weekly TRIM Timer (fstrim.timer)", self.safety):
                    return
            ok, msg = self.storage_tuner.disable_fstrim_timer()
            QMessageBox.information(self, "fstrim.timer Disabled", msg)
        else:
            if not self.safety.is_root:
                if not prompt_root_required(self, "Enable Weekly TRIM Timer (fstrim.timer)", self.safety):
                    return
            ok, msg = self.storage_tuner.enable_fstrim_timer()
            QMessageBox.information(self, "fstrim.timer Enabled", msg)
        self._refresh()

    def _run_trim_now(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Run TRIM Discard Across All Block Devices", self.safety):
                return
        self.btn_run_trim.setEnabled(False)

        def task():
            return self.storage_tuner.run_fstrim_now()

        def on_done(ok, msg, res):
            self.btn_run_trim.setEnabled(True)
            QMessageBox.information(self, "TRIM Output", msg)

        run_async_task(task, on_done)

    def _configure_zram(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Configure ZRAM Compressed Swap Engine", self.safety):
                return
        ok, msg = self.storage_tuner.configure_zram()
        self._refresh()
        QMessageBox.information(self, "ZRAM Configured", msg)

    def _restore_zram(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Restore default system ZRAM configuration", self.safety):
                return

        reply = QMessageBox.question(
            self,
            "Reset ZRAM to Default",
            "Are you sure you want to remove /etc/systemd/zram-generator.conf and restore Fedora's default ZRAM swap generator settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.storage_tuner.restore_default_zram()
        self._refresh()
        QMessageBox.information(self, "ZRAM Defaults Restored", msg)
