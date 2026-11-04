"""
Preset Export, Import, Standalone Script & ISO Provisioning Engine for ConfTune FC.
Copyright (C) BuildDesignCreate.com.
Enables portable configuration archives (.conftune.tar.gz), standalone self-deploying
shell scripts, Anaconda Kickstart snippets, and bootable ISO customization with mkksiso.
"""

import datetime
import json
import os
import shutil
import subprocess
import tarfile
from typing import Any, Dict, List, Optional, Tuple

from conftune import __version__
from conftune.core.backup_manager import BackupManager
from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine


class PresetManager:
    """Manages preset archiving, importing, standalone script generation, and ISO injection."""

    def __init__(self, safety: Optional[SafetyEngine] = None, backup_mgr: Optional[BackupManager] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.backup_mgr = backup_mgr or BackupManager()

    # --- 1. Snapshot and Export Current System as Preset Archive ---

    def capture_current_settings(self, name: str = "Custom Preset", description: str = "") -> Dict[str, Any]:
        """Inspect and capture all active tuning configurations from host."""
        sysctl_dict = {}
        if os.path.isfile("/etc/sysctl.d/99-conftune.conf"):
            try:
                with open("/etc/sysctl.d/99-conftune.conf", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            sysctl_dict[k.strip()] = v.strip()
            except Exception:
                pass

        # If 99-conftune.conf is empty or absent, capture key live sysctls
        if not sysctl_dict:
            keys_to_poll = [
                "vm.swappiness", "vm.vfs_cache_pressure", "vm.dirty_ratio", "vm.dirty_background_ratio",
                "vm.max_map_count", "net.core.somaxconn", "net.ipv4.tcp_max_syn_backlog",
                "net.ipv4.tcp_tw_reuse", "net.core.default_qdisc", "net.ipv4.tcp_congestion_control",
                "fs.file-max", "fs.inotify.max_user_watches", "fs.inotify.max_user_instances",
                "net.ipv4.ip_forward", "kernel.pid_max"
            ]
            for k in keys_to_poll:
                proc_p = "/proc/sys/" + k.replace(".", "/")
                if os.path.isfile(proc_p):
                    try:
                        with open(proc_p, "r") as f:
                            sysctl_dict[k] = f.read().strip()
                    except Exception:
                        pass

        # DNF settings
        dnf_cfg = {"max_parallel_downloads": "10", "fastestmirror": "True", "defaultyes": "True", "keepcache": "True"}
        if os.path.isfile("/etc/dnf/dnf.conf"):
            try:
                import configparser
                parser = configparser.ConfigParser()
                parser.read("/etc/dnf/dnf.conf")
                section = "main" if parser.has_section("main") else parser.sections()[0] if parser.sections() else None
                if section:
                    for opt in ["max_parallel_downloads", "fastestmirror", "defaultyes", "keepcache"]:
                        if parser.has_option(section, opt):
                            dnf_cfg[opt] = parser.get(section, opt)
            except Exception:
                pass

        # Journald Max Size
        journal_max = "300M"
        if os.path.isfile("/etc/systemd/journald.conf.d/99-conftune.conf"):
            try:
                with open("/etc/systemd/journald.conf.d/99-conftune.conf", "r") as f:
                    for line in f:
                        if line.startswith("SystemMaxUse="):
                            journal_max = line.split("=", 1)[1].strip()
            except Exception:
                pass

        # Tuned Profile
        tuned_active = "throughput-performance"
        if shutil.which("tuned-adm"):
            try:
                res = subprocess.run(["tuned-adm", "active"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0 and ":" in res.stdout:
                    tuned_active = res.stdout.strip().split(":", 1)[1].strip()
            except Exception:
                pass

        # CPU Governor & EPP
        cpu_gov = "performance"
        gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        if os.path.isfile(gov_file):
            try:
                with open(gov_file, "r") as f:
                    cpu_gov = f.read().strip()
            except Exception:
                pass

        cpu_epp = "balance_performance"
        epp_file = "/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference"
        if os.path.isfile(epp_file):
            try:
                with open(epp_file, "r") as f:
                    cpu_epp = f.read().strip()
            except Exception:
                pass

        return {
            "name": name,
            "description": description or f"Captured from host on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "created_at": datetime.datetime.now().isoformat(),
            "conftune_version": __version__,
            "sysctl": sysctl_dict,
            "dnf": dnf_cfg,
            "journald_max": journal_max,
            "tuned_profile": tuned_active,
            "cpu_governor": cpu_gov,
            "cpu_epp": cpu_epp,
            "fstrim": True,
        }

    def export_preset_archive(self, output_path: str, name: str = "Host Preset", description: str = "") -> Tuple[bool, str]:
        """Export system configuration into a portable .conftune.tar.gz archive."""
        if not output_path.endswith(".conftune.tar.gz") and not output_path.endswith(".tar.gz"):
            output_path += ".conftune.tar.gz"

        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            preset_data = self.capture_current_settings(name=name, description=description)

            tmp_dir = "/tmp/conftune_export_tmp"
            shutil.rmtree(tmp_dir, ignore_errors=True)
            os.makedirs(tmp_dir, exist_ok=True)

            manifest_path = os.path.join(tmp_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(preset_data, f, indent=2)

            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(manifest_path, arcname="manifest.json")

            shutil.rmtree(tmp_dir, ignore_errors=True)
            self.logger.info(f"Exported preset bundle to {output_path}")
            return True, f"Preset bundle exported successfully to:\n{output_path}"
        except Exception as e:
            return False, f"Failed to export preset archive: {e}"

    def import_preset_archive(self, archive_path: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Extract and validate a portable .conftune.tar.gz archive."""
        if not os.path.isfile(archive_path):
            return False, f"Archive file '{archive_path}' not found.", None

        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                manifest_member = tar.extractfile("manifest.json")
                if not manifest_member:
                    return False, "Archive does not contain a valid manifest.json file.", None
                preset_data = json.load(manifest_member)

            self.logger.info(f"Imported preset '{preset_data.get('name')}' from {archive_path}")
            return True, f"Preset '{preset_data.get('name')}' loaded successfully.", preset_data
        except Exception as e:
            return False, f"Failed to import preset: {e}", None

    def apply_preset(self, preset_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Apply an imported preset bundle to the active system with pre-tune snapshots."""
        from conftune.core.dnf_tuner import DNFTuner
        from conftune.core.power_tuner import PowerTuner
        from conftune.core.server_tuner import ServerTuner
        from conftune.core.storage_tuner import StorageTuner
        from conftune.core.sysctl_tuner import SysctlTuner
        from conftune.core.systemd_tuner import SystemdTuner

        sysctl_tuner = SysctlTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        dnf_tuner = DNFTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        systemd_tuner = SystemdTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        server_tuner = ServerTuner(safety=self.safety, backup_mgr=self.backup_mgr)
        power_tuner = PowerTuner(safety=self.safety)
        storage_tuner = StorageTuner(safety=self.safety, backup_mgr=self.backup_mgr)

        results = []

        # 1. Sysctl
        if "sysctl" in preset_data and preset_data["sysctl"]:
            ok, msg = sysctl_tuner.apply_parameters(preset_data["sysctl"], profile_name=preset_data.get("name", "Imported Preset"))
            results.append(f"Sysctl: {msg}")

        # 2. DNF
        dnf_cfg = preset_data.get("dnf", {})
        if dnf_cfg:
            ok, msg = dnf_tuner.apply_optimizations(
                max_parallel_downloads=int(dnf_cfg.get("max_parallel_downloads", 10)),
                fastestmirror=(str(dnf_cfg.get("fastestmirror", "True")).lower() == "true"),
                defaultyes=(str(dnf_cfg.get("defaultyes", "True")).lower() == "true"),
                keepcache=(str(dnf_cfg.get("keepcache", "True")).lower() == "true"),
            )
            results.append(f"DNF: {msg}")

        # 3. Journald
        if "journald_max" in preset_data:
            ok, msg = systemd_tuner.configure_journald_limit(preset_data["journald_max"])
            results.append(f"Journald: {msg}")

        # 4. Tuned Profile
        if "tuned_profile" in preset_data:
            ok, msg = server_tuner.set_tuned_profile(preset_data["tuned_profile"])
            results.append(f"Tuned: {msg}")

        # 5. CPU Governor & EPP
        if "cpu_governor" in preset_data:
            ok, msg = power_tuner.set_governor_all_cores(preset_data["cpu_governor"])
            results.append(f"Governor: {msg}")

        if "cpu_epp" in preset_data:
            ok, msg = power_tuner.set_epp_all_cores(preset_data["cpu_epp"])
            results.append(f"EPP: {msg}")

        # 6. Storage TRIM
        if preset_data.get("fstrim", False):
            ok, msg = storage_tuner.enable_fstrim_timer()
            results.append(f"TRIM: {msg}")

        summary = "\n".join(results)
        self.logger.info("Applied imported preset configurations.")
        return True, summary

    # --- 2. Generate Standalone 1-File Shell Deployment Script ---

    def generate_standalone_script(self, preset_data: Dict[str, Any], output_path: str) -> Tuple[bool, str]:
        """
        Generate a self-contained, standalone Bash deployment script.
        Zero dependencies needed on the destination server.
        """
        if not output_path.endswith(".sh"):
            output_path += ".sh"

        sysctl_lines = []
        for k, v in sorted(preset_data.get("sysctl", {}).items()):
            sysctl_lines.append(f"{k} = {v}")
        sysctl_block = "\n".join(sysctl_lines)

        dnf_cfg = preset_data.get("dnf", {})
        max_dl = dnf_cfg.get("max_parallel_downloads", 10)
        fastest = dnf_cfg.get("fastestmirror", "True")
        defaultyes = dnf_cfg.get("defaultyes", "True")
        keepcache = dnf_cfg.get("keepcache", "True")

        journal_max = preset_data.get("journald_max", "300M")
        tuned_prof = preset_data.get("tuned_profile", "throughput-performance")
        cpu_gov = preset_data.get("cpu_governor", "performance")

        script_content = f"""#!/usr/bin/env bash
# ==============================================================================
# ConfTune FC - Automated Standalone Deployment Script
# Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Preset: {preset_data.get('name', 'Custom')}
# Copyright (C) BuildDesignCreate.com
# ==============================================================================
set -e

echo "==> ConfTune FC: Applying automated system tuning..."

if [ "$EUID" -ne 0 ]; then
    echo "Error: This deployment script must be run as root (sudo)." >&2
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/lib/conftune/backups/standalone_${{TIMESTAMP}}"
mkdir -p "${{BACKUP_DIR}}"

# 1. Snapshot and write sysctl
if [ -f /etc/sysctl.d/99-conftune.conf ]; then
    cp /etc/sysctl.d/99-conftune.conf "${{BACKUP_DIR}}/"
fi
mkdir -p /etc/sysctl.d
cat << 'EOF' > /etc/sysctl.d/99-conftune.conf
# ConfTune FC - Automated System Tuning
{sysctl_block}
EOF
if command -v sysctl >/dev/null 2>&1; then
    sysctl -p /etc/sysctl.d/99-conftune.conf >/dev/null 2>&1 || true
fi
echo "  ✓ Sysctl parameters applied (/etc/sysctl.d/99-conftune.conf)"

# 2. Snapshot and configure DNF
if [ -f /etc/dnf/dnf.conf ]; then
    cp /etc/dnf/dnf.conf "${{BACKUP_DIR}}/"
    # Update or append DNF parameters
    grep -q "^max_parallel_downloads=" /etc/dnf/dnf.conf && sed -i "s/^max_parallel_downloads=.*/max_parallel_downloads={max_dl}/" /etc/dnf/dnf.conf || echo "max_parallel_downloads={max_dl}" >> /etc/dnf/dnf.conf
    grep -q "^fastestmirror=" /etc/dnf/dnf.conf && sed -i "s/^fastestmirror=.*/fastestmirror={fastest}/" /etc/dnf/dnf.conf || echo "fastestmirror={fastest}" >> /etc/dnf/dnf.conf
    grep -q "^defaultyes=" /etc/dnf/dnf.conf && sed -i "s/^defaultyes=.*/defaultyes={defaultyes}/" /etc/dnf/dnf.conf || echo "defaultyes={defaultyes}" >> /etc/dnf/dnf.conf
    grep -q "^keepcache=" /etc/dnf/dnf.conf && sed -i "s/^keepcache=.*/keepcache={keepcache}/" /etc/dnf/dnf.conf || echo "keepcache={keepcache}" >> /etc/dnf/dnf.conf
    echo "  ✓ DNF multi-threaded acceleration configured"
fi

# 3. Systemd Journal Size Cap
mkdir -p /etc/systemd/journald.conf.d
cat << 'EOF' > /etc/systemd/journald.conf.d/99-conftune.conf
[Journal]
SystemMaxUse={journal_max}
RuntimeMaxUse=100M
EOF
systemctl restart systemd-journald 2>/dev/null || true
echo "  ✓ Systemd journal size cap applied ({journal_max})"

# 4. Red Hat Tuned Profile
if command -v tuned-adm >/dev/null 2>&1; then
    tuned-adm profile {tuned_prof} 2>/dev/null || true
    echo "  ✓ Tuned profile set to: {tuned_prof}"
fi

# 5. CPU Governor
if [ -d /sys/devices/system/cpu/cpu0/cpufreq ]; then
    for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        [ -f "$gov" ] && echo "{cpu_gov}" > "$gov" 2>/dev/null || true
    done
    echo "  ✓ CPU scaling governor set to: {cpu_gov}"
fi

# 6. SSD/NVMe TRIM Timer
systemctl enable --now fstrim.timer 2>/dev/null || true
echo "  ✓ Weekly SSD/NVMe fstrim.timer enabled"

echo ""
echo "==> ConfTune FC Deployment Complete! Original files backed up to ${{BACKUP_DIR}}"
"""

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            os.chmod(output_path, 0o755)
            self.logger.info(f"Generated standalone deploy script: {output_path}")
            return True, f"Standalone deployment script generated:\n{output_path}\n\nYou can scp and execute this file directly on any fresh server!"
        except Exception as e:
            return False, f"Failed to generate standalone script: {e}"

    # --- 3. Generate Anaconda Kickstart Snippet ---

    def generate_kickstart(self, preset_data: Dict[str, Any], output_path: str) -> Tuple[bool, str]:
        """
        Generate a Red Hat / Fedora Kickstart (.ks) file for automated OS installation.
        """
        if not output_path.endswith(".ks"):
            output_path += ".ks"

        sysctl_lines = []
        for k, v in sorted(preset_data.get("sysctl", {}).items()):
            sysctl_lines.append(f"{k} = {v}")
        sysctl_block = "\n".join(sysctl_lines)

        dnf_cfg = preset_data.get("dnf", {})
        max_dl = dnf_cfg.get("max_parallel_downloads", 10)
        journal_max = preset_data.get("journald_max", "300M")
        tuned_prof = preset_data.get("tuned_profile", "throughput-performance")

        ks_content = f"""# ==============================================================================
# ConfTune FC - Automated Anaconda Kickstart Post-Install Configuration
# Compatible with Fedora 40-45+, Rocky Linux 8-10, and CentOS Stream 9-10
# Copyright (C) BuildDesignCreate.com
# ==============================================================================

%post --log=/var/log/conftune-postinstall.log
echo "==> ConfTune FC: Applying automated post-install optimizations..."

# 1. Kernel Sysctl Configuration
mkdir -p /etc/sysctl.d
cat << 'EOF' > /etc/sysctl.d/99-conftune.conf
# ConfTune FC - Automated Kickstart Settings
{sysctl_block}
EOF

# 2. DNF Package Manager Accelerator
mkdir -p /etc/dnf
cat << 'EOF' >> /etc/dnf/dnf.conf
max_parallel_downloads={max_dl}
fastestmirror=True
defaultyes=True
keepcache=True
clean_requirements_on_remove=True
EOF

# 3. Systemd Journal Storage Cap
mkdir -p /etc/systemd/journald.conf.d
cat << 'EOF' > /etc/systemd/journald.conf.d/99-conftune.conf
[Journal]
SystemMaxUse={journal_max}
RuntimeMaxUse=100M
EOF

# 4. Enable Weekly SSD/NVMe TRIM
systemctl enable fstrim.timer 2>/dev/null || true

# 5. Set Tuned Profile
if command -v tuned-adm >/dev/null 2>&1; then
    tuned-adm profile {tuned_prof} 2>/dev/null || true
fi

echo "==> ConfTune FC: Kickstart post-install configuration finished successfully."
%end
"""

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(ks_content)
            self.logger.info(f"Generated Kickstart configuration: {output_path}")
            return True, f"Anaconda Kickstart configuration generated:\n{output_path}"
        except Exception as e:
            return False, f"Failed to generate Kickstart: {e}"

    # --- 4. Inject Kickstart into Bootable ISO with mkksiso ---

    def build_custom_iso(self, base_iso_path: str, kickstart_path: str, output_iso_path: str) -> Tuple[bool, str]:
        """
        Inject a Kickstart file into an official Fedora / Rocky / CentOS ISO using mkksiso.
        """
        if not os.path.isfile(base_iso_path):
            return False, f"Base ISO image '{base_iso_path}' not found."
        if not os.path.isfile(kickstart_path):
            return False, f"Kickstart file '{kickstart_path}' not found."

        mkksiso_bin = shutil.which("mkksiso")
        if not mkksiso_bin:
            return False, (
                "The 'mkksiso' utility is required to inject Kickstarts into ISO images.\n"
                "Please install it using:\n\n"
                "    sudo dnf install lorax\n"
            )

        cmd = [mkksiso_bin, "--ks", kickstart_path, base_iso_path, output_iso_path]

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would execute: {' '.join(cmd)}"

        try:
            self.logger.info(f"Executing mkksiso: {' '.join(cmd)}")
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if res.returncode == 0:
                self.logger.info(f"Successfully generated automated ISO: {output_iso_path}")
                return True, f"Automated bootable ISO generated successfully!\n\nOutput: {output_iso_path}\n\nYou can now flash this ISO directly to a USB drive with Fedora Media Writer, Rufus, or dd."
            return False, f"mkksiso failed: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Error building custom ISO: {e}"
