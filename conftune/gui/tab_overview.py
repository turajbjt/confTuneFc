"""
System Overview & Dashboard Tab for ConfTune FC.
Displays hardware profiling, OS role identification, and current tuning status.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from conftune.core.detector import SystemDetector
from conftune.core.server_tuner import ServerTuner
from conftune.core.storage_tuner import StorageTuner
from conftune.gui.workers import run_async_task


class OverviewTab(QWidget):
    """Main dashboard showing hardware, OS, and performance health."""

    action_requested = pyqtSignal(str)

    def __init__(self, detector: SystemDetector, server_tuner: ServerTuner, storage_tuner: StorageTuner):
        super().__init__()
        self.detector = detector
        self.server_tuner = server_tuner
        self.storage_tuner = storage_tuner
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

        # Title Card
        title_card = QFrame()
        title_card.setProperty("class", "card")
        tc_layout = QHBoxLayout(title_card)
        tc_layout.setContentsMargins(16, 14, 16, 14)

        v_box = QVBoxLayout()
        lbl_h = QLabel("System Dashboard & Hardware Intelligence")
        lbl_h.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Profiles host specifications, RPM environment, and tuning readiness.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        v_box.addWidget(lbl_h)
        v_box.addWidget(lbl_sub)
        tc_layout.addLayout(v_box)
        tc_layout.addStretch()

        btn_refresh = QPushButton("🔄 Refresh Specs")
        btn_refresh.clicked.connect(self.refresh_data)
        tc_layout.addWidget(btn_refresh)
        layout.addWidget(title_card)

        # System Specs Grid
        self.specs_card = QFrame()
        self.specs_card.setProperty("class", "card")
        self.grid = QGridLayout(self.specs_card)
        self.grid.setSpacing(12)
        layout.addWidget(self.specs_card)

        # Performance Health & Stack Card
        self.health_card = QFrame()
        self.health_card.setProperty("class", "card")
        self.h_layout = QVBoxLayout(self.health_card)
        self.h_layout.setSpacing(10)
        layout.addWidget(self.health_card)

        # Beta Notice & Safety Card
        beta_card = QFrame()
        beta_card.setProperty("class", "card")
        b_lay = QHBoxLayout(beta_card)
        b_lay.setContentsMargins(14, 10, 14, 10)
        b_lay.setSpacing(12)
        lbl_b_icon = QLabel("⚠️")
        lbl_b_icon.setStyleSheet("font-size: 20px;")
        lbl_b_text = QLabel(
            "<b>ConfTune FC Beta Software Notice:</b> Always verify configuration parameters in simulation (dry run) mode "
            "before applying changes. ConfTune FC creates automated safety snapshots, but independent system backups are always recommended."
        )
        lbl_b_text.setStyleSheet("color: #ffbe6f; font-size: 12px; line-height: 1.4;")
        lbl_b_text.setWordWrap(True)
        b_lay.addWidget(lbl_b_icon)
        b_lay.addWidget(lbl_b_text, 1)
        layout.addWidget(beta_card)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self.refresh_data()

    def refresh_data(self):
        """Reload detection and update cards."""
        self.detector.refresh()
        os_info = self.detector.os_info
        hw = self.detector.hardware_info
        role = self.detector.role_info
        tuned = self.server_tuner.get_tuned_status()

        # Clear specs grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        specs = [
            ("Operating System", os_info.get("pretty_name", "Linux")),
            ("Kernel Architecture", f"{os_info.get('kernel')} ({os_info.get('arch')})"),
            ("System Role", "Desktop Workstation (" + role.get("desktop_env", "GUI") + ")" if role.get("is_desktop") else "Headless Server / Cloud Node"),
            ("Virtualization", hw.get("virtualization", "none")),
            ("CPU Processor", f"{hw.get('cpu_model')} ({hw.get('cpu_cores')} logical cores)"),
            ("CPU Governor", hw.get("cpu_governor", "unknown")),
            ("Memory (RAM)", f"{hw.get('ram_avail_gb')} GB Available / {hw.get('ram_total_gb')} GB Total"),
            ("ZRAM Swap", f"Active ({hw.get('zram_size_gb')} GB)" if hw.get("has_zram") else "Not configured / Disabled"),
            ("Primary Storage", f"{'NVMe SSD' if hw.get('has_nvme') else 'SATA SSD / HDD'} (Root FS: {hw.get('root_fs')})"),
            ("Active Tuned Profile", tuned.get("active_profile", "unknown")),
        ]

        row = 0
        col = 0
        for title, val in specs:
            box = QFrame()
            box.setStyleSheet("background-color: #242424; border-radius: 6px; padding: 8px;")
            b_lay = QVBoxLayout(box)
            b_lay.setContentsMargins(6, 6, 6, 6)
            b_lay.setSpacing(4)
            l_t = QLabel(title)
            l_t.setStyleSheet("font-size: 11px; color: #888888; font-weight: bold; text-transform: uppercase;")
            l_v = QLabel(str(val))
            l_v.setStyleSheet("font-size: 13px; color: #ffffff; font-weight: 500;")
            l_v.setWordWrap(True)
            b_lay.addWidget(l_t)
            b_lay.addWidget(l_v)
            self.grid.addWidget(box, row, col)

            col += 1
            if col >= 2:
                col = 0
                row += 1

        # Health / Stack layout
        while self.h_layout.count():
            item = self.h_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lbl_sec = QLabel("Specialized Stack & Readiness Summary")
        lbl_sec.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        self.h_layout.addWidget(lbl_sec)

        stacks = self.detector.specialized_stacks
        vm = stacks.get("virtualmin", {})
        c = stacks.get("containers", {})
        v = stacks.get("virtualization_host", {})

        s_text = (
            f"• <b>Virtualmin / Webmin:</b> {'✅ Installed & Detected' if vm.get('detected') else '⚪ Not detected'}<br>"
            f"• <b>Container Hosts (Podman/Docker):</b> {'✅ Detected' if (c.get('has_podman') or c.get('has_docker')) else '⚪ None'} (IPv4 Forwarding: {'Active' if c.get('ip_forwarding') else 'Disabled'})<br>"
            f"• <b>Virtualization (KVM/Libvirt):</b> {'✅ Hardware KVM (/dev/kvm) Ready' if v.get('is_kvm_host') else '⚪ No KVM acceleration'}<br>"
            f"• <b>SELinux Mode:</b> {self.server_tuner.get_selinux_status()}<br>"
        )
        lbl_stack_info = QLabel(s_text)
        lbl_stack_info.setStyleSheet("color: #dedede; line-height: 1.5; font-size: 13px;")
        self.h_layout.addWidget(lbl_stack_info)
