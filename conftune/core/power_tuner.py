"""
CPU Power, Governor & Hardware Energy Management for ConfTune FC.
Inspired by QuickCPU and auto-cpufreq. Controls CPU EPP (Energy Performance Preference),
scaling governors, Transparent Huge Pages (THP), power-profiles-daemon, and Feral GameMode.
"""

import glob
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine

THP_FILE = "/sys/kernel/mm/transparent_hugepage/enabled"


class PowerTuner:
    """Manages CPU governors, EPP policies, power-profiles, and memory paging."""

    def __init__(self, safety: Optional[SafetyEngine] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()

    # --- 1. CPU Scaling Governors ---

    def get_available_governors(self) -> List[str]:
        """Query available CPU scaling governors."""
        avail_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
        if os.path.isfile(avail_file):
            try:
                with open(avail_file, "r") as f:
                    return f.read().strip().split()
            except Exception:
                pass
        return ["performance", "powersave", "schedutil", "ondemand"]

    def get_current_governor(self) -> str:
        """Query active scaling governor on cpu0."""
        gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        if os.path.isfile(gov_file):
            try:
                with open(gov_file, "r") as f:
                    return f.read().strip()
            except Exception:
                pass
        return "unknown"

    def set_governor_all_cores(self, governor: str) -> Tuple[bool, str]:
        """Apply scaling governor across all CPU cores."""
        valid, msg = self.safety.verify_privilege(f"Setting CPU governor to {governor}")
        if not valid:
            return False, msg

        gov_files = glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor")
        if not gov_files:
            return False, "cpufreq governor interface not found on this system."

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would write '{governor}' to {len(gov_files)} CPU core governor files."

        count = 0
        try:
            for gf in gov_files:
                ok_w, msg_w = self.safety.write_file(gf, governor)
                if not ok_w:
                    return False, msg_w
                count += 1
            self.logger.info(f"Applied CPU governor '{governor}' across {count} cores.")
            return True, f"CPU scaling governor set to '{governor}' across {count} cores."
        except Exception as e:
            return False, str(e)

    # --- 2. CPU Energy Performance Preference (EPP) ---

    def has_epp_support(self) -> bool:
        """Check if amd-pstate-epp or intel_pstate EPP interface is available."""
        return len(glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference")) > 0

    def get_current_epp(self) -> str:
        """Read EPP mode from cpu0."""
        epp_file = "/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference"
        if os.path.isfile(epp_file):
            try:
                with open(epp_file, "r") as f:
                    return f.read().strip()
            except Exception:
                pass
        return "none"

    def set_epp_all_cores(self, epp_mode: str) -> Tuple[bool, str]:
        """Set EPP mode (performance, balance_performance, balance_power, power)."""
        valid, msg = self.safety.verify_privilege(f"Setting CPU EPP to {epp_mode}")
        if not valid:
            return False, msg

        files = glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference")
        if not files:
            return False, "CPU EPP hardware interface not supported on this processor/driver."

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would set EPP to '{epp_mode}' across {len(files)} CPU cores."

        count = 0
        try:
            for f_path in files:
                ok_w, msg_w = self.safety.write_file(f_path, epp_mode)
                if not ok_w:
                    return False, msg_w
                count += 1
            self.logger.info(f"Applied CPU EPP '{epp_mode}' across {count} cores.")
            return True, f"CPU EPP mode set to '{epp_mode}' across {count} cores."
        except Exception as e:
            return False, str(e)

    # --- 3. Power Profiles Daemon ---

    def get_power_profiles_status(self) -> Dict[str, Any]:
        """Query power-profiles-daemon status."""
        status = {"installed": shutil.which("powerprofilesctl") is not None, "active": "unknown"}
        if status["installed"]:
            try:
                res = subprocess.run(["powerprofilesctl", "get"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    status["active"] = res.stdout.strip()
            except Exception:
                pass
        return status

    def set_power_profile(self, profile: str) -> Tuple[bool, str]:
        """Switch power-profiles-daemon profile (performance, balanced, power-saver)."""
        if not shutil.which("powerprofilesctl"):
            return False, "powerprofilesctl utility not found."
        try:
            res = subprocess.run(["powerprofilesctl", "set", profile], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                self.logger.info(f"Set power-profiles-daemon to '{profile}'.")
                return True, f"Active system power profile set to '{profile}'."
            return False, res.stderr.strip()
        except Exception as e:
            return False, str(e)

    # --- 4. Transparent Huge Pages (THP) ---

    def get_thp_status(self) -> Dict[str, str]:
        """Read active and available THP modes."""
        info = {"active": "unknown", "raw": ""}
        if os.path.isfile(THP_FILE):
            try:
                with open(THP_FILE, "r") as f:
                    content = f.read().strip()
                info["raw"] = content
                for item in content.split():
                    if item.startswith("[") and item.endswith("]"):
                        info["active"] = item[1:-1]
            except Exception:
                pass
        return info

    def set_thp_mode(self, mode: str) -> Tuple[bool, str]:
        """Set THP mode: 'always', 'madvise', or 'never'."""
        valid, msg = self.safety.verify_privilege(f"Setting Transparent Huge Pages to {mode}")
        if not valid:
            return False, msg

        if not os.path.isfile(THP_FILE):
            return False, "Transparent Huge Pages interface not available."

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would write '{mode}' to {THP_FILE}"

        try:
            ok_w, msg_w = self.safety.write_file(THP_FILE, mode)
            if not ok_w:
                return False, msg_w
            self.logger.info(f"Transparent Huge Pages (THP) set to '{mode}'.")
            return True, f"Transparent Huge Pages mode set to '{mode}'."
        except Exception as e:
            return False, str(e)

    # --- 5. Feral GameMode ---

    def get_gamemode_status(self) -> Dict[str, Any]:
        """Check if gamemoded daemon is installed and active."""
        installed = shutil.which("gamemoded") is not None
        running = False
        if installed:
            try:
                res = subprocess.run(["gamemoded", "-s"], capture_output=True, text=True, timeout=2)
                running = "gamemode is active" in res.stdout.lower()
            except Exception:
                pass
        return {"installed": installed, "active": running}
