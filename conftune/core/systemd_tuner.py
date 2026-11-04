"""
Systemd Boot and Service Optimizer for ConfTune FC.
Analyzes systemd-analyze blame, detects boot bottlenecks, optimizes background daemons,
and manages journald log size limits in /etc/systemd/journald.conf.d/99-conftune.conf.
"""

import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from conftune.core.backup_manager import BackupManager
from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine

JOURNALD_CONF_PATH = "/etc/systemd/journald.conf.d/99-conftune.conf"

RECOMMENDED_SERVER_DISABLE = [
    ("ModemManager.service", "Cellular modem management daemon. Unneeded on servers and wired desktops."),
    ("bluetooth.service", "Bluetooth daemon. Safe to disable on headless servers and rack mounts."),
    ("cups.service", "Common Unix Printing System. Safe to disable on non-printing servers."),
    ("avahi-daemon.service", "mDNS/DNS-SD discovery. Can be disabled if local hostname broadcast is unneeded."),
    ("plymouth-quit-wait.service", "Graphical boot splash wait barrier. Delays server startup times."),
]


class SystemdTuner:
    """Provides boot analysis, daemon management, and journald size caps."""

    def __init__(self, safety: Optional[SafetyEngine] = None, backup_mgr: Optional[BackupManager] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.backup_mgr = backup_mgr or BackupManager()

    def get_boot_blame(self, top_n: int = 15) -> List[Dict[str, Any]]:
        """Parse `systemd-analyze blame` output."""
        blame_items = []
        if not shutil.which("systemd-analyze"):
            return blame_items

        try:
            res = subprocess.run(
                ["systemd-analyze", "blame"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0:
                for line in res.stdout.strip().split("\n")[:top_n]:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        duration_str, unit_name = parts
                        blame_items.append({
                            "duration": duration_str,
                            "unit": unit_name,
                        })
        except Exception as e:
            self.logger.warning(f"Error running systemd-analyze blame: {e}")

        return blame_items

    def get_boot_time_summary(self) -> str:
        """Get summary from `systemd-analyze` (kernel, initrd, userspace)."""
        if not shutil.which("systemd-analyze"):
            return "systemd-analyze not available"
        try:
            res = subprocess.run(["systemd-analyze"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return res.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return "Unknown boot time"

    def get_server_removable_services(self) -> List[Dict[str, Any]]:
        """Check status of services typically safe to disable on servers."""
        status_list = []
        for service, desc in RECOMMENDED_SERVER_DISABLE:
            is_active = self._check_service_active(service)
            is_enabled = self._check_service_enabled(service)
            status_list.append({
                "service": service,
                "description": desc,
                "active": is_active,
                "enabled": is_enabled,
            })
        return status_list

    def set_service_state(self, service_name: str, enable: bool) -> Tuple[bool, str]:
        """Enable/start or disable/stop a systemd service."""
        action_verb = "enable --now" if enable else "disable --now"
        valid, msg = self.safety.verify_privilege(f"{action_verb.capitalize()} {service_name}")
        if not valid:
            return False, msg

        if self.safety.dry_run:
            self.logger.info(f"[DRY RUN] Would execute: systemctl {action_verb} {service_name}")
            return True, f"[DRY RUN] Would {action_verb} {service_name}"

        cmd = ["systemctl", "enable" if enable else "disable", "--now", service_name]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                self.logger.info(f"Successfully ran systemctl {action_verb} {service_name}")
                return True, f"Service {service_name} {'enabled' if enable else 'disabled'}."
            return False, f"systemctl error: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Failed to modify service {service_name}: {e}"

    def configure_journald_limit(self, max_size: str = "300M") -> Tuple[bool, str]:
        """Write /etc/systemd/journald.conf.d/99-conftune.conf to cap log usage."""
        valid, msg = self.safety.verify_privilege("Configuring systemd-journald limits")
        if not valid:
            return False, msg

        self.backup_mgr.create_snapshot(
            profile_name="journald_tuning",
            target_paths=[JOURNALD_CONF_PATH],
            notes="Cap journald storage size",
            dry_run=self.safety.dry_run,
        )

        content = (
            "# ConfTune FC - Journald Optimization\n"
            "[Journal]\n"
            f"SystemMaxUse={max_size}\n"
            "RuntimeMaxUse=100M\n"
            "SystemMaxFiles=10\n"
        )

        if self.safety.dry_run:
            self.logger.info(f"[DRY RUN] Would write {JOURNALD_CONF_PATH} with:\n{content}")
            return True, f"[DRY RUN] journald size cap ({max_size}) simulated."

        try:
            os.makedirs(os.path.dirname(JOURNALD_CONF_PATH), exist_ok=True)
            with open(JOURNALD_CONF_PATH, "w", encoding="utf-8") as f:
                f.write(content)

            # Restart journald to pick up changes
            subprocess.run(["systemctl", "restart", "systemd-journald"], check=False)
            # Vacuum logs to respect limit immediately
            if shutil.which("journalctl"):
                subprocess.run(["journalctl", f"--vacuum-size={max_size}"], check=False)

            self.logger.info(f"Applied journald storage limit ({max_size}) in {JOURNALD_CONF_PATH}.")
            return True, f"Journald maximum disk usage set to {max_size}."
        except Exception as e:
            err = f"Failed to configure journald: {e}"
            self.logger.error(err)
            return False, err

    def _check_service_active(self, service: str) -> bool:
        try:
            res = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True, timeout=2)
            return res.stdout.strip() == "active"
        except Exception:
            return False

    def _check_service_enabled(self, service: str) -> bool:
        try:
            res = subprocess.run(["systemctl", "is-enabled", service], capture_output=True, text=True, timeout=2)
            return res.stdout.strip() in ["enabled", "enabled-runtime"]
        except Exception:
            return False
