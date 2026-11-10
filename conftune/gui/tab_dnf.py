"""
DNF Package Manager Accelerator Tab for ConfTune FC.
Provides controls for parallel downloading, fastest mirror selection, and cache purge.
"""

from typing import Any
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from conftune.core.dnf_tuner import DNFTuner
from conftune.core.safety import SafetyEngine
from conftune.gui.auth import prompt_root_required
from conftune.gui.workers import run_async_task


class DNFTab(QWidget):
    """DNF configuration and acceleration interface."""

    def __init__(self, dnf_tuner: DNFTuner, safety: SafetyEngine):
        super().__init__()
        self.dnf_tuner = dnf_tuner
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
        lbl_title = QLabel("DNF Package Manager Speed Accelerator")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Optimize /etc/dnf/dnf.conf to enable parallel multi-threaded RPM downloads and fastest mirror routing.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header)

        # Options Card
        opts_card = QFrame()
        opts_card.setProperty("class", "card")
        opts_lay = QVBoxLayout(opts_card)
        opts_lay.setSpacing(14)
        opts_lay.setContentsMargins(16, 16, 16, 16)

        # Status badge
        self.lbl_status = QLabel("Checking DNF configuration...")
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 500;")
        opts_lay.addWidget(self.lbl_status)

        # Parallel downloads
        h_dl = QHBoxLayout()
        lbl_dl = QLabel("Maximum Parallel Concurrent Downloads:")
        lbl_dl.setStyleSheet("font-weight: 500; font-size: 13px;")
        self.spin_dl = QSpinBox()
        self.spin_dl.setRange(2, 50)
        self.spin_dl.setValue(3)
        self.spin_dl.setFixedWidth(80)
        btn_def_dl = QPushButton("↺ Default (3)")
        btn_def_dl.setToolTip("Reset parallel downloads to Fedora default value of 3")
        btn_def_dl.clicked.connect(lambda: self.spin_dl.setValue(3))
        h_dl.addWidget(lbl_dl)
        h_dl.addWidget(self.spin_dl)
        h_dl.addWidget(btn_def_dl)
        h_dl.addStretch()
        opts_lay.addLayout(h_dl)

        lbl_dl_hint = QLabel("Default is 3. Setting to 10 or 15 saturates modern broadband links and speeds up system updates significantly.")
        lbl_dl_hint.setStyleSheet("color: #888888; font-size: 11px;")
        opts_lay.addWidget(lbl_dl_hint)

        # Fastest Mirror
        self.chk_fastest = QCheckBox("Enable Fastest Mirror Detection (fastestmirror=True)")
        opts_lay.addWidget(self.chk_fastest)

        # Default Yes
        self.chk_defaultyes = QCheckBox("Default confirmation prompts to Yes (defaultyes=True)")
        opts_lay.addWidget(self.chk_defaultyes)

        # Keep Cache
        self.chk_keepcache = QCheckBox("Keep downloaded packages in local cache (keepcache=True)")
        opts_lay.addWidget(self.chk_keepcache)

        # Buttons
        h_btns = QHBoxLayout()
        self.btn_apply = QPushButton("🚀 Apply DNF Acceleration" if self.safety.is_root else "🔒 Apply DNF Acceleration (Requires Root)")
        self.btn_apply.setProperty("class", "primary")
        self.btn_apply.clicked.connect(self._apply_dnf)
        h_btns.addWidget(self.btn_apply)

        reset_lbl = "↺ Reset to DNF Defaults (Undo)" if self.safety.is_root else "🔒 ↺ Reset to DNF Defaults (Root)"
        self.btn_reset = QPushButton(reset_lbl)
        self.btn_reset.setToolTip("Roll back parallel downloads and flags to stock Fedora DNF defaults")
        self.btn_reset.clicked.connect(self._reset_dnf_defaults)
        h_btns.addWidget(self.btn_reset)

        self.btn_clean = QPushButton("🧹 Purge DNF Metadata & Cache" if self.safety.is_root else "🔒 Purge DNF Cache (Requires Root)")
        self.btn_clean.clicked.connect(self._clean_dnf_cache)
        h_btns.addWidget(self.btn_clean)

        self.btn_reload = QPushButton("🔄 Refresh Status")
        self.btn_reload.clicked.connect(self._load_current)
        h_btns.addWidget(self.btn_reload)

        h_btns.addStretch()

        opts_lay.addLayout(h_btns)
        layout.addWidget(opts_card)

        # Gray out root-only controls if unprivileged
        if not self.safety.is_root:
            root_tip = "Root privileges required to modify DNF system configuration"
            self.spin_dl.setEnabled(False)
            self.spin_dl.setToolTip(root_tip)
            btn_def_dl.setEnabled(False)
            btn_def_dl.setToolTip(root_tip)
            self.chk_fastest.setEnabled(False)
            self.chk_fastest.setToolTip(root_tip)
            self.chk_defaultyes.setEnabled(False)
            self.chk_defaultyes.setToolTip(root_tip)
            self.chk_keepcache.setEnabled(False)
            self.chk_keepcache.setToolTip(root_tip)
            self.btn_apply.setEnabled(False)
            self.btn_apply.setToolTip(root_tip)
            self.btn_reset.setEnabled(False)
            self.btn_reset.setToolTip(root_tip)
            self.btn_clean.setEnabled(False)
            self.btn_clean.setToolTip("Root privileges required to purge system DNF package cache")

        layout.addStretch()
        self._load_current()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_current()

    @staticmethod
    def _to_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0
        return str(val).strip().lower() in ("true", "1", "yes", "on", "t")

    def _load_current(self):
        curr = self.dnf_tuner.get_current_settings()
        val = curr.get("max_parallel_downloads", "3")
        try:
            num = int(str(val).strip())
            if num > self.spin_dl.maximum():
                self.spin_dl.setMaximum(num)
            if num < self.spin_dl.minimum():
                self.spin_dl.setMinimum(num)
            self.spin_dl.setValue(num)
        except (ValueError, TypeError):
            self.spin_dl.setValue(3)

        self.chk_fastest.setChecked(self._to_bool(curr.get("fastestmirror", False)))
        self.chk_defaultyes.setChecked(self._to_bool(curr.get("defaultyes", False)))
        self.chk_keepcache.setChecked(self._to_bool(curr.get("keepcache", False)))

        # Update status badge
        is_custom = self.dnf_tuner.is_customized()
        if is_custom:
            self.lbl_status.setText(f"Status: 🟢 Custom DNF Acceleration Active ({self.spin_dl.value()} parallel downloads)")
            self.lbl_status.setStyleSheet("color: #57e389; font-size: 12px; font-weight: 500;")
        else:
            self.lbl_status.setText("Status: ⚪ Stock Fedora DNF Defaults Active (3 parallel downloads, stock mirrors)")
            self.lbl_status.setStyleSheet("color: #99c1f1; font-size: 12px; font-weight: 500;")

    def _reset_dnf_defaults(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Restore standard Fedora DNF configuration defaults", self.safety):
                return

        reply = QMessageBox.question(
            self,
            "Reset DNF to Defaults",
            "Are you sure you want to revert DNF configuration back to stock Fedora defaults (3 downloads, fastestmirror=False, defaultyes=False, keepcache=False)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.dnf_tuner.restore_defaults()
        if ok:
            self._load_current()
        QMessageBox.information(self, "DNF Defaults Restored", msg)

    def _apply_dnf(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Modifying DNF configuration in /etc/dnf/dnf.conf", self.safety):
                return

        ok, msg = self.dnf_tuner.apply_optimizations(
            max_parallel_downloads=self.spin_dl.value(),
            fastestmirror=self.chk_fastest.isChecked(),
            defaultyes=self.chk_defaultyes.isChecked(),
            keepcache=self.chk_keepcache.isChecked(),
        )
        if ok:
            self._load_current()
        QMessageBox.information(self, "DNF Configured", msg)

    def _clean_dnf_cache(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Purging system DNF package and metadata cache", self.safety):
                return

        ok, msg = self.dnf_tuner.clean_cache()
        QMessageBox.information(self, "DNF Cache Clean", msg)
