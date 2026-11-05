"""
Authentication & Privilege Management for ConfTune FC GUI.
Provides interactive in-app sudo elevation, secure password dialogs,
and safeguards against application termination or crashes during administrative tasks.
"""

import getpass
import os
import shutil
import sys
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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
            f"Superuser (sudo) privileges are required to modify system configuration.<br>"
            f"Enter administrator password for <b>{current_user}</b>:"
        )
        lbl_prompt.setWordWrap(True)
        lbl_prompt.setStyleSheet("color: #dedede; font-size: 12px; line-height: 1.4;")
        layout.addWidget(lbl_prompt)

        # Password input field
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Enter sudo password...")
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

        self.btn_auth = QPushButton("🛡️ Authenticate (sudo)")
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
            self.btn_auth.setText("🛡️ Authenticate (sudo)")


def prompt_root_required(
    parent: Optional[QWidget],
    action_description: str = "This operation",
    safety: Optional[SafetyEngine] = None,
    on_elevated: Optional[Callable[[], None]] = None,
) -> bool:
    """
    Alert the user that root/sudo privileges are required, and prompts for
    in-app sudo elevation. Returns True if elevated/authorized, False otherwise.
    Guarantees the running application NEVER terminates or crashes.
    """
    target_safety = safety or getattr(parent, "safety", None)

    # If already root or running simulation, permit immediately
    if target_safety and (target_safety.is_root or target_safety.dry_run):
        return True

    # Check for passwordless sudo authorization
    if target_safety and target_safety.check_passwordless_sudo():
        if on_elevated:
            on_elevated()
        return True

    # If safety engine is present, open native in-app authentication dialog
    if target_safety:
        dialog = SudoAuthDialog(parent, action_description, target_safety, on_success=on_elevated)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted and dialog.authenticated:
            return True
        return False

    # Fallback advisory message box if safety engine is somehow not attached
    QMessageBox.warning(
        parent,
        "Administrator Access Required",
        f"<b>{action_description}</b> requires root or sudo privileges.<br><br>"
        "Please run ConfTune FC with sudo:<br><code>sudo conftune-fc</code>",
    )
    return False
