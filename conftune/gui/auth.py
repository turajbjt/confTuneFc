"""
Authentication & Privilege Management for ConfTune FC GUI.
Provides PolicyKit (pkexec) root elevation with asynchronous GUI handshake,
XWayland display authorization, and safe prompt guards matching ConfClean FC.
"""

import getpass
import os
import shutil
import subprocess
import sys
from typing import Callable, Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from conftune.core.safety import SafetyEngine


def is_root() -> bool:
    """Return True if current process has root privileges (UID 0)."""
    return os.geteuid() == 0


class ElevationWorker(QThread):
    """Monitors asynchronous pkexec launch and waits for child GUI readiness handshake."""

    elevation_failed = pyqtSignal(str)
    elevation_succeeded = pyqtSignal()

    def __init__(self, cmd, parent=None):
        super().__init__(parent)
        self.cmd = cmd

    def run(self):
        try:
            proc = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Read first line from stdout (blocks until child flushes CONFTUNE_ELEVATED_READY or terminates)
            line = proc.stdout.readline()
            if "CONFTUNE_ELEVATED_READY" in line:
                self.elevation_succeeded.emit()
                return

            # Process exited or failed before displaying its GUI window
            proc.wait()
            stderr_out = proc.stderr.read().strip()
            if proc.returncode in (126, 127) or "not authorized" in stderr_out.lower() or "dismissed" in stderr_out.lower():
                self.elevation_failed.emit("cancelled")
            elif stderr_out:
                self.elevation_failed.emit(stderr_out)
            else:
                self.elevation_failed.emit(f"Process exited with code {proc.returncode}")
        except Exception as e:
            self.elevation_failed.emit(str(e))


