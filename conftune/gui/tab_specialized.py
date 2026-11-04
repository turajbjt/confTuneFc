"""
Specialized Server Roles Tab for ConfTune FC.
Provides dedicated setup and optimization interfaces for:
1. Virtualmin & Webmin Web Hosting
2. Docker & Podman Container Hosts
3. KVM / Libvirt Virtualization Hosts
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from conftune.core.detector import SystemDetector
from conftune.core.profiles import get_profile
from conftune.core.safety import SafetyEngine
from conftune.core.server_tuner import ServerTuner
from conftune.core.sysctl_tuner import SysctlTuner
from conftune.gui.workers import run_async_task


class SpecializedTab(QWidget):
    """Configuration and tuning interface for Webmin, Containers, and Virtualization."""

    def __init__(
        self,
        detector: SystemDetector,
        server_tuner: ServerTuner,
        sysctl_tuner: SysctlTuner,
        safety: SafetyEngine,
    ):
        super().__init__()
        self.detector = detector
        self.server_tuner = server_tuner
        self.sysctl_tuner = sysctl_tuner
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
        lbl_title = QLabel("Specialized Server Stacks & Roles")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("One-click tuning and prerequisites for Virtualmin, Docker/Podman container nodes, and KVM hypervisors.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_sub)
        layout.addWidget(header)

        # 1. Virtualmin & Webmin Card
        self.card_vm = self._create_virtualmin_card()
        layout.addWidget(self.card_vm)

        # 2. Containers (Podman & Docker) Card
        self.card_cnt = self._create_containers_card()
        layout.addWidget(self.card_cnt)

        # 3. Virtualization (KVM & Libvirt) Card
        self.card_virt = self._create_virtualization_card()
        layout.addWidget(self.card_virt)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_virtualmin_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        h_top = QHBoxLayout()
        lbl_h = QLabel("🌐 Virtualmin & Webmin Multi-Tenant Hosting")
        lbl_h.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        h_top.addWidget(lbl_h)
        h_top.addStretch()

        vm_stat = self.detector.specialized_stacks.get("virtualmin", {})
        badge_text = "Installed / Active" if vm_stat.get("detected") else "Not Detected"
        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet(
            f"background-color: {'#26a269' if vm_stat.get('detected') else '#383838'}; "
            "color: #ffffff; border-radius: 10px; padding: 3px 8px; font-size: 11px; font-weight: bold;"
        )
        h_top.addWidget(lbl_badge)
        lay.addLayout(h_top)

        lbl_desc = QLabel(
            "Configures multi-domain web hosting, mail (Postfix/Dovecot), DNS (BIND), and MariaDB. "
            "Opens Webmin port 10000 in firewalld, scales TCP connection backlogs (somaxconn=65535), "
            "and accelerates socket recycling to handle high concurrency."
        )
        lbl_desc.setStyleSheet("color: #dedede; font-size: 12px; line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_desc)

        h_act = QHBoxLayout()
        btn_opt_vm = QPushButton("⚡ Optimize Virtualmin Hosting Stack")
        btn_opt_vm.setProperty("class", "primary")
        btn_opt_vm.clicked.connect(self._optimize_virtualmin)
        h_act.addWidget(btn_opt_vm)
        h_act.addStretch()
        lay.addLayout(h_act)

        return card

    def _create_containers_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        h_top = QHBoxLayout()
        lbl_h = QLabel("🐳 Docker & Podman Container Engine Host")
        lbl_h.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        h_top.addWidget(lbl_h)
        h_top.addStretch()

        c_stat = self.detector.specialized_stacks.get("containers", {})
        engines = []
        if c_stat.get("has_podman"):
            engines.append("Podman")
        if c_stat.get("has_docker"):
            engines.append("Docker")
        badge_text = ", ".join(engines) if engines else "None"
        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet(
            f"background-color: {'#3584e4' if engines else '#383838'}; "
            "color: #ffffff; border-radius: 10px; padding: 3px 8px; font-size: 11px; font-weight: bold;"
        )
        h_top.addWidget(lbl_badge)
        lay.addLayout(h_top)

        lbl_desc = QLabel(
            "Enables kernel IPv4/IPv6 packet forwarding for bridge networks, loads 'br_netfilter' and 'overlay' "
            "kernel modules, expands inotify file watchers to 1,048,576 for multi-container microservices, "
            "and raises PID ceilings to prevent fork exhaustion."
        )
        lbl_desc.setStyleSheet("color: #dedede; font-size: 12px; line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_desc)

        h_act = QHBoxLayout()
        btn_opt_c = QPushButton("⚡ Optimize Container Host Stack")
        btn_opt_c.setProperty("class", "primary")
        btn_opt_c.clicked.connect(self._optimize_containers)
        h_act.addWidget(btn_opt_c)
        h_act.addStretch()
        lay.addLayout(h_act)

        return card

    def _create_virtualization_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 16, 16, 16)

        h_top = QHBoxLayout()
        lbl_h = QLabel("🖥️ KVM / QEMU & Libvirt Virtualization Host")
        lbl_h.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        h_top.addWidget(lbl_h)
        h_top.addStretch()

        v_stat = self.detector.specialized_stacks.get("virtualization_host", {})
        badge_text = "KVM Ready (/dev/kvm)" if v_stat.get("is_kvm_host") else "No Hardware KVM"
        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet(
            f"background-color: {'#26a269' if v_stat.get('is_kvm_host') else '#e01b24'}; "
            "color: #ffffff; border-radius: 10px; padding: 3px 8px; font-size: 11px; font-weight: bold;"
        )
        h_top.addWidget(lbl_badge)
        lay.addLayout(h_top)

        lbl_desc = QLabel(
            "Tunes Rocky, CentOS, and Fedora bare-metal hypervisors. Activates 'virtual-host' profile in tuned-adm, "
            "activates KSM (Kernel Samepage Merging) memory deduplication for dense guest density, "
            "and lowers swappiness to 1 to protect guest memory allocations."
        )
        lbl_desc.setStyleSheet("color: #dedede; font-size: 12px; line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_desc)

        h_act = QHBoxLayout()
        btn_opt_v = QPushButton("⚡ Optimize Virtualization Hypervisor")
        btn_opt_v.setProperty("class", "primary")
        btn_opt_v.clicked.connect(self._optimize_virtualization)
        h_act.addWidget(btn_opt_v)
        h_act.addStretch()
        lay.addLayout(h_act)

        return card

    def _optimize_virtualmin(self):
        dry_run = not self.safety.is_root
        ok1, msg1 = self.server_tuner.optimize_virtualmin_stack()
        prof = get_profile("virtualmin")
        ok2, msg2 = self.sysctl_tuner.apply_parameters(prof["sysctl"], profile_name="Virtualmin Hosting")
        title = "Simulation Results" if dry_run else "Virtualmin Tuning Applied"
        QMessageBox.information(self, title, f"{msg1}\n\n{msg2}")

    def _optimize_containers(self):
        dry_run = not self.safety.is_root
        ok1, msg1 = self.server_tuner.optimize_containers_stack()
        prof = get_profile("container_host")
        ok2, msg2 = self.sysctl_tuner.apply_parameters(prof["sysctl"], profile_name="Container Host")
        title = "Simulation Results" if dry_run else "Container Host Tuning Applied"
        QMessageBox.information(self, title, f"{msg1}\n\n{msg2}")

    def _optimize_virtualization(self):
        dry_run = not self.safety.is_root
        ok1, msg1 = self.server_tuner.optimize_virtualization_host()
        prof = get_profile("virtualization_host")
        ok2, msg2 = self.sysctl_tuner.apply_parameters(prof["sysctl"], profile_name="Virtualization Host")
        title = "Simulation Results" if dry_run else "Virtualization Tuning Applied"
        QMessageBox.information(self, title, f"{msg1}\n\n{msg2}")
