"""
DNF Package Manager Accelerator Tab for ConfTune FC.
Provides controls for parallel downloading, fastest mirror selection, and cache purge.
"""

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

        # Parallel downloads
        h_dl = QHBoxLayout()
        lbl_dl = QLabel("Maximum Parallel Concurrent Downloads:")
        lbl_dl.setStyleSheet("font-weight: 500; font-size: 13px;")
        self.spin_dl = QSpinBox()
        self.spin_dl.setRange(2, 20)
        self.spin_dl.setValue(10)
        self.spin_dl.setFixedWidth(80)
        h_dl.addWidget(lbl_dl)
        h_dl.addWidget(self.spin_dl)
        h_dl.addStretch()
        opts_lay.addLayout(h_dl)

        lbl_dl_hint = QLabel("Default is 3. Setting to 10 or 15 saturates modern broadband links and speeds up system updates significantly.")
        lbl_dl_hint.setStyleSheet("color: #888888; font-size: 11px;")
        opts_lay.addWidget(lbl_dl_hint)

        # Fastest Mirror
        self.chk_fastest = QCheckBox("Enable Fastest Mirror Detection (fastestmirror=True)")
        self.chk_fastest.setChecked(True)
        opts_lay.addWidget(self.chk_fastest)

        # Default Yes
        self.chk_defaultyes = QCheckBox("Default confirmation prompts to Yes (defaultyes=True)")
        self.chk_defaultyes.setChecked(True)
        opts_lay.addWidget(self.chk_defaultyes)

        # Keep Cache
        self.chk_keepcache = QCheckBox("Keep downloaded packages in local cache (keepcache=True)")
        self.chk_keepcache.setChecked(True)
        opts_lay.addWidget(self.chk_keepcache)

        # Buttons
        h_btns = QHBoxLayout()
        self.btn_apply = QPushButton("🚀 Apply DNF Acceleration" if self.safety.is_root else "🔒 Apply DNF Acceleration (Requires Root)")
        self.btn_apply.setProperty("class", "primary")
        self.btn_apply.clicked.connect(self._apply_dnf)
        h_btns.addWidget(self.btn_apply)

        self.btn_clean = QPushButton("🧹 Purge DNF Metadata & Cache" if self.safety.is_root else "🔒 Purge DNF Cache (Requires Root)")
        self.btn_clean.clicked.connect(self._clean_dnf_cache)
        h_btns.addWidget(self.btn_clean)
        h_btns.addStretch()

        opts_lay.addLayout(h_btns)
        layout.addWidget(opts_card)

        layout.addStretch()
        self._load_current()

    def _load_current(self):
        curr = self.dnf_tuner.get_current_settings()
        val = curr.get("max_parallel_downloads", "3")
        if str(val).isdigit():
            self.spin_dl.setValue(int(val))
        self.chk_fastest.setChecked(curr.get("fastestmirror", "False").lower() == "true")
        self.chk_defaultyes.setChecked(curr.get("defaultyes", "False").lower() == "true")
        self.chk_keepcache.setChecked(curr.get("keepcache", "False").lower() == "true")

    def _apply_dnf(self):
        if not self.safety.is_root:
            prompt_root_required(self, "Modifying DNF configuration in /etc/dnf/dnf.conf")
            return

        ok, msg = self.dnf_tuner.apply_optimizations(
            max_parallel_downloads=self.spin_dl.value(),
            fastestmirror=self.chk_fastest.isChecked(),
            defaultyes=self.chk_defaultyes.isChecked(),
            keepcache=self.chk_keepcache.isChecked(),
        )
        QMessageBox.information(self, "DNF Configured", msg)

    def _clean_dnf_cache(self):
        if not self.safety.is_root:
            prompt_root_required(self, "Purging system DNF package and metadata cache")
            return

        ok, msg = self.dnf_tuner.clean_cache()
        QMessageBox.information(self, "DNF Cache Clean", msg)
