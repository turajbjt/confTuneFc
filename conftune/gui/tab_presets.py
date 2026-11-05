"""
Deploy, Presets & ISO Provisioning Tab for ConfTune FC.
Copyright (C) BuildDesignCreate.com.
Provides interfaces for:
1. Exporting host tuning as portable .conftune.tar.gz presets
2. Importing and applying external preset bundles
3. Generating standalone 1-file deploy.sh scripts
4. Generating Anaconda Kickstart files and building bootable installer ISOs with mkksiso
"""

import os
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from conftune.core.preset_manager import PresetManager
from conftune.core.safety import SafetyEngine
from conftune.gui.auth import prompt_root_required
from conftune.gui.workers import run_async_task


class PresetsTab(QWidget):
    """Presets export/import, standalone deployment scripts, and bootable ISO generator."""

    def __init__(self, preset_mgr: PresetManager, safety: SafetyEngine):
        super().__init__()
        self.preset_mgr = preset_mgr
        self.safety = safety
        self.loaded_preset_data = None
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
        lbl_title = QLabel("Presets, Portable Bundles & USB/ISO Provisioning")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Export your configuration into portable bundles, generate standalone 1-file deploy scripts, or inject into bootable USB installer ISOs.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # 1. Export Current System Card
        exp_card = QFrame()
        exp_card.setProperty("class", "card")
        e_lay = QVBoxLayout(exp_card)
        e_lay.setSpacing(10)
        e_lay.setContentsMargins(16, 14, 16, 14)

        lbl_e_h = QLabel("📤 Export Current Host Tuning as Portable Preset")
        lbl_e_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        e_lay.addWidget(lbl_e_h)

        h_e_inputs = QHBoxLayout()
        self.txt_exp_name = QLineEdit()
        self.txt_exp_name.setPlaceholderText("Preset Name (e.g. My Fedora 44 Workstation)")
        self.txt_exp_desc = QLineEdit()
        self.txt_exp_desc.setPlaceholderText("Description / Notes")
        h_e_inputs.addWidget(self.txt_exp_name)
        h_e_inputs.addWidget(self.txt_exp_desc)
        e_lay.addLayout(h_e_inputs)

        h_e_btn = QHBoxLayout()
        btn_export = QPushButton("📦 Export Preset Archive (.conftune.tar.gz)")
        btn_export.setProperty("class", "primary")
        btn_export.clicked.connect(self._export_preset)
        h_e_btn.addWidget(btn_export)
        h_e_btn.addStretch()
        e_lay.addLayout(h_e_btn)
        layout.addWidget(exp_card)

        # 2. Import & Apply Preset Card
        imp_card = QFrame()
        imp_card.setProperty("class", "card")
        i_lay = QVBoxLayout(imp_card)
        i_lay.setSpacing(10)
        i_lay.setContentsMargins(16, 14, 16, 14)

        lbl_i_h = QLabel("📥 Import & Apply External Preset Bundle")
        lbl_i_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        i_lay.addWidget(lbl_i_h)

        h_i_btn = QHBoxLayout()
        btn_browse_imp = QPushButton("📂 Select .conftune.tar.gz Archive...")
        btn_browse_imp.clicked.connect(self._select_import_file)
        h_i_btn.addWidget(btn_browse_imp)

        apply_lbl = "🚀 Apply Imported Preset" if self.safety.is_root else "🔒 Apply Imported Preset (Requires Root)"
        self.btn_apply_preset = QPushButton(apply_lbl)
        self.btn_apply_preset.setProperty("class", "primary")
        self.btn_apply_preset.setEnabled(False)
        self.btn_apply_preset.clicked.connect(self._apply_loaded_preset)
        h_i_btn.addWidget(self.btn_apply_preset)
        h_i_btn.addStretch()
        i_lay.addLayout(h_i_btn)

        self.txt_imp_preview = QTextEdit()
        self.txt_imp_preview.setReadOnly(True)
        self.txt_imp_preview.setMaximumHeight(140)
        self.txt_imp_preview.setStyleSheet("font-family: monospace; font-size: 11px;")
        self.txt_imp_preview.setPlaceholderText("Load a .conftune.tar.gz archive to preview parameters and metadata...")
        i_lay.addWidget(self.txt_imp_preview)
        layout.addWidget(imp_card)

        # 3. Standalone Script Generator Card
        sh_card = QFrame()
        sh_card.setProperty("class", "card")
        s_lay = QVBoxLayout(sh_card)
        s_lay.setSpacing(10)
        s_lay.setContentsMargins(16, 14, 16, 14)

        lbl_s_h = QLabel("📜 Generate Standalone 1-File Shell Installer (deploy.sh)")
        lbl_s_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        s_lay.addWidget(lbl_s_h)

        lbl_s_desc = QLabel(
            "Generates a self-contained bash script embedding your complete preset. "
            "Zero dependencies needed on the destination server (no Python or ConfTune required). "
            "Simply 'scp deploy.sh user@server:' and run 'sudo bash deploy.sh'."
        )
        lbl_s_desc.setStyleSheet("color: #a0a0a0; font-size: 12px; line-height: 1.4;")
        lbl_s_desc.setWordWrap(True)
        s_lay.addWidget(lbl_s_desc)

        h_s_btn = QHBoxLayout()
        btn_gen_sh = QPushButton("⚡ Generate deploy.sh Script")
        btn_gen_sh.clicked.connect(self._generate_deploy_script)
        h_s_btn.addWidget(btn_gen_sh)

        btn_gen_ansible = QPushButton("📋 Generate Ansible Playbook (.yml)")
        btn_gen_ansible.clicked.connect(self._generate_ansible_playbook)
        h_s_btn.addWidget(btn_gen_ansible)
        h_s_btn.addStretch()
        s_lay.addLayout(h_s_btn)
        layout.addWidget(sh_card)

        # 4. Kickstart & Bootable ISO Card
        iso_card = QFrame()
        iso_card.setProperty("class", "card")
        k_lay = QVBoxLayout(iso_card)
        k_lay.setSpacing(10)
        k_lay.setContentsMargins(16, 14, 16, 14)

        lbl_k_h = QLabel("💿 Bootable USB / ISO Provisioning (Kickstart & mkksiso)")
        lbl_k_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        k_lay.addWidget(lbl_k_h)

        lbl_k_desc = QLabel(
            "Generate an Anaconda Kickstart (.ks) file, or inject it directly into an official Fedora / Rocky / CentOS ISO image "
            "using 'mkksiso'. Flash the generated ISO to a USB drive to install an auto-tuned system out of the box."
        )
        lbl_k_desc.setStyleSheet("color: #a0a0a0; font-size: 12px; line-height: 1.4;")
        lbl_k_desc.setWordWrap(True)
        k_lay.addWidget(lbl_k_desc)

        h_k_btn = QHBoxLayout()
        btn_gen_ks = QPushButton("📄 Generate Kickstart (.ks)")
        btn_gen_ks.clicked.connect(self._generate_kickstart)
        h_k_btn.addWidget(btn_gen_ks)

        btn_build_iso = QPushButton("💿 Inject Kickstart into ISO with mkksiso")
        btn_build_iso.setProperty("class", "primary")
        btn_build_iso.clicked.connect(self._build_custom_iso)
        h_k_btn.addWidget(btn_build_iso)
        h_k_btn.addStretch()
        k_lay.addLayout(h_k_btn)

        layout.addWidget(iso_card)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    # --- Actions ---

    def _export_preset(self):
        name = self.txt_exp_name.text().strip() or "Fedora Custom Preset"
        desc = self.txt_exp_desc.text().strip()

        default_file = os.path.expanduser(f"~/Desktop/{name.lower().replace(' ', '_')}.conftune.tar.gz")
        dest_path, _ = QFileDialog.getSaveFileName(self, "Save Preset Archive", default_file, "ConfTune Archives (*.conftune.tar.gz *.tar.gz)")
        if not dest_path:
            return

        ok, msg = self.preset_mgr.export_preset_archive(dest_path, name=name, description=desc)
        if ok:
            QMessageBox.information(self, "Preset Exported", msg)
        else:
            QMessageBox.critical(self, "Export Error", msg)

    def _select_import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Preset Archive", os.path.expanduser("~"), "ConfTune Archives (*.conftune.tar.gz *.tar.gz)")
        if not file_path:
            return

        ok, msg, data = self.preset_mgr.import_preset_archive(file_path)
        if not ok:
            QMessageBox.critical(self, "Import Error", msg)
            return

        self.loaded_preset_data = data
        self.btn_apply_preset.setEnabled(True)

        preview = [
            f"Preset Name : {data.get('name')}",
            f"Description : {data.get('description')}",
            f"Created At  : {data.get('created_at')}",
            f"Tuned Adm   : {data.get('tuned_profile')}",
            f"Journal Max : {data.get('journald_max')}",
            f"Sysctl Keys : {len(data.get('sysctl', {}))} parameters configured",
            f"DNF Options : {data.get('dnf', {})}",
        ]
        self.txt_imp_preview.setText("\n".join(preview))

    def _apply_loaded_preset(self):
        if not self.loaded_preset_data:
            return

        if not self.safety.is_root:
            if not prompt_root_required(self, "Apply External Preset to System Host", self.safety):
                return

        dry_run = not self.safety.is_root
        old_dry = self.preset_mgr.safety.dry_run
        self.preset_mgr.safety.dry_run = dry_run

        ok, msg = self.preset_mgr.apply_preset(self.loaded_preset_data)
        self.preset_mgr.safety.dry_run = old_dry

        QMessageBox.information(self, "Preset Applied", msg)

    def _generate_deploy_script(self):
        preset = self.loaded_preset_data or self.preset_mgr.capture_current_settings(name="Host Tuning")
        default_file = os.path.expanduser("~/Desktop/deploy-conftune.sh")
        dest_path, _ = QFileDialog.getSaveFileName(self, "Save Standalone Script", default_file, "Shell Scripts (*.sh)")
        if not dest_path:
            return

        ok, msg = self.preset_mgr.generate_standalone_script(preset, dest_path)
        if ok:
            QMessageBox.information(self, "Script Generated", msg)
        else:
            QMessageBox.critical(self, "Generation Error", msg)

    def _generate_ansible_playbook(self):
        preset = self.loaded_preset_data or self.preset_mgr.capture_current_settings(name="Host Tuning")
        default_file = os.path.expanduser("~/Desktop/conftune-playbook.yml")
        dest_path, _ = QFileDialog.getSaveFileName(self, "Save Ansible Playbook", default_file, "Ansible Playbooks (*.yml *.yaml)")
        if not dest_path:
            return

        ok, msg = self.preset_mgr.generate_ansible_playbook(preset, dest_path)
        if ok:
            QMessageBox.information(self, "Playbook Generated", msg)
        else:
            QMessageBox.critical(self, "Generation Error", msg)

    def _generate_kickstart(self):
        preset = self.loaded_preset_data or self.preset_mgr.capture_current_settings(name="Host Tuning")
        default_file = os.path.expanduser("~/Desktop/conftune-postinstall.ks")
        dest_path, _ = QFileDialog.getSaveFileName(self, "Save Kickstart File", default_file, "Kickstart Files (*.ks)")
        if not dest_path:
            return

        ok, msg = self.preset_mgr.generate_kickstart(preset, dest_path)
        if ok:
            QMessageBox.information(self, "Kickstart Generated", msg)
        else:
            QMessageBox.critical(self, "Generation Error", msg)

    def _build_custom_iso(self):
        base_iso, _ = QFileDialog.getOpenFileName(self, "Select Base Fedora / Rocky / CentOS ISO", os.path.expanduser("~"), "ISO Images (*.iso)")
        if not base_iso:
            return

        default_out = os.path.splitext(base_iso)[0] + "-ConfTune.iso"
        out_iso, _ = QFileDialog.getSaveFileName(self, "Save Custom Bootable ISO", default_out, "ISO Images (*.iso)")
        if not out_iso:
            return

        # Generate temporary kickstart
        tmp_ks = "/tmp/conftune_temp.ks"
        preset = self.loaded_preset_data or self.preset_mgr.capture_current_settings(name="Host Tuning")
        self.preset_mgr.generate_kickstart(preset, tmp_ks)

        self.progress.setVisible(True)

        def task():
            return self.preset_mgr.build_custom_iso(base_iso, tmp_ks, out_iso)

        def on_done(ok, msg, res):
            self.progress.setVisible(False)
            if os.path.exists(tmp_ks):
                os.remove(tmp_ks)
            if ok:
                QMessageBox.information(self, "ISO Built", msg)
            else:
                QMessageBox.critical(self, "ISO Build Error", msg)

        run_async_task(task, on_done)
