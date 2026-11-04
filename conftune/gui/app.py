"""
Main GUI Application Window for ConfTune FC.
Coordinates sidebar navigation, header badges, Polkit elevation, and all feature views.
"""

import os
import shutil
import subprocess
import sys
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from conftune import __version__
from conftune.core.autostart_tuner import AutostartTuner
from conftune.core.backup_manager import BackupManager
from conftune.core.detector import SystemDetector
from conftune.core.dnf_tuner import DNFTuner
from conftune.core.fedy_tuner import FedyTuner
from conftune.core.logger import get_logger, setup_logger
from conftune.core.power_tuner import PowerTuner
from conftune.core.privacy_tuner import PrivacyTuner
from conftune.core.process_tuner import ProcessTuner
from conftune.core.safety import SafetyEngine
from conftune.core.server_tuner import ServerTuner
from conftune.core.storage_tuner import StorageTuner
from conftune.core.sysctl_tuner import SysctlTuner
from conftune.core.systemd_tuner import SystemdTuner
from conftune.gui.styles import ADWAITA_DARK_STYLE
from conftune.gui.tab_autostart import AutostartTab
from conftune.gui.tab_backups import BackupsTab
from conftune.gui.tab_dnf import DNFTab
from conftune.gui.tab_fedy import FedyTab
from conftune.gui.tab_logs import LogsTab
from conftune.gui.tab_overview import OverviewTab
from conftune.gui.tab_power import PowerTab
from conftune.gui.tab_privacy import PrivacyTab
from conftune.gui.tab_process import ProcessTab
from conftune.gui.tab_profiles import ProfilesTab
from conftune.gui.tab_server import ServerTab
from conftune.gui.tab_specialized import SpecializedTab
from conftune.gui.tab_storage import StorageTab
from conftune.gui.tab_sysctl import SysctlTab
from conftune.gui.tab_systemd import SystemdTab


