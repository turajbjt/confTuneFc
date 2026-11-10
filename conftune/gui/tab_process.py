"""
Process Scheduling & OOM Protection Tab for ConfTune FC.
Inspired by Process Lasso. Manages systemd-oomd thresholds and protects critical processes.
"""

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from conftune.core.process_tuner import ProcessTuner
from conftune.core.safety import SafetyEngine
from conftune.gui.auth import prompt_root_required


class ProcessTab(QWidget):
    """systemd-oomd thresholds and process priority/OOM score adjustment view."""

    def __init__(self, process_tuner: ProcessTuner, safety: SafetyEngine):
        super().__init__()
        self.process_tuner = process_tuner
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
        lbl_title = QLabel("Process Scheduling & OOM Killer Defense")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Tune Fedora's systemd-oomd memory pressure sensitivity and protect critical databases, IDEs, and desktop processes.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header)

        # 1. systemd-oomd Thresholds Card
        oomd_card = QFrame()
        oomd_card.setProperty("class", "card")
        o_lay = QVBoxLayout(oomd_card)
        o_lay.setSpacing(10)
        o_lay.setContentsMargins(16, 14, 16, 14)

        lbl_o_h = QLabel("🛡️ systemd-oomd Memory Pressure Sensitivity")
        lbl_o_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        o_lay.addWidget(lbl_o_h)

        self.lbl_oomd_status = QLabel("Checking systemd-oomd status...")
        self.lbl_oomd_status.setStyleSheet("color: #dedede; font-size: 12px;")
        o_lay.addWidget(self.lbl_oomd_status)

        lbl_o_desc = QLabel(
            "Default Fedora threshold (60%) can abruptly kill applications under moderate compilation or gaming loads. "
            "Raising to 75% or 80% prevents premature process termination."
        )
        lbl_o_desc.setStyleSheet("color: #a0a0a0; font-size: 12px; line-height: 1.4;")
        lbl_o_desc.setWordWrap(True)
        o_lay.addWidget(lbl_o_desc)

        h_oc = QHBoxLayout()
        lbl_press = QLabel("Memory Pressure Limit:")
        self.combo_press = QComboBox()
        self.combo_press.addItems(["50%", "60%", "70%", "80%", "90%"])
        self.combo_press.setCurrentText("70%")

        lbl_swap = QLabel("Swap Used Limit:")
        self.combo_swap = QComboBox()
        self.combo_swap.addItems(["80%", "90%", "95%"])
        self.combo_swap.setCurrentText("90%")

        oomd_btn_lbl = "Apply oomd Limits" if self.safety.is_root else "🔒 Apply oomd Limits (Requires Root)"
        self.btn_apply_oomd = QPushButton(oomd_btn_lbl)
        self.btn_apply_oomd.setProperty("class", "primary")
        self.btn_apply_oomd.clicked.connect(self._apply_oomd)

        reset_oomd_lbl = "↺ Reset to oomd Defaults (Undo)" if self.safety.is_root else "🔒 ↺ Reset oomd (Root)"
        self.btn_reset_oomd = QPushButton(reset_oomd_lbl)
        self.btn_reset_oomd.setToolTip("Remove /etc/systemd/oomd.conf.d/99-conftune.conf and restore system default limits")
        self.btn_reset_oomd.clicked.connect(self._reset_oomd)

        h_oc.addWidget(lbl_press)
        h_oc.addWidget(self.combo_press)
        h_oc.addWidget(lbl_swap)
        h_oc.addWidget(self.combo_swap)
        h_oc.addWidget(self.btn_apply_oomd)
        h_oc.addWidget(self.btn_reset_oomd)
        h_oc.addStretch()
        o_lay.addLayout(h_oc)

        if not self.safety.is_root:
            oomd_tip = "Root privileges required to configure systemd-oomd in /etc/systemd/"
            self.combo_press.setEnabled(False)
            self.combo_swap.setEnabled(False)
            self.btn_apply_oomd.setEnabled(False)
            self.btn_apply_oomd.setToolTip(oomd_tip)
            self.btn_reset_oomd.setEnabled(False)
            self.btn_reset_oomd.setToolTip(oomd_tip)

        layout.addWidget(oomd_card)

        # 2. Process OOM Immunity Card
        proc_card = QFrame()
        proc_card.setProperty("class", "card")
        p_lay = QVBoxLayout(proc_card)
        p_lay.setSpacing(10)
        p_lay.setContentsMargins(16, 14, 16, 14)

        lbl_p_h = QLabel("🎯 Process OOM Immunity (oom_score_adj)")
        lbl_p_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        p_lay.addWidget(lbl_p_h)

        lbl_p_desc = QLabel(
            "Protect crucial daemons (e.g. 'postgres', 'mariadb', 'code', 'docker') from being terminated by the Linux OOM Killer. "
            "Scores range from -1000 (immune) to +1000 (terminate first). Default unadjusted score is 0."
        )
        lbl_p_desc.setStyleSheet("color: #a0a0a0; font-size: 12px; line-height: 1.4;")
        lbl_p_desc.setWordWrap(True)
        p_lay.addWidget(lbl_p_desc)

        h_pc = QHBoxLayout()
        lbl_pn = QLabel("Process Name:")
        self.txt_pname = QLineEdit()
        self.txt_pname.setPlaceholderText("e.g. postgres, code, gnome-shell")
        self.txt_pname.setFixedWidth(200)

        lbl_adj = QLabel("Score Adjust:")
        self.spin_score = QSpinBox()
        self.spin_score.setRange(-1000, 1000)
        self.spin_score.setValue(-500)
        self.spin_score.setFixedWidth(90)

        btn_reset_score = QPushButton("↺ Default (0)")
        btn_reset_score.setToolTip("Set score adjust back to neutral default of 0")
        btn_reset_score.clicked.connect(lambda: self.spin_score.setValue(0))

        protect_btn_lbl = "🛡️ Protect Process" if self.safety.is_root else "🔒 Protect Process (Requires Root)"
        self.btn_protect = QPushButton(protect_btn_lbl)
        self.btn_protect.setProperty("class", "primary")
        self.btn_protect.clicked.connect(self._protect_process)

        h_pc.addWidget(lbl_pn)
        h_pc.addWidget(self.txt_pname)
        h_pc.addWidget(lbl_adj)
        h_pc.addWidget(self.spin_score)
        h_pc.addWidget(btn_reset_score)
        h_pc.addWidget(self.btn_protect)
        h_pc.addStretch()
        p_lay.addLayout(h_pc)

        if not self.safety.is_root:
            proc_tip = "Root privileges required to adjust process OOM killer score"
            self.txt_pname.setEnabled(False)
            self.spin_score.setEnabled(False)
            btn_reset_score.setEnabled(False)
            self.btn_protect.setEnabled(False)
            self.btn_protect.setToolTip(proc_tip)

        layout.addWidget(proc_card)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._refresh()

    def _refresh(self):
        stat = self.process_tuner.get_oomd_status()
        p_val = stat.get("memory_pressure_limit", "60%")
        if p_val in ["50%", "60%", "70%", "80%", "90%"]:
            self.combo_press.setCurrentText(p_val)

        # Update oomd status badge
        if self.process_tuner.is_oomd_customized():
            self.lbl_oomd_status.setText(f"Status: 🟢 Custom oomd limits active ({p_val} pressure) in /etc/systemd/oomd.conf.d/99-conftune.conf")
            self.lbl_oomd_status.setStyleSheet("color: #57e389; font-size: 12px; font-weight: 500;")
        else:
            self.lbl_oomd_status.setText("Status: ⚪ Fedora default oomd thresholds active (60% memory pressure, 90% swap)")
            self.lbl_oomd_status.setStyleSheet("color: #99c1f1; font-size: 12px; font-weight: 500;")

    def _apply_oomd(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Apply systemd-oomd Memory Pressure Limits", self.safety):
                return
        press = self.combo_press.currentText()
        swap = self.combo_swap.currentText()
        ok, msg = self.process_tuner.configure_oomd_limits(press, swap)
        self._refresh()
        QMessageBox.information(self, "oomd Limits Applied", msg)

    def _reset_oomd(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Restore default systemd-oomd thresholds", self.safety):
                return

        reply = QMessageBox.question(
            self,
            "Reset oomd to Defaults",
            "Are you sure you want to remove /etc/systemd/oomd.conf.d/99-conftune.conf and restore Fedora's default memory pressure limits (60% pressure, 90% swap)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.process_tuner.restore_default_oomd()
        self._refresh()
        QMessageBox.information(self, "oomd Defaults Restored", msg)

    def _protect_process(self):
        if not self.safety.is_root:
            if not prompt_root_required(self, "Adjust Process OOM Killer Score", self.safety):
                return
        pname = self.txt_pname.text().strip()
        if not pname:
            QMessageBox.warning(self, "Input Required", "Please enter a process name.")
            return

        ok, msg = self.process_tuner.protect_process_by_name(pname, self.spin_score.value())
        QMessageBox.information(self, "OOM Score Adjusted", msg)
