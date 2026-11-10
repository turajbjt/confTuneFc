"""
Snapshots and Rollback Tab for ConfTune FC.
Provides historical review of pre-tune backups with 1-click safe rollback.
"""

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from conftune.core.backup_manager import BackupManager
from conftune.core.safety import SafetyEngine
from conftune.gui.auth import prompt_root_required


class BackupsTab(QWidget):
    """Snapshot history and rollback interface."""

    def __init__(self, backup_mgr: BackupManager, safety: SafetyEngine):
        super().__init__()
        self.backup_mgr = backup_mgr
        self.safety = safety
        self.selected_snap_id = None
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
        lbl_title = QLabel("Configuration Snapshots & Rollback Engine")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Automatic pre-tune snapshots enable instant 1-click rollback to any previous system state.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        v_box.addWidget(lbl_title)
        v_box.addWidget(lbl_sub)
        h_lay.addLayout(v_box)
        h_lay.addStretch()

        btn_ref = QPushButton("🔄 Refresh")
        btn_ref.clicked.connect(self._reload_snapshots)
        h_lay.addWidget(btn_ref)

        roll_lbl = "⏪ Rollback to Snapshot" if self.safety.is_root else "🔒 Rollback to Snapshot (Requires Root)"
        self.btn_rollback = QPushButton(roll_lbl)
        self.btn_rollback.setProperty("class", "destructive")
        if not self.safety.is_root:
            self.btn_rollback.setEnabled(False)
            self.btn_rollback.setToolTip("Root privileges required to rollback system configuration files from a snapshot")
        self.btn_rollback.clicked.connect(self._perform_rollback)
        h_lay.addWidget(self.btn_rollback)

        layout.addWidget(header)

        # Table of Snapshots
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Snapshot ID", "Created At", "Profile / Context", "Files Tracked"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

        # Details View
        lbl_det = QLabel("Snapshot File Manifest & Audit Details")
        lbl_det.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_det)

        self.txt_manifest = QTextEdit()
        self.txt_manifest.setReadOnly(True)
        self.txt_manifest.setStyleSheet("font-family: monospace; font-size: 12px;")
        layout.addWidget(self.txt_manifest)

        self._reload_snapshots()

    def _reload_snapshots(self):
        snaps = self.backup_mgr.list_snapshots()
        self.table.setRowCount(len(snaps))
        for row, s in enumerate(snaps):
            self.table.setItem(row, 0, QTableWidgetItem(s.get("id", "")))
            self.table.setItem(row, 1, QTableWidgetItem(s.get("timestamp", "")))
            self.table.setItem(row, 2, QTableWidgetItem(s.get("profile", "")))
            self.table.setItem(row, 3, QTableWidgetItem(str(len(s.get("files", [])))))

        if snaps:
            self.table.selectRow(0)
        else:
            self.txt_manifest.setText("No snapshots available yet. Applying a profile creates automatic pre-tune backups.")

    def _on_selection_changed(self):
        sel = self.table.selectedItems()
        if not sel:
            return
        row = self.table.currentRow()
        snap_id = self.table.item(row, 0).text()
        self.selected_snap_id = snap_id

        snap = self.backup_mgr.get_snapshot(snap_id)
        if snap:
            lines = [
                f"Snapshot ID: {snap.get('id')}",
                f"Timestamp  : {snap.get('timestamp')}",
                f"Profile    : {snap.get('profile')}",
                f"Notes      : {snap.get('notes', 'None')}",
                "",
                "Tracked Files in this Snapshot:",
            ]
            for f in snap.get("files", []):
                stat = "Existed prior to tune" if f.get("existed") else "Newly created file"
                lines.append(f"  • {f.get('original_path')} ({stat}, {f.get('size', 0)} bytes)")
            self.txt_manifest.setText("\n".join(lines))

    def _perform_rollback(self):
        if not self.selected_snap_id:
            QMessageBox.warning(self, "No Selection", "Please select a snapshot to restore.")
            return

        if not self.safety.is_root:
            if not prompt_root_required(self, f"Rollback System Configuration to Snapshot '{self.selected_snap_id}'", self.safety):
                return

        reply = QMessageBox.question(
            self,
            "Confirm System Rollback",
            f"Are you sure you want to rollback all system files to snapshot:\n\n{self.selected_snap_id}\n\n"
            "This will revert tuned files and reload systemd / sysctl configurations.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.backup_mgr.rollback_snapshot(self.selected_snap_id, dry_run=False)
        QMessageBox.information(self, "Rollback Finished", msg)
        self._reload_snapshots()
