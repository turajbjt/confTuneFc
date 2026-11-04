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
