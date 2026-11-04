"""
Autostart Applications, Core Dump Limiter & ABRT Management for ConfTune FC.
Inspired by Stacer. Manages autostart desktop entries, systemd-coredump limits,
and Automatic Bug Reporting Tool (ABRT) daemons.
"""

import glob
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from conftune.core.backup_manager import BackupManager
from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine

COREDUMP_CONF_PATH = "/etc/systemd/coredump.conf.d/99-conftune.conf"
USER_AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
SYSTEM_AUTOSTART_DIR = "/etc/xdg/autostart"


class AutostartTuner:
    """Manages autostart launchers, core dump disk retention, and ABRT services."""

    def __init__(self, safety: Optional[SafetyEngine] = None, backup_mgr: Optional[BackupManager] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.backup_mgr = backup_mgr or BackupManager()

    # --- 1. Autostart Applications Manager ---

    def list_autostart_entries(self) -> List[Dict[str, Any]]:
        """Discover and parse user and system autostart .desktop launchers."""
        entries = []
        paths = []
        if os.path.isdir(USER_AUTOSTART_DIR):
            paths.extend([(f, "user") for f in glob.glob(os.path.join(USER_AUTOSTART_DIR, "*.desktop"))])
        if os.path.isdir(SYSTEM_AUTOSTART_DIR):
            paths.extend([(f, "system") for f in glob.glob(os.path.join(SYSTEM_AUTOSTART_DIR, "*.desktop"))])

        for filepath, scope in paths:
            try:
                data = {
                    "path": filepath,
                    "filename": os.path.basename(filepath),
                    "scope": scope,
                    "name": os.path.basename(filepath),
                    "exec": "",
                    "comment": "",
                    "enabled": True,
                }
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("Name=") and data["name"] == os.path.basename(filepath):
                            data["name"] = line.split("=", 1)[1]
                        elif line.startswith("Exec=") and not data["exec"]:
                            data["exec"] = line.split("=", 1)[1]
                        elif line.startswith("Comment=") and not data["comment"]:
                            data["comment"] = line.split("=", 1)[1]
                        elif line.lower() in ["hidden=true", "x-gnome-autostart-enabled=false"]:
                            data["enabled"] = False
                entries.append(data)
            except Exception:
                pass

        return entries

    def toggle_autostart_entry(self, entry_path: str, enable: bool) -> Tuple[bool, str]:
        """Enable or disable an autostart desktop entry."""
        if not os.path.isfile(entry_path):
            return False, f"Autostart file '{entry_path}' not found."

        try:
            with open(entry_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            new_lines = []
            for l in lines:
                if l.startswith("Hidden=") or l.startswith("X-GNOME-Autostart-enabled="):
                    continue
                new_lines.append(l)

            if not enable:
                new_lines.append("Hidden=true\n")
                new_lines.append("X-GNOME-Autostart-enabled=false\n")

            with open(entry_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            action = "enabled" if enable else "disabled"
            self.logger.info(f"Autostart launcher '{os.path.basename(entry_path)}' {action}.")
            return True, f"Launcher {action}."
        except Exception as e:
            return False, str(e)

    # --- 2. Core Dump Disk Limiter ---

    def configure_coredump_limit(self, max_use: str = "200M") -> Tuple[bool, str]:
        """Configure /etc/systemd/coredump.conf.d/99-conftune.conf to cap core dump waste."""
        valid, msg = self.safety.verify_privilege("Configuring systemd-coredump limits")
        if not valid:
            return False, msg

        self.backup_mgr.create_snapshot(
            profile_name="coredump_tuning",
            target_paths=[COREDUMP_CONF_PATH],
            notes="Cap coredump disk usage",
            dry_run=self.safety.dry_run,
        )

        content = (
            "# ConfTune FC - Core Dump Storage Limits\n"
            "[Coredump]\n"
            f"MaxUse={max_use}\n"
            "ProcessSizeMax=500M\n"
            "KeepFree=1G\n"
        )

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would write {COREDUMP_CONF_PATH} with:\n{content}"

        try:
            os.makedirs(os.path.dirname(COREDUMP_CONF_PATH), exist_ok=True)
            with open(COREDUMP_CONF_PATH, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.info(f"Applied core dump storage limit ({max_use}) in {COREDUMP_CONF_PATH}.")
            return True, f"Core dump disk storage ceiling set to {max_use}."
        except Exception as e:
            return False, str(e)

    # --- 3. ABRT Bug Reporting Daemons ---

    def get_abrt_status(self) -> Dict[str, Any]:
        """Query ABRT background daemon states."""
        services = ["abrt-ccpp.service", "abrtd.service", "abrt-oops.service"]
        status = {}
        for s in services:
            try:
                res = subprocess.run(["systemctl", "is-active", s], capture_output=True, text=True, timeout=2)
                status[s] = (res.stdout.strip() == "active")
            except Exception:
                status[s] = False
        return status

    def toggle_abrt_services(self, enable: bool) -> Tuple[bool, str]:
        """Enable or disable ABRT background daemons."""
        action = "enable --now" if enable else "disable --now"
        valid, msg = self.safety.verify_privilege(f"{action.capitalize()} ABRT services")
        if not valid:
            return False, msg

        services = ["abrt-ccpp.service", "abrtd.service", "abrt-oops.service"]
        if self.safety.dry_run:
            return True, f"[DRY RUN] Would execute: systemctl {action} {' '.join(services)}"

        count = 0
        for s in services:
            try:
                subprocess.run(["systemctl", "enable" if enable else "disable", "--now", s], check=False)
                count += 1
            except Exception:
                pass

        verb = "enabled" if enable else "disabled"
        self.logger.info(f"ABRT background services {verb}.")
        return True, f"ABRT background bug reporting services {verb}."
