"""
Authentication & Privilege Management for ConfTune FC GUI.
Segregates administrative root/sudo operations from casual user offerings.
"""

import os
import shutil
import subprocess
import sys
from typing import Optional
from PyQt6.QtWidgets import QMessageBox, QWidget


def is_root() -> bool:
    """Return True if current process has root privileges (UID 0)."""
    return os.geteuid() == 0


def prompt_root_required(parent: Optional[QWidget], action_description: str = "This operation") -> None:
    """
    Alert the casual user that root/sudo privileges are required.
    Offers instant PolicyKit (pkexec) elevation if available, or guides the user to run with sudo.
    """
    pkexec_bin = shutil.which("pkexec")
    msg = (
        f"<b>{action_description}</b> requires administrative (root/sudo) privileges.<br><br>"
        "System configuration files in <code>/etc</code> and kernel parameters in <code>/sys</code> "
        "are protected from casual user modification.<br><br>"
    )
    if pkexec_bin:
        msg += "Would you like to relaunch ConfTune FC with Administrator privileges using PolicyKit (pkexec)?"
        reply = QMessageBox.question(
            parent,
            "Administrator Access Required",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            main_py = os.path.abspath(sys.argv[0])
            cmd = [pkexec_bin, sys.executable, main_py]
            try:
                subprocess.Popen(cmd)
                sys.exit(0)
            except Exception as e:
                QMessageBox.critical(parent, "Elevation Error", f"Could not elevate process: {e}")
    else:
        msg += (
            "Please relaunch ConfTune FC from terminal with root access:<br><br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;<code>sudo conftune-fc</code>"
        )
        QMessageBox.warning(parent, "Administrator Access Required", msg)
