"""
Fedy Post-Install, Codecs & Desktop Tweaks Engine for ConfTune FC.
Inspired by Fedy (Fedora Utils). Manages RPM Fusion, multimedia codecs,
Microsoft TrueType fonts, font rendering enhancements, and GNOME productivity tweaks.
"""

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from conftune.core.backup_manager import BackupManager
from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine

FONTCONFIG_USER_DIR = os.path.expanduser("~/.config/fontconfig")
FONTCONFIG_USER_FILE = os.path.join(FONTCONFIG_USER_DIR, "fonts.conf")

OPTIMIZED_FONTCONFIG = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <!-- ConfTune FC: Subpixel RGB Anti-Aliasing and LCD Filtering -->
  <match target="font">
    <edit mode="assign" name="antialias"><bool>true</bool></edit>
    <edit mode="assign" name="hinting"><bool>true</bool></edit>
    <edit mode="assign" name="hintstyle"><const>hintslight</const></edit>
    <edit mode="assign" name="rgba"><const>rgb</const></edit>
    <edit mode="assign" name="lcdfilter"><const>lcddefault</const></edit>
  </match>
</fontconfig>
"""


class FedyTuner:
    """Provides Fedy-style post-install automation and desktop refinements."""

    def __init__(self, safety: Optional[SafetyEngine] = None, backup_mgr: Optional[BackupManager] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.backup_mgr = backup_mgr or BackupManager()

    # --- 1. RPM Fusion Repositories ---

    def is_rpmfusion_installed(self) -> Dict[str, bool]:
        """Check if RPM Fusion Free and Nonfree are installed."""
        free = os.path.isfile("/etc/yum.repos.d/rpmfusion-free.repo")
        nonfree = os.path.isfile("/etc/yum.repos.d/rpmfusion-nonfree.repo")
        return {"free": free, "nonfree": nonfree}

    def install_rpmfusion(self) -> Tuple[bool, str]:
        """Enable RPM Fusion Free & Nonfree repositories on Fedora / EL."""
        valid, msg = self.safety.verify_privilege("Installing RPM Fusion repositories")
        if not valid:
            return False, msg

        dnf_bin = shutil.which("dnf5") or shutil.which("dnf")
        if not dnf_bin:
            return False, "DNF package manager not found."

        cmd = [
            dnf_bin, "install", "-y",
            "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm",
            "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm",
        ]

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would execute: {' '.join(cmd)}"

        try:
            res = self.safety.run_command(["bash", "-c", " ".join(cmd)], timeout=60)
            if res.returncode == 0:
                self.logger.info("Successfully enabled RPM Fusion Free and Nonfree.")
                return True, "RPM Fusion Free and Nonfree repositories installed successfully."
            return False, f"Failed to enable RPM Fusion: {res.stderr.strip()}"
        except Exception as e:
            return False, str(e)

    # --- 2. Multimedia Codecs & Hardware Acceleration ---

    def install_multimedia_codecs(self) -> Tuple[bool, str]:
        """Install GStreamer ugly/bad plugins, ffmpeg, OpenH264, and VA-API acceleration."""
        valid, msg = self.safety.verify_privilege("Installing multimedia codecs")
        if not valid:
            return False, msg

        dnf_bin = shutil.which("dnf5") or shutil.which("dnf")
        if not dnf_bin:
            return False, "DNF package manager not found."

        packages = [
            "gstreamer1-plugins-ugly",
            "gstreamer1-plugins-bad-free",
            "gstreamer1-plugin-openh264",
            "ffmpeg",
            "libva",
            "libva-utils",
        ]

        cmd = [dnf_bin, "install", "-y"] + packages

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would execute: {' '.join(cmd)}"

        try:
            res = self.safety.run_command(cmd, timeout=180)
            if res.returncode == 0:
                self.logger.info("Installed multimedia codecs and hardware video acceleration.")
                return True, "Multimedia codecs (GStreamer, FFmpeg, OpenH264, VA-API) installed."
            return False, f"Codec installation error: {res.stderr.strip()}"
        except Exception as e:
            return False, str(e)

    # --- 3. Font Rendering & Microsoft TrueType Fonts ---

    def configure_font_rendering(self) -> Tuple[bool, str]:
        """Deploy crisp subpixel RGB antialiasing and slight hinting config."""
        try:
            os.makedirs(FONTCONFIG_USER_DIR, exist_ok=True)
            with open(FONTCONFIG_USER_FILE, "w", encoding="utf-8") as f:
                f.write(OPTIMIZED_FONTCONFIG)

            if shutil.which("fc-cache"):
                subprocess.run(["fc-cache", "-fv"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            self.logger.info("Applied optimized subpixel RGB font rendering config.")
            return True, "Font rendering optimized: Subpixel RGB anti-aliasing & LCD filter enabled."
        except Exception as e:
            return False, str(e)

    # --- 4. Proprietary Driver & Hardware Detection ---

    def check_nvidia_status(self) -> Dict[str, Any]:
        """Detect NVIDIA GPU hardware and akmod-nvidia installation."""
        has_nvidia_hw = False
        try:
            res = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
            if "NVIDIA" in res.stdout:
                has_nvidia_hw = True
        except Exception:
            pass

        has_driver = shutil.which("nvidia-smi") is not None
        has_akmod = False
        try:
            res_rpm = subprocess.run(["rpm", "-q", "akmod-nvidia"], capture_output=True, text=True, timeout=3)
            has_akmod = (res_rpm.returncode == 0)
        except Exception:
            pass

        return {
            "has_hardware": has_nvidia_hw,
            "has_driver": has_driver,
            "has_akmod": has_akmod,
        }

    # --- 5. GNOME Desktop Productivity Tweaks ---

    def get_gnome_tweaks_status(self) -> Dict[str, Any]:
        """Query standard GNOME desktop productivity gsettings."""
        status = {
            "is_gnome": shutil.which("gsettings") is not None,
            "show_maximize": False,
            "show_minimize": False,
            "battery_percent": False,
            "mouse_accel": "default",
        }
        if not status["is_gnome"]:
            return status

        try:
            # Button layout
            res = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.wm.preferences", "button-layout"],
                capture_output=True, text=True, timeout=2,
            )
            val = res.stdout.strip().replace("'", "")
            status["show_maximize"] = "maximize" in val
            status["show_minimize"] = "minimize" in val

            # Battery percent
            res_b = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "show-battery-percentage"],
                capture_output=True, text=True, timeout=2,
            )
            status["battery_percent"] = (res_b.stdout.strip() == "true")

            # Mouse accel
            res_m = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.peripherals.mouse", "accel-profile"],
                capture_output=True, text=True, timeout=2,
            )
            status["mouse_accel"] = res_m.stdout.strip().replace("'", "")
        except Exception:
            pass

        return status

    def set_gnome_titlebar_buttons(self, minimize: bool = True, maximize: bool = True) -> Tuple[bool, str]:
        """Enable or disable minimize/maximize buttons on GNOME window headers."""
        if not shutil.which("gsettings"):
            return False, "gsettings not available (non-GNOME desktop)."

        buttons = ["close"]
        if minimize:
            buttons.insert(0, "minimize")
        if maximize:
            buttons.insert(0, "maximize")
        btn_str = f"appmenu:{','.join(buttons)}"

        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.wm.preferences", "button-layout", btn_str],
                check=True,
            )
            self.logger.info(f"Updated GNOME button layout to: {btn_str}")
            return True, f"Window header buttons updated: {', '.join(buttons)}"
        except Exception as e:
            return False, str(e)

    def set_gnome_battery_percent(self, show: bool = True) -> Tuple[bool, str]:
        """Toggle battery percentage in GNOME top bar."""
        if not shutil.which("gsettings"):
            return False, "gsettings not available."
        try:
            val = "true" if show else "false"
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.interface", "show-battery-percentage", val],
                check=True,
            )
            return True, f"Battery percentage display set to {show}."
        except Exception as e:
            return False, str(e)
