"""
Process Scheduling & Out-Of-Memory (OOM) Management for ConfTune FC.
Inspired by Process Lasso and systemd-oomd tuning.
Protects critical workloads from OOM termination and manages process scheduling priorities.
"""

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from conftune.core.backup_manager import BackupManager
from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine

OOMD_CONF_PATH = "/etc/systemd/oomd.conf.d/99-conftune.conf"


class ProcessTuner:
    """Manages systemd-oomd pressure limits, OOM scores, and process prioritization."""

    def __init__(self, safety: Optional[SafetyEngine] = None, backup_mgr: Optional[BackupManager] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.backup_mgr = backup_mgr or BackupManager()

    # --- 1. systemd-oomd Management ---

    def get_oomd_status(self) -> Dict[str, Any]:
        """Query systemd-oomd active status and current configuration."""
        status = {
            "installed": shutil.which("oomctl") is not None,
            "active": False,
            "memory_pressure_limit": "60% (default)",
            "swap_used_limit": "90% (default)",
        }
        try:
            res = subprocess.run(["systemctl", "is-active", "systemd-oomd"], capture_output=True, text=True, timeout=2)
            status["active"] = (res.stdout.strip() == "active")
        except Exception:
            pass

        if os.path.isfile(OOMD_CONF_PATH):
            try:
                with open(OOMD_CONF_PATH, "r") as f:
                    for line in f:
                        if "DefaultMemoryPressureLimit=" in line:
                            status["memory_pressure_limit"] = line.split("=", 1)[1].strip()
                        elif "SwapUsedLimit=" in line:
                            status["swap_used_limit"] = line.split("=", 1)[1].strip()
            except Exception:
                pass

        return status

    def configure_oomd_limits(self, memory_pressure: str = "70%", swap_limit: str = "90%") -> Tuple[bool, str]:
        """Configure /etc/systemd/oomd.conf.d/99-conftune.conf to adjust OOM sensitivity."""
        valid, msg = self.safety.verify_privilege("Configuring systemd-oomd parameters")
        if not valid:
            return False, msg

        self.backup_mgr.create_snapshot(
            profile_name="oomd_tuning",
            target_paths=[OOMD_CONF_PATH],
            notes="Adjust systemd-oomd memory pressure thresholds",
            dry_run=self.safety.dry_run,
        )

        content = (
            "# ConfTune FC - systemd-oomd Thresholds\n"
            "[OOM]\n"
            f"DefaultMemoryPressureLimit={memory_pressure}\n"
            f"SwapUsedLimit={swap_limit}\n"
        )

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would write {OOMD_CONF_PATH} with:\n{content}"

        try:
            ok_w, msg_w = self.safety.write_file(OOMD_CONF_PATH, content)
            if not ok_w:
                return False, msg_w

            # Reload oomd
            self.safety.run_command(["systemctl", "restart", "systemd-oomd"])
            self.logger.info(f"Applied systemd-oomd tuning in {OOMD_CONF_PATH}.")
            return True, f"systemd-oomd limits configured: Pressure={memory_pressure}, Swap={swap_limit}."
        except Exception as e:
            return False, str(e)

    # --- 2. OOM Killer Protection Score ---

    def protect_process_by_name(self, process_name: str, score_adjust: int = -500) -> Tuple[bool, str]:
        """
        Adjust /proc/<PID>/oom_score_adj to protect critical services from OOM kills.
        (-1000 = completely immune, -500 = highly protected, +1000 = kill first).
        """
        valid, msg = self.safety.verify_privilege(f"Protecting process {process_name}")
        if not valid:
            return False, msg

        score_adjust = max(-1000, min(1000, score_adjust))

        try:
            res = subprocess.run(["pgrep", "-f", process_name], capture_output=True, text=True, timeout=3)
            pids = res.stdout.strip().split()
            if not pids:
                return False, f"No running processes matching '{process_name}' found."

            if self.safety.dry_run:
                return True, f"[DRY RUN] Would set oom_score_adj={score_adjust} for {len(pids)} PIDs ({', '.join(pids[:5])})."

            applied = 0
            for pid in pids:
                score_file = f"/proc/{pid}/oom_score_adj"
                if os.path.isfile(score_file):
                    try:
                        ok_w, _ = self.safety.write_file(score_file, str(score_adjust))
                        if ok_w:
                            applied += 1
                    except Exception:
                        pass

            self.logger.info(f"Set oom_score_adj={score_adjust} on {applied} PIDs matching '{process_name}'.")
            return True, f"OOM score adjustment ({score_adjust}) applied to {applied} PIDs."
        except Exception as e:
            return False, str(e)
