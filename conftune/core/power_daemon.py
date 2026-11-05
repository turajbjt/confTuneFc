"""
Dynamic Power & Energy Performance Preference Daemon for ConfTune FC.
Automatically monitors AC vs. Battery power states and adapts CPU governors
and Energy Performance Preferences (EPP) for optimal performance and battery life.
"""

import glob
import os
import signal
import sys
import time
from typing import Any, Dict, Optional, Tuple

from conftune.core.logger import get_logger
from conftune.core.power_tuner import PowerTuner
from conftune.core.safety import SafetyEngine


class PowerDaemon:
    """Monitors system power supplies and switches CPU governors / EPP policies dynamically."""

    def __init__(self, power_tuner: Optional[PowerTuner] = None, safety: Optional[SafetyEngine] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.power_tuner = power_tuner or PowerTuner(safety=self.safety)
        self.last_state: Optional[str] = None
        self._running = False

    def detect_power_state(self) -> Dict[str, Any]:
        """
        Inspect /sys/class/power_supply to determine whether system is running on AC or Battery.
        """
        supplies = glob.glob("/sys/class/power_supply/*")
        has_battery = False
        ac_online = False
        battery_level: Optional[int] = None
        battery_status = "Unknown"

        for ps in supplies:
            type_file = os.path.join(ps, "type")
            online_file = os.path.join(ps, "online")
            capacity_file = os.path.join(ps, "capacity")
            status_file = os.path.join(ps, "status")

            ps_type = ""
            if os.path.isfile(type_file):
                try:
                    with open(type_file, "r") as f:
                        ps_type = f.read().strip().lower()
                except Exception:
                    pass

            # Check for AC / Mains
            if ps_type in ["mains", "ac"]:
                if os.path.isfile(online_file):
                    try:
                        with open(online_file, "r") as f:
                            if f.read().strip() == "1":
                                ac_online = True
                    except Exception:
                        pass

            # Check for Battery
            if ps_type == "battery":
                has_battery = True
                if os.path.isfile(capacity_file):
                    try:
                        with open(capacity_file, "r") as f:
                            battery_level = int(f.read().strip())
                    except Exception:
                        pass
                if os.path.isfile(status_file):
                    try:
                        with open(status_file, "r") as f:
                            battery_status = f.read().strip()
                    except Exception:
                        pass

        # If system has no battery (Desktop, Bare-Metal Server, VM, Container), default to AC
        if not has_battery:
            state = "ac"
        elif ac_online:
            state = "ac"
        else:
            state = "battery"

        return {
            "state": state,
            "has_battery": has_battery,
            "ac_online": ac_online,
            "battery_level": battery_level,
            "battery_status": battery_status,
        }

    def apply_profile(self, state: str) -> Tuple[bool, str]:
        """
        Apply governor and EPP profile corresponding to the given power state ('ac' or 'battery').
        """
        avail_govs = self.power_tuner.get_available_governors()
        if state == "battery":
            target_gov = "powersave" if "powersave" in avail_govs else avail_govs[0]
            target_epp = "balance_power"
        else:
            target_gov = "performance" if "performance" in avail_govs else "schedutil" if "schedutil" in avail_govs else avail_govs[0]
            target_epp = "balance_performance"

        ok_gov, msg_gov = self.power_tuner.set_governor_all_cores(target_gov)
        if self.power_tuner.has_epp_support():
            ok_epp, msg_epp = self.power_tuner.set_epp_all_cores(target_epp)
        else:
            ok_epp, msg_epp = True, "EPP hardware interface not present (skipped)"

        summary = f"[{state.upper()}] Governor: {target_gov} ({msg_gov}) | EPP: {target_epp} ({msg_epp})"
        self.logger.info(summary)
        self.last_state = state
        return (ok_gov and ok_epp), summary

    def run_once(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Perform a single inspection and apply appropriate profile if state has changed."""
        info = self.detect_power_state()
        state = info["state"]
        ok, msg = self.apply_profile(state)
        return ok, msg, info

    def run_daemon(self, interval_seconds: int = 15) -> None:
        """Run continuous monitoring loop for systemd service or background daemon."""
        self._running = True

        def _handle_signal(signum, frame):
            self.logger.info(f"Received signal {signum}. Terminating power daemon gracefully.")
            self._running = False

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        self.logger.info(f"ConfTune FC Power Daemon started (poll interval: {interval_seconds}s).")
        while self._running:
            try:
                info = self.detect_power_state()
                current_state = info["state"]
                if current_state != self.last_state:
                    self.logger.info(f"Power state transition detected: {self.last_state} -> {current_state}")
                    self.apply_profile(current_state)
            except Exception as e:
                self.logger.error(f"Error in power daemon cycle: {e}")

            # Sleep in 1-second slices so shutdown signals respond instantly
            for _ in range(interval_seconds):
                if not self._running:
                    break
                time.sleep(1)

        self.logger.info("ConfTune FC Power Daemon stopped.")