class MainWindow(QMainWindow):
    """Primary application window with GNOME Adwaita navigation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ConfTune FC - Fedora & RPM Performance Tuner")
        self.resize(1180, 740)
        self.setMinimumSize(920, 600)

        # Assets and Icon
        self.app_icon_path = None
        icon_candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icon.svg"),
            "/usr/share/conftune-fc/assets/icon.svg",
            "/usr/share/icons/hicolor/scalable/apps/conftune-fc.svg",
        ]
        for icon_path in icon_candidates:
            if os.path.isfile(icon_path):
                self.app_icon_path = icon_path
                self.setWindowIcon(QIcon(icon_path))
                break

        # Core Subsystems
        self.logger = get_logger()
        self.safety = SafetyEngine()
        self.backup_mgr = BackupManager()
        self.detector = SystemDetector()
        self.sysctl_tuner = SysctlTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.dnf_tuner = DNFTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.systemd_tuner = SystemdTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.storage_tuner = StorageTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.server_tuner = ServerTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.fedy_tuner = FedyTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.power_tuner = PowerTuner(safety=self.safety)
        self.process_tuner = ProcessTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.autostart_tuner = AutostartTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        self.privacy_tuner = PrivacyTuner(safety=self.safety)

        self._init_ui()
        self.logger.info("ConfTune FC GUI initialized.")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Bar
        header = QFrame()
        header.setObjectName("header_bar")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(18, 10, 18, 10)
        h_layout.setSpacing(10)

        # Logo Icon
        if self.app_icon_path and os.path.isfile(self.app_icon_path):
            pix = QIcon(self.app_icon_path).pixmap(38, 38)
            if not pix.isNull():
                lbl_logo = QLabel()
                lbl_logo.setPixmap(pix)
                lbl_logo.setFixedSize(38, 38)
                lbl_logo.setScaledContents(True)
                h_layout.addWidget(lbl_logo)

        title_lbl = QLabel("ConfTune FC")
        title_lbl.setObjectName("app_title")
        h_layout.addWidget(title_lbl)

        os_label = self.detector.os_info.get("pretty_name", "Fedora / RPM")
        version_badge = QLabel(f"v{__version__} ({os_label})")
        version_badge.setStyleSheet("color: #787878; font-size: 11px; margin-left: 4px;")
        h_layout.addWidget(version_badge)

        h_layout.addStretch()

        # Mode Badge (Root vs User)
        is_root = (os.geteuid() == 0)
        user_name = os.environ.get("USER", "root" if is_root else "user")
        mode_pill = QLabel(f"Mode: {'Root (System Administrator)' if is_root else f'User ({user_name})'}")
        if is_root:
            mode_pill.setObjectName("pill_root")
        else:
            mode_pill.setObjectName("pill_badge")
        h_layout.addWidget(mode_pill)

        # Elevate Button if running unprivileged
        if not is_root and self.safety.has_pkexec:
            self.btn_elevate = QPushButton("🛡️ Elevate (pkexec)")
            self.btn_elevate.clicked.connect(self._elevate_root)
            h_layout.addWidget(self.btn_elevate)

        main_layout.addWidget(header)

        # Body Layout: Sidebar + Stacked Views
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Navigation Sidebar Container
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(240)
        sidebar_container.setStyleSheet("background-color: #1e1e1e; border-right: 1px solid #323232;")
        sb_layout = QVBoxLayout(sidebar_container)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("nav_sidebar")
        self.sidebar.setIconSize(QSize(20, 20))

        nav_items = [
            ("📊  Overview & Specs", "overview"),
            ("🎯  Tuning Profiles", "profiles"),
            ("⚡  Kernel & Sysctl", "sysctl"),
            ("📦  DNF Accelerator", "dnf"),
            ("⏱️  Boot & Systemd", "systemd"),
            ("💾  Storage & ZRAM", "storage"),
            ("🌐  Specialized Stacks", "specialized"),
            ("🚀  Fedy Essentials", "fedy"),
            ("⚡  CPU & Power Policy", "power"),
            ("🛡️  Process & OOM Defense", "process"),
            ("🚀  Autostart Manager", "autostart"),
            ("🚫  Privacy & Telemetry", "privacy"),
            ("🏢  Server & Security", "server"),
            ("🗄️  Snapshots & Rollback", "backups"),
            ("📋  Audit Logs", "logs"),
        ]

        for text, key in nav_items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.sidebar.addItem(item)

        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        sb_layout.addWidget(self.sidebar)

        # Copyright Footer Link
        lbl_copyright = QLabel('© <a href="https://builddesigncreate.com" style="color: #727b84; text-decoration: none;">BuildDesignCreate.com</a>')
        lbl_copyright.setOpenExternalLinks(True)
        lbl_copyright.setStyleSheet("color: #727b84; font-size: 11px; padding: 12px 14px; border-top: 1px solid #282828;")
        lbl_copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_layout.addWidget(lbl_copyright)

        body_layout.addWidget(sidebar_container)

        # Stacked Views Widget
        self.stack = QStackedWidget()

        # 1. Overview Tab
        self.tab_overview = OverviewTab(self.detector, self.server_tuner, self.storage_tuner)
        self.stack.addWidget(self.tab_overview)

        # 2. Profiles Tab
        self.tab_profiles = ProfilesTab(
            self.sysctl_tuner,
            self.dnf_tuner,
            self.systemd_tuner,
            self.server_tuner,
            self.safety,
        )
        self.stack.addWidget(self.tab_profiles)

        # 3. Sysctl Tab
        self.tab_sysctl = SysctlTab(self.sysctl_tuner, self.safety)
        self.stack.addWidget(self.tab_sysctl)

        # 4. DNF Tab
        self.tab_dnf = DNFTab(self.dnf_tuner, self.safety)
        self.stack.addWidget(self.tab_dnf)

        # 5. Systemd Tab
        self.tab_systemd = SystemdTab(self.systemd_tuner, self.safety)
        self.stack.addWidget(self.tab_systemd)

        # 6. Storage Tab
        self.tab_storage = StorageTab(self.storage_tuner, self.safety)
        self.stack.addWidget(self.tab_storage)

        # 7. Specialized Stacks Tab
        self.tab_specialized = SpecializedTab(
            self.detector,
            self.server_tuner,
            self.sysctl_tuner,
            self.safety,
        )
        self.stack.addWidget(self.tab_specialized)

        # 8. Fedy Essentials Tab
        self.tab_fedy = FedyTab(self.fedy_tuner, self.safety)
        self.stack.addWidget(self.tab_fedy)

        # 9. Power Policy Tab
        self.tab_power = PowerTab(self.power_tuner, self.safety)
        self.stack.addWidget(self.tab_power)

        # 10. Process & OOM Tab
        self.tab_process = ProcessTab(self.process_tuner, self.safety)
        self.stack.addWidget(self.tab_process)

        # 11. Autostart Tab
        self.tab_autostart = AutostartTab(self.autostart_tuner, self.safety)
        self.stack.addWidget(self.tab_autostart)

        # 12. Privacy Tab
        self.tab_privacy = PrivacyTab(self.privacy_tuner, self.safety)
        self.stack.addWidget(self.tab_privacy)

        # 13. Server & Security Tab
        self.tab_server = ServerTab(self.server_tuner, self.safety)
        self.stack.addWidget(self.tab_server)

        # 14. Snapshots & Rollback Tab
        self.tab_backups = BackupsTab(self.backup_mgr, self.safety)
        self.stack.addWidget(self.tab_backups)

        # 15. Audit Logs Tab
        self.tab_logs = LogsTab()
        self.stack.addWidget(self.tab_logs)

        body_layout.addWidget(self.stack)
        main_layout.addLayout(body_layout)

        # Set default tab
        self.sidebar.setCurrentRow(0)

    def _on_nav_changed(self, row: int):
        self.stack.setCurrentIndex(row)

    def _elevate_root(self):
        """Relaunch ConfTune FC as root via pkexec."""
        pkexec_bin = shutil.which("pkexec")
        if not pkexec_bin:
            QMessageBox.warning(self, "pkexec Missing", "PolicyKit pkexec utility is not installed.")
            return

        main_py = os.path.abspath(sys.argv[0])
        cmd = [pkexec_bin, sys.executable, main_py]
        try:
            self.logger.info("Spawning elevated process via pkexec...")
            subprocess.Popen(cmd)
            sys.exit(0)
        except Exception as e:
            QMessageBox.critical(self, "Elevation Error", f"Could not elevate process: {e}")


def run_gui(ready_signal: bool = False) -> None:
    """Initialize QApplication and start Qt event loop."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(ADWAITA_DARK_STYLE)

    window = MainWindow()
    window.show()

    if ready_signal:
        print("CONFTUNE_READY", flush=True)

    sys.exit(app.exec())