def relaunch_as_root(
    parent: Optional[QWidget] = None,
    prompt_confirm: bool = True,
    action_description: str = "",
) -> None:
    """
    Relaunch ConfTune FC as root via PolicyKit (pkexec) using the proven
    ConfClean FC elevation architecture with XWayland display authorization
    and asynchronous GUI readiness handshake.
    """
    if os.geteuid() == 0:
        if parent:
            QMessageBox.information(
                parent,
                "Already Elevated",
                "ConfTune FC is already running with root / administrative privileges.",
            )
        return

    pkexec_bin = shutil.which("pkexec")
    if not pkexec_bin:
        if parent:
            QMessageBox.critical(
                parent,
                "Elevation Unavailable",
                "The 'pkexec' utility was not found. Please install the polkit package to use privilege elevation.",
            )
        return

    if prompt_confirm and parent:
        desc_text = f"to perform:\n• {action_description}\n\n" if action_description else "to enable system-wide performance tuning.\n\n"
        reply = QMessageBox.question(
            parent,
            "Elevate Privileges",
            f"This will restart ConfTune FC as root via PolicyKit (pkexec) {desc_text}Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

    # Grant local root access to XWayland / X11 server
    try:
        subprocess.run(["xhost", "+SI:localuser:root"], capture_output=True, timeout=2, check=False)
    except Exception:
        pass

    env_bin = shutil.which("env") or "/usr/bin/env"
    env_vars = []
    for var in ["DISPLAY", "XAUTHORITY"]:
        val = os.environ.get(var)
        if val:
            env_vars.append(f"{var}={val}")

    if not any(v.startswith("DISPLAY=") for v in env_vars):
        env_vars.append("DISPLAY=:0")

    # In Wayland, root cannot connect to user's wayland-0 socket.
    # Force Qt to use XCB backend to connect to XWayland via DISPLAY.
    env_vars.append("QT_QPA_PLATFORM=xcb")

    script_path = os.path.abspath(sys.argv[0])
    target_cmd = [sys.executable, script_path, "--gui", "--elevated-child"]
    cmd = [pkexec_bin, env_bin] + env_vars + target_cmd

    window = parent.window() if (parent and hasattr(parent, "window")) else parent
    btn_elevate = getattr(window, "btn_elevate", None)
    if btn_elevate:
        btn_elevate.setEnabled(False)
        btn_elevate.setText("Waiting for authorization...")

    def on_succeeded():
        QApplication.quit()

    def on_failed(error_msg: str):
        if btn_elevate:
            btn_elevate.setEnabled(True)
            btn_elevate.setText("🛡️ Elevate (pkexec)")
        if error_msg != "cancelled" and parent:
            QMessageBox.critical(
                parent,
                "Elevation Failed",
                f"Could not launch elevated instance:\n\n{error_msg}",
            )

    worker = ElevationWorker(cmd, parent)
    worker.elevation_succeeded.connect(on_succeeded)
    worker.elevation_failed.connect(on_failed)
    if parent:
        parent._elevation_worker = worker
    worker.start()


class SudoAuthDialog(QDialog):
    """
    Secure, native in-app administrator authentication dialog.
    Authenticates user sudo credentials without killing the application.
    """

    def __init__(
        self,
        parent: Optional[QWidget],
        action_description: str,
        safety: SafetyEngine,
        on_success: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.action_description = action_description
        self.safety = safety
        self.on_success = on_success
        self.authenticated = False
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Administrator Authentication Required")
        self.setFixedWidth(460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header card
        header_card = QFrame()
        header_card.setProperty("class", "card")
        h_box = QHBoxLayout(header_card)
        h_box.setContentsMargins(12, 10, 12, 10)

        lbl_icon = QLabel("🛡️")
        lbl_icon.setStyleSheet("font-size: 28px; margin-right: 8px;")
        h_box.addWidget(lbl_icon)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        lbl_title = QLabel("Privileged Action Authorization")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel(f"Authorizing: {self.action_description}")
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("font-size: 11px; color: #a0a0a0;")
        v_head.addWidget(lbl_title)
        v_head.addWidget(lbl_sub)
        h_box.addLayout(v_head)
        layout.addWidget(header_card)

        # Instruction label
        current_user = getpass.getuser()
        lbl_prompt = QLabel(
            f"Superuser privileges are required to modify system configuration.<br>"
            f"Enter administrator password for <b>{current_user}</b>:"
        )
        lbl_prompt.setWordWrap(True)
        lbl_prompt.setStyleSheet("color: #dedede; font-size: 12px; line-height: 1.4;")
        layout.addWidget(lbl_prompt)

        # Password input field
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Enter password...")
        self.txt_password.setStyleSheet(
            "padding: 8px 10px; font-size: 13px; background-color: #242424; "
            "border: 1px solid #3c3c3c; border-radius: 6px; color: #ffffff;"
        )
        self.txt_password.returnPressed.connect(self._handle_auth)
        layout.addWidget(self.txt_password)

        # Error notification label (initially hidden)
        self.lbl_error = QLabel()
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setStyleSheet("color: #ff6b6b; font-size: 11px; font-weight: bold;")
        self.lbl_error.setVisible(False)
        layout.addWidget(self.lbl_error)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_auth = QPushButton("🛡️ Authenticate")
        self.btn_auth.setProperty("class", "primary")
        self.btn_auth.clicked.connect(self._handle_auth)
        btn_layout.addWidget(self.btn_auth)

        layout.addLayout(btn_layout)

    def _handle_auth(self):
        password = self.txt_password.text().strip()
        if not password:
            self.lbl_error.setText("Password cannot be blank.")
            self.lbl_error.setVisible(True)
            return

        self.btn_auth.setEnabled(False)
        self.btn_auth.setText("Verifying...")
        self.lbl_error.setVisible(False)

        ok, msg = self.safety.authenticate_sudo(password)
        if ok:
            self.authenticated = True
            if self.on_success:
                try:
                    self.on_success()
                except Exception:
                    pass
            self.accept()
        else:
            self.lbl_error.setText(f"❌ {msg}")
            self.lbl_error.setVisible(True)
            self.txt_password.selectAll()
            self.txt_password.setFocus()
            self.btn_auth.setEnabled(True)
            self.btn_auth.setText("🛡️ Authenticate")


def prompt_root_required(
    parent: Optional[QWidget],
    action_description: str = "This tuning operation",
    safety: Optional[SafetyEngine] = None,
    on_elevated: Optional[Callable[[], None]] = None,
) -> bool:
    """
    Alert the user that root privileges are required and prompt to relaunch via pkexec.
    Guarantees the running application NEVER terminates unless the elevated child is fully ready.
    """
    target_safety = safety or getattr(parent, "safety", None)
    if target_safety and (target_safety.is_root or target_safety.dry_run):
        return True

    if os.geteuid() == 0:
        return True

    relaunch_as_root(parent, prompt_confirm=True, action_description=action_description)
    return False
