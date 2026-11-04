"""
CPU Power, Governor & Energy Management Tab for ConfTune FC.
Inspired by QuickCPU and auto-cpufreq. Controls CPU EPP, governors, THP, and GameMode.
"""

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from conftune.core.power_tuner import PowerTuner
from conftune.core.safety import SafetyEngine


class PowerTab(QWidget):
    """CPU frequency governors, Energy Performance Preference, and THP view."""

    def __init__(self, power_tuner: PowerTuner, safety: SafetyEngine):
        super().__init__()
        self.power_tuner = power_tuner
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
        lbl_title = QLabel("CPU Power, Frequency Scaling & Energy Policy")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Control modern amd-pstate/intel_pstate EPP hints, cpufreq governors, and Transparent Huge Pages (THP).")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header)

        # 1. Scaling Governor Card
        gov_card = QFrame()
        gov_card.setProperty("class", "card")
        g_lay = QVBoxLayout(gov_card)
        g_lay.setSpacing(10)
        g_lay.setContentsMargins(16, 14, 16, 14)

        lbl_g_h = QLabel("⚡ CPU Frequency Scaling Governor")
        lbl_g_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        g_lay.addWidget(lbl_g_h)

        h_gc = QHBoxLayout()
        self.lbl_cur_gov = QLabel("Current Governor: Querying...")
        self.lbl_cur_gov.setStyleSheet("color: #dedede; font-weight: 500;")
        h_gc.addWidget(self.lbl_cur_gov)
        h_gc.addStretch()

        lbl_set_g = QLabel("Set Governor:")
        self.combo_gov = QComboBox()
        btn_set_gov = QPushButton("Apply Governor")
        btn_set_gov.clicked.connect(self._apply_governor)
        h_gc.addWidget(lbl_set_g)
        h_gc.addWidget(self.combo_gov)
        h_gc.addWidget(btn_set_gov)
        g_lay.addLayout(h_gc)
        layout.addWidget(gov_card)

        # 2. CPU EPP (Energy Performance Preference) Card
        epp_card = QFrame()
        epp_card.setProperty("class", "card")
        e_lay = QVBoxLayout(epp_card)
        e_lay.setSpacing(10)
        e_lay.setContentsMargins(16, 14, 16, 14)

        lbl_e_h = QLabel("🔋 Modern CPU EPP (Energy Performance Preference)")
        lbl_e_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        e_lay.addWidget(lbl_e_h)

        lbl_e_desc = QLabel("Hardware energy bias hint for modern AMD Zen and Intel Core processors (performance, balance_performance, power).")
        lbl_e_desc.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        e_lay.addWidget(lbl_e_desc)

        h_ec = QHBoxLayout()
        self.lbl_cur_epp = QLabel("Current EPP: Querying...")
        self.lbl_cur_epp.setStyleSheet("color: #dedede; font-weight: 500;")
        h_ec.addWidget(self.lbl_cur_epp)
        h_ec.addStretch()

        lbl_set_e = QLabel("Set EPP Mode:")
        self.combo_epp = QComboBox()
        self.combo_epp.addItems(["performance", "balance_performance", "balance_power", "power"])
        btn_set_epp = QPushButton("Apply EPP Mode")
        btn_set_epp.clicked.connect(self._apply_epp)
        h_ec.addWidget(lbl_set_e)
        h_ec.addWidget(self.combo_epp)
        h_ec.addWidget(btn_set_epp)
        e_lay.addLayout(h_ec)
        layout.addWidget(epp_card)

        # 3. Transparent Huge Pages (THP) Card
        thp_card = QFrame()
        thp_card.setProperty("class", "card")
        t_lay = QVBoxLayout(thp_card)
        t_lay.setSpacing(10)
        t_lay.setContentsMargins(16, 14, 16, 14)

        lbl_t_h = QLabel("🧠 Transparent Huge Pages (THP)")
        lbl_t_h.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        t_lay.addWidget(lbl_t_h)

        lbl_t_desc = QLabel("Controls automatic 2MB memory page aggregation. Databases (Redis, PostgreSQL) recommend 'madvise' or 'never', while virtualization benefits from 'always'.")
        lbl_t_desc.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        t_lay.addWidget(lbl_t_desc)

        h_tc = QHBoxLayout()
        self.lbl_cur_thp = QLabel("Current THP: Querying...")
        self.lbl_cur_thp.setStyleSheet("color: #dedede; font-weight: 500;")
        h_tc.addWidget(self.lbl_cur_thp)
        h_tc.addStretch()

        lbl_set_t = QLabel("Set THP Mode:")
        self.combo_thp = QComboBox()
        self.combo_thp.addItems(["always", "madvise", "never"])
        btn_set_thp = QPushButton("Apply THP")
        btn_set_thp.clicked.connect(self._apply_thp)
        h_tc.addWidget(lbl_set_t)
        h_tc.addWidget(self.combo_thp)
        h_tc.addWidget(btn_set_thp)
        t_lay.addLayout(h_tc)
        layout.addWidget(thp_card)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._refresh()

    def _refresh(self):
        # Governors
        curr_gov = self.power_tuner.get_current_governor()
        self.lbl_cur_gov.setText(f"Active Governor: {curr_gov}")
        self.combo_gov.clear()
        for g in self.power_tuner.get_available_governors():
            self.combo_gov.addItem(g)
        if curr_gov in self.power_tuner.get_available_governors():
            self.combo_gov.setCurrentText(curr_gov)

        # EPP
        curr_epp = self.power_tuner.get_current_epp()
        self.lbl_cur_epp.setText(f"Active EPP: {curr_epp}")
        if curr_epp in ["performance", "balance_performance", "balance_power", "power"]:
            self.combo_epp.setCurrentText(curr_epp)

        # THP
        thp = self.power_tuner.get_thp_status()
        self.lbl_cur_thp.setText(f"Active THP: {thp.get('active', 'unknown')}")
        if thp.get("active") in ["always", "madvise", "never"]:
            self.combo_thp.setCurrentText(thp.get("active"))

    def _apply_governor(self):
        gov = self.combo_gov.currentText()
        dry_run = not self.safety.is_root
        ok, msg = self.power_tuner.set_governor_all_cores(gov)
        title = "Simulation Results" if dry_run else "Governor Applied"
        QMessageBox.information(self, title, msg)
        self._refresh()

    def _apply_epp(self):
        epp = self.combo_epp.currentText()
        dry_run = not self.safety.is_root
        ok, msg = self.power_tuner.set_epp_all_cores(epp)
        title = "Simulation Results" if dry_run else "EPP Mode Applied"
        QMessageBox.information(self, title, msg)
        self._refresh()

    def _apply_thp(self):
        thp_mode = self.combo_thp.currentText()
        dry_run = not self.safety.is_root
        ok, msg = self.power_tuner.set_thp_mode(thp_mode)
        title = "Simulation Results" if dry_run else "THP Mode Applied"
        QMessageBox.information(self, title, msg)
        self._refresh()
