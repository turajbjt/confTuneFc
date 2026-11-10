"""
Storage, I/O Scheduler, and ZRAM Optimizer for ConfTune FC.
Manages SSD/NVMe fstrim maintenance, I/O queues, and ZRAM swap configuration.
"""

import glob
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from conftune.core.backup_manager import BackupManager
from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine

ZRAM_CONF_PATH = "/etc/systemd/zram-generator.conf"


class StorageTuner:
    """Manages disk trimming, block scheduler policies, and ZRAM settings."""

    def __init__(self, safety: Optional[SafetyEngine] = None, backup_mgr: Optional[BackupManager] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.backup_mgr = backup_mgr or BackupManager()

    def get_fstrim_status(self) -> Dict[str, Any]:
        """Check status of fstrim.timer systemd unit."""
        status = {"active": False, "enabled": False}
        try:
            res_a = subprocess.run(["systemctl", "is-active", "fstrim.timer"], capture_output=True, text=True, timeout=2)
            status["active"] = (res_a.stdout.strip() == "active")
            res_e = subprocess.run(["systemctl", "is-enabled", "fstrim.timer"], capture_output=True, text=True, timeout=2)
            status["enabled"] = (res_e.stdout.strip() == "enabled")
        except Exception:
            pass
        return status

    def enable_fstrim_timer(self) -> Tuple[bool, str]:
        """Enable and start fstrim.timer for periodic SSD/NVMe background TRIM."""
        valid, msg = self.safety.verify_privilege("Enabling fstrim.timer")
        if not valid:
            return False, msg

        if self.safety.dry_run:
            return True, "[DRY RUN] Would execute: systemctl enable --now fstrim.timer"

        try:
            res = self.safety.run_command(["systemctl", "enable", "--now", "fstrim.timer"], timeout=5)
            if res.returncode == 0:
                self.logger.info("Enabled and started fstrim.timer.")
                return True, "Weekly SSD/NVMe TRIM timer enabled and activated."
            return False, res.stderr.strip()
        except Exception as e:
            return False, str(e)

    def disable_fstrim_timer(self) -> Tuple[bool, str]:
        """Disable and stop fstrim.timer."""
        valid, msg = self.safety.verify_privilege("Disabling fstrim.timer")
        if not valid:
            return False, msg

        if self.safety.dry_run:
            return True, "[DRY RUN] Would execute: systemctl disable --now fstrim.timer"

        try:
            res = self.safety.run_command(["systemctl", "disable", "--now", "fstrim.timer"], timeout=5)
            if res.returncode == 0:
                self.logger.info("Disabled and stopped fstrim.timer.")
                return True, "SSD/NVMe TRIM timer disabled."
            return False, res.stderr.strip()
        except Exception as e:
            return False, str(e)

    def run_fstrim_now(self) -> Tuple[bool, str]:
        """Run manual discard operation across all mounted filesystems."""
        valid, msg = self.safety.verify_privilege("Executing fstrim")
        if not valid:
            return False, msg

        if self.safety.dry_run:
            return True, "[DRY RUN] Would execute: fstrim -av"

        try:
            res = self.safety.run_command(["fstrim", "-av"], timeout=60)
            if res.returncode == 0:
                self.logger.info(f"fstrim output: {res.stdout.strip()}")
                return True, res.stdout.strip()
            return False, res.stderr.strip()
        except Exception as e:
            return False, str(e)

    def get_disk_schedulers(self) -> List[Dict[str, str]]:
        """List current I/O schedulers for block devices."""
        schedulers = []
        for path in sorted(glob.glob("/sys/block/*/queue/scheduler")):
            dev_name = path.split("/")[3]
            # Ignore loop, ram, and zram devices
            if dev_name.startswith(("loop", "ram", "zram", "dm-")):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                # Selected scheduler is wrapped in brackets, e.g. "none [mq-deadline] kyber bfq"
                schedulers.append({
                    "device": dev_name,
                    "available": content,
                    "active": self._parse_active_scheduler(content),
                })
            except Exception:
                pass
        return schedulers

    def _parse_active_scheduler(self, sched_str: str) -> str:
        for item in sched_str.split():
            if item.startswith("[") and item.endswith("]"):
                return item[1:-1]
        return "default"

    def set_disk_scheduler(self, device: str, scheduler: str) -> Tuple[bool, str]:
        """Set scheduler for specific block device."""
        sched_file = f"/sys/block/{device}/queue/scheduler"
        if not os.path.isfile(sched_file):
            return False, f"Device {device} scheduler interface not found."

        valid, msg = self.safety.verify_privilege(f"Setting I/O scheduler on {device}")
        if not valid:
            return False, msg

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would set scheduler for {device} to {scheduler}"

        try:
            ok_w, msg_w = self.safety.write_file(sched_file, scheduler)
            if not ok_w:
                return False, msg_w
            self.logger.info(f"Set I/O scheduler on {device} to '{scheduler}'.")
            return True, f"Scheduler on {device} changed to {scheduler}."
        except Exception as e:
            return False, str(e)

    def configure_zram(self, size_percent: int = 50, max_size_mb: int = 8192) -> Tuple[bool, str]:
        """Configure /etc/systemd/zram-generator.conf."""
        valid, msg = self.safety.verify_privilege("Configuring ZRAM swap generator")
        if not valid:
            return False, msg

        self.backup_mgr.create_snapshot(
            profile_name="zram_config",
            target_paths=[ZRAM_CONF_PATH],
            notes="Configure zram-generator",
            dry_run=self.safety.dry_run,
        )

        content = (
            "# ConfTune FC - ZRAM Generator Configuration\n"
            "[zram0]\n"
            f"zram-size = min(ram / 2, {max_size_mb})\n"
            "compression-algorithm = zstd\n"
            "swap-priority = 100\n"
        )

        if self.safety.dry_run:
            self.logger.info(f"[DRY RUN] Would write {ZRAM_CONF_PATH} with:\n{content}")
            return True, "[DRY RUN] ZRAM configuration simulated."

        try:
            ok_w, msg_w = self.safety.write_file(ZRAM_CONF_PATH, content)
            if not ok_w:
                return False, msg_w
            self.logger.info(f"Wrote ZRAM configuration to {ZRAM_CONF_PATH}.")
            return True, "ZRAM generator configuration saved."
        except Exception as e:
            return False, str(e)

    def is_zram_customized(self) -> bool:
        """Check if custom ZRAM generator override file exists."""
        return os.path.isfile(ZRAM_CONF_PATH)

    def restore_default_zram(self) -> Tuple[bool, str]:
        """Restore default system ZRAM generator by removing /etc/systemd/zram-generator.conf."""
        valid, msg = self.safety.verify_privilege("Restoring default ZRAM configuration")
        if not valid:
            return False, msg

        if os.path.isfile(ZRAM_CONF_PATH):
            self.backup_mgr.create_snapshot(
                profile_name="zram_pre_restore",
                target_paths=[ZRAM_CONF_PATH],
                notes="Backup before restoring default ZRAM generator",
                dry_run=self.safety.dry_run,
            )

        ok_rm, msg_rm = self.safety.remove_file(ZRAM_CONF_PATH)
        if not ok_rm:
            return False, f"Failed to remove {ZRAM_CONF_PATH}: {msg_rm}"

        self.logger.info("Restored default ZRAM generator configuration.")
        return True, "Removed /etc/systemd/zram-generator.conf and restored Fedora default ZRAM settings."
