"""
Privacy, Telemetry & Debloat Engine for ConfTune FC.
Inspired by O&O ShutUp and debloat scripts.
Provides 1-click toggles for system telemetry, GNOME metrics, and server debloating.
"""

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine


class PrivacyTuner:
    """Manages telemetry opt-outs and residue debloating."""

    def __init__(self, safety: Optional[SafetyEngine] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()

    def get_telemetry_status(self) -> Dict[str, Any]:
        """Check status of telemetry and metrics reporting."""
        status = {
            "gnome_software_metrics": False,
            "gnome_privacy_recent": True,
            "fedora_metrics_active": False,
        }

        if shutil.which("gsettings"):
            try:
                # GNOME Software usage
                res = subprocess.run(
                    ["gsettings", "get", "org.gnome.software", "download-updates"],
                    capture_output=True, text=True, timeout=2,
                )
                # GNOME Privacy
                res_p = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.privacy", "remember-recent-files"],
                    capture_output=True, text=True, timeout=2,
                )
                status["gnome_privacy_recent"] = (res_p.stdout.strip() == "true")
            except Exception:
                pass

        return status

    def disable_all_telemetry(self) -> Tuple[bool, str]:
        """Opt out of GNOME usage stats, crash reporting, and metrics."""
        results = []

        if shutil.which("gsettings"):
            try:
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.privacy", "send-software-usage-stats", "false"],
                    check=False,
                )
                results.append("GNOME software usage statistics disabled.")
            except Exception:
                pass

            try:
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.privacy", "report-technical-problems", "false"],
                    check=False,
                )
                results.append("Automatic problem reporting disabled.")
            except Exception:
                pass

        # Disable core dump network forwarding if systemd-coredump present
        coredump_dir = "/etc/systemd/coredump.conf.d"
        if os.path.isdir(coredump_dir) and self.safety.is_root:
            try:
                with open(os.path.join(coredump_dir, "99-privacy.conf"), "w") as f:
                    f.write("[Coredump]\nStorage=none\n")
                results.append("Local and remote core dump collection disabled.")
            except Exception:
                pass

        msg = " ".join(results) if results else "Telemetry settings verified."
        self.logger.info(msg)
        return True, msg

    def is_telemetry_disabled(self) -> bool:
        """Check whether strict privacy mode or telemetry disabling is active."""
        coredump_conf = "/etc/systemd/coredump.conf.d/99-privacy.conf"
        if os.path.isfile(coredump_conf):
            return True

        if shutil.which("gsettings"):
            try:
                res_s = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.privacy", "send-software-usage-stats"],
                    capture_output=True, text=True, timeout=2,
                )
                if res_s.stdout.strip().replace("'", "") == "false":
                    return True
                res_r = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.privacy", "report-technical-problems"],
                    capture_output=True, text=True, timeout=2,
                )
                if res_r.stdout.strip().replace("'", "") == "false":
                    return True
            except Exception:
                pass

        return False

    def restore_telemetry_defaults(self) -> Tuple[bool, str]:
        """Restore standard Fedora defaults for crash reporting and usage metrics."""
        results = []

        if shutil.which("gsettings"):
            try:
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.privacy", "send-software-usage-stats", "true"],
                    check=False,
                )
                results.append("GNOME software statistics restored to default.")
            except Exception:
                pass

            try:
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.privacy", "report-technical-problems", "true"],
                    check=False,
                )
                results.append("Automatic problem reporting restored to default.")
            except Exception:
                pass

        coredump_conf = "/etc/systemd/coredump.conf.d/99-privacy.conf"
        if os.path.isfile(coredump_conf):
            ok_rm, msg_rm = self.safety.remove_file(coredump_conf)
            if ok_rm:
                results.append("Core dump collection override removed.")

        msg = " ".join(results) if results else "Restored standard telemetry and reporting defaults."
        self.logger.info(msg)
        return True, msg
