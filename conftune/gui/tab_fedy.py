"""
Fedy Post-Install & Desktop Refinements Tab for ConfTune FC.
Inspired by Fedy (Fedora Utils). Manages RPM Fusion, multimedia codecs,
font rendering, proprietary hardware checks, and GNOME desktop tweaks.
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from conftune.core.fedy_tuner import FedyTuner
from conftune.core.safety import SafetyEngine
from conftune.gui.auth import prompt_root_required
from conftune.gui.workers import run_async_task


class FedyTab(QWidget):
    """Fedy-style post-installation & desktop refinement interface."""

    def __init__(self, fedy_tuner: FedyTuner, safety: SafetyEngine):
        super().__init__()
        self.fedy_tuner = fedy_tuner
        self.safety = safety
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)

        # Header Card
        header = QFrame()
        header.setProperty("class", "card")
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(16, 12, 16, 12)
        lbl_title = QLabel("Fedy Essentials: Codecs, Repos & Desktop Tweaks")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Streamline post-install tasks: RPM Fusion, GStreamer codecs, subpixel font rendering, and GNOME header buttons.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header)

        # 1. RPM Fusion Card
        rf_card = QFrame()
        rf_card.setProperty("class", "card")
        rf_lay = QVBoxLayout(rf_card)
        rf_lay.setSpacing(10)
        rf_lay.setContentsMargins(16, 14, 16, 14)

        lbl_rf_h = QLabel("📦 RPM Fusion (Free & Nonfree) Repositories")
        lbl_rf_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        rf_lay.addWidget(lbl_rf_h)

        self.lbl_rf_status = QLabel("Checking RPM Fusion...")
        self.lbl_rf_status.setStyleSheet("color: #dedede; font-size: 12px;")
        rf_lay.addWidget(self.lbl_rf_status)

        h_rf_btn = QHBoxLayout()
        rf_lbl = "🚀 Enable RPM Fusion Repositories" if self.safety.is_root else "🔒 Enable RPM Fusion Repositories (Requires Root)"
        self.btn_install_rf = QPushButton(rf_lbl)
        self.btn_install_rf.setProperty("class", "primary")
        self.btn_install_rf.clicked.connect(self._toggle_rpmfusion)
        h_rf_btn.addWidget(self.btn_install_rf)
        h_rf_btn.addStretch()
        rf_lay.addLayout(h_rf_btn)
        layout.addWidget(rf_card)

        # 2. Multimedia Codecs Card
        mc_card = QFrame()
        mc_card.setProperty("class", "card")
        mc_lay = QVBoxLayout(mc_card)
        mc_lay.setSpacing(10)
        mc_lay.setContentsMargins(16, 14, 16, 14)

        lbl_mc_h = QLabel("🎬 Multimedia Codecs & Hardware Video Acceleration")
        lbl_mc_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        mc_lay.addWidget(lbl_mc_h)

        lbl_mc_desc = QLabel(
            "Installs GStreamer plugins (ugly, bad, libav), FFmpeg, OpenH264, and VA-API acceleration "
            "so that browser video playback (YouTube, Netflix) and local media players decode seamlessly on GPU."
        )
        lbl_mc_desc.setStyleSheet("color: #dedede; font-size: 12px; line-height: 1.4;")
        lbl_mc_desc.setWordWrap(True)
        mc_lay.addWidget(lbl_mc_desc)

        h_mc_btn = QHBoxLayout()
        mc_lbl = "⚡ Install All Multimedia Codecs" if self.safety.is_root else "🔒 Install All Multimedia Codecs (Requires Root)"
        self.btn_install_codecs = QPushButton(mc_lbl)
        self.btn_install_codecs.setProperty("class", "primary")
        if not self.safety.is_root:
            self.btn_install_codecs.setEnabled(False)
            self.btn_install_codecs.setToolTip("Root privileges required to install system multimedia codecs")
        self.btn_install_codecs.clicked.connect(self._install_codecs)
        h_mc_btn.addWidget(self.btn_install_codecs)
        h_mc_btn.addStretch()
        mc_lay.addLayout(h_mc_btn)
        layout.addWidget(mc_card)

        # 3. Font Rendering Card
        font_card = QFrame()
        font_card.setProperty("class", "card")
        f_lay = QVBoxLayout(font_card)
        f_lay.setSpacing(10)
        f_lay.setContentsMargins(16, 14, 16, 14)

        lbl_f_h = QLabel("🔤 Crisp Font Rendering & Anti-Aliasing")
        lbl_f_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        f_lay.addWidget(lbl_f_h)

        self.lbl_font_status = QLabel("Checking font configuration...")
        self.lbl_font_status.setStyleSheet("color: #dedede; font-size: 12px;")
        f_lay.addWidget(self.lbl_font_status)

        lbl_f_desc = QLabel("Applies subpixel RGB antialiasing and slight LCD hinting in ~/.config/fontconfig/fonts.conf for maximum text sharpness.")
        lbl_f_desc.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        f_lay.addWidget(lbl_f_desc)

        h_f_btn = QHBoxLayout()
        btn_apply_fonts = QPushButton("✨ Optimize Font Rendering")
        btn_apply_fonts.setProperty("class", "primary")
        btn_apply_fonts.clicked.connect(self._optimize_fonts)
        h_f_btn.addWidget(btn_apply_fonts)

        btn_restore_fonts = QPushButton("↺ Restore Default Font Rendering (Undo)")
        btn_restore_fonts.setToolTip("Remove custom fonts.conf and restore system default font rendering")
        btn_restore_fonts.clicked.connect(self._restore_fonts)
        h_f_btn.addWidget(btn_restore_fonts)

        h_f_btn.addStretch()
        f_lay.addLayout(h_f_btn)
        layout.addWidget(font_card)

        # 4. GNOME Productivity Tweaks Card
        gnome_card = QFrame()
        gnome_card.setProperty("class", "card")
        g_lay = QVBoxLayout(gnome_card)
        g_lay.setSpacing(12)
        g_lay.setContentsMargins(16, 14, 16, 14)

        lbl_g_h = QLabel("🖥️ GNOME Desktop Productivity Tweaks")
        lbl_g_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        g_lay.addWidget(lbl_g_h)

        self.lbl_gnome_status = QLabel("Checking GNOME configuration...")
        self.lbl_gnome_status.setStyleSheet("color: #dedede; font-size: 12px;")
        g_lay.addWidget(self.lbl_gnome_status)

        self.chk_min = QCheckBox("Show Minimize Button on Window Headers")
        self.chk_max = QCheckBox("Show Maximize Button on Window Headers")
        self.chk_bat = QCheckBox("Show Battery Percentage in Top Panel")

        g_lay.addWidget(self.chk_min)
        g_lay.addWidget(self.chk_max)
        g_lay.addWidget(self.chk_bat)

        h_g_btn = QHBoxLayout()
        btn_apply_gnome = QPushButton("Apply GNOME Tweaks")
        btn_apply_gnome.setProperty("class", "primary")
        btn_apply_gnome.clicked.connect(self._apply_gnome_tweaks)
        h_g_btn.addWidget(btn_apply_gnome)

        btn_restore_gnome = QPushButton("↺ Reset to GNOME Defaults (Undo)")
        btn_restore_gnome.setToolTip("Reset window header buttons to stock [Close] and hide battery percentage")
        btn_restore_gnome.clicked.connect(self._restore_gnome_defaults)
        h_g_btn.addWidget(btn_restore_gnome)

        h_g_btn.addStretch()
        g_lay.addLayout(h_g_btn)
        layout.addWidget(gnome_card)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _refresh(self):
        rf = self.fedy_tuner.is_rpmfusion_installed()
        is_active = rf.get("enabled", rf["free"] and rf["nonfree"])

        if is_active:
            self.lbl_rf_status.setText("Status: 🟢 RPM Fusion Free & Nonfree are active.")
            self.lbl_rf_status.setStyleSheet("color: #57e389; font-size: 12px; font-weight: 500;")
            btn_txt = "🗑️ Disable RPM Fusion Repositories" if self.safety.is_root else "🔒 Disable RPM Fusion Repositories (Requires Root)"
            self.btn_install_rf.setText(btn_txt)
            self.btn_install_rf.setProperty("class", "destructive")
            self.btn_install_rf.setEnabled(self.safety.is_root)
        else:
            self.lbl_rf_status.setText("Status: 🔴 RPM Fusion is not currently enabled.")
            self.lbl_rf_status.setStyleSheet("color: #ff7b72; font-size: 12px; font-weight: 500;")
            btn_txt = "🚀 Enable RPM Fusion Repositories" if self.safety.is_root else "🔒 Enable RPM Fusion Repositories (Requires Root)"
            self.btn_install_rf.setText(btn_txt)
            self.btn_install_rf.setProperty("class", "primary")
            self.btn_install_rf.setEnabled(self.safety.is_root)

        if not self.safety.is_root:
            self.btn_install_rf.setToolTip("Root privileges required to modify RPM Fusion repositories")

        self.btn_install_rf.style().unpolish(self.btn_install_rf)
        self.btn_install_rf.style().polish(self.btn_install_rf)

        gt = self.fedy_tuner.get_gnome_tweaks_status()
        self.chk_min.setChecked(gt.get("show_minimize", False))
        self.chk_max.setChecked(gt.get("show_maximize", False))
        self.chk_bat.setChecked(gt.get("battery_percent", False))

        # Font status
        is_font_opt = self.fedy_tuner.is_font_rendering_optimized()
        if is_font_opt:
            self.lbl_font_status.setText("Status: 🟢 Custom subpixel anti-aliasing active (~/.config/fontconfig/fonts.conf)")
            self.lbl_font_status.setStyleSheet("color: #57e389; font-size: 12px; font-weight: 500;")
        else:
            self.lbl_font_status.setText("Status: ⚪ System default font rendering active (no override file)")
            self.lbl_font_status.setStyleSheet("color: #99c1f1; font-size: 12px; font-weight: 500;")

        # GNOME status
        has_min = gt.get("show_minimize", False)
        has_max = gt.get("show_maximize", False)
        has_bat = gt.get("battery_percent", False)
        if has_min or has_max or has_bat:
            details = []
            if has_min and has_max:
                details.append("Min & Max buttons")
            elif has_min:
                details.append("Min button")
            elif has_max:
                details.append("Max button")
            if has_bat:
                details.append("Battery %")
            self.lbl_gnome_status.setText(f"Status: 🟢 Custom settings active ({', '.join(details)})")
            self.lbl_gnome_status.setStyleSheet("color: #57e389; font-size: 12px; font-weight: 500;")
        else:
            self.lbl_gnome_status.setText("Status: ⚪ Stock GNOME defaults (Close button only, battery % hidden)")
            self.lbl_gnome_status.setStyleSheet("color: #99c1f1; font-size: 12px; font-weight: 500;")

    def _toggle_rpmfusion(self):
        rf = self.fedy_tuner.is_rpmfusion_installed()
        is_active = rf.get("enabled", rf["free"] and rf["nonfree"])
        if is_active:
            self._disable_rpmfusion()
        else:
            self._install_rpmfusion()

    def _disable_rpmfusion(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Disable RPM Fusion Repositories", self.safety):
                return
        self.btn_install_rf.setEnabled(False)

        def task():
            return self.fedy_tuner.disable_rpmfusion()

        def on_done(ok, msg, res):
            self.btn_install_rf.setEnabled(True)
            QMessageBox.information(self, "RPM Fusion", msg)
            self._refresh()

        run_async_task(task, on_done)

    def _install_rpmfusion(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Enable RPM Fusion Repositories", self.safety):
                return
        self.btn_install_rf.setEnabled(False)

        def task():
            return self.fedy_tuner.install_rpmfusion()

        def on_done(ok, msg, res):
            self.btn_install_rf.setEnabled(True)
            QMessageBox.information(self, "RPM Fusion", msg)
            self._refresh()

        run_async_task(task, on_done)

    def _install_codecs(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Install All Multimedia Codecs", self.safety):
                return
        self.btn_install_codecs.setEnabled(False)

        def task():
            return self.fedy_tuner.install_multimedia_codecs()

        def on_done(ok, msg, res):
            self.btn_install_codecs.setEnabled(True)
            QMessageBox.information(self, "Multimedia Codecs", msg)

        run_async_task(task, on_done)

    def _optimize_fonts(self):
        ok, msg = self.fedy_tuner.configure_font_rendering()
        self._refresh()
        QMessageBox.information(self, "Font Rendering", msg)

    def _restore_fonts(self):
        reply = QMessageBox.question(
            self,
            "Restore Font Defaults",
            "Revert font rendering configuration back to system defaults?\n(This removes ~/.config/fontconfig/fonts.conf and refreshes font cache)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.fedy_tuner.restore_default_fonts()
        self._refresh()
        QMessageBox.information(self, "Font Defaults Restored", msg)

    def _apply_gnome_tweaks(self):
        self.fedy_tuner.set_gnome_titlebar_buttons(
            minimize=self.chk_min.isChecked(),
            maximize=self.chk_max.isChecked(),
        )
        self.fedy_tuner.set_gnome_battery_percent(self.chk_bat.isChecked())
        self._refresh()
        QMessageBox.information(self, "GNOME Tweaks", "Desktop header buttons and battery settings updated.")

    def _restore_gnome_defaults(self):
        reply = QMessageBox.question(
            self,
            "Reset GNOME Defaults",
            "Reset GNOME window buttons back to stock default [Close] and hide battery percentage?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.fedy_tuner.restore_gnome_defaults()
        self._refresh()
        QMessageBox.information(self, "GNOME Defaults Restored", msg)
