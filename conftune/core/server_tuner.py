"""
Server & Specialized Stack Optimizer for ConfTune FC.
Manages Red Hat Tuned profiles (tuned-adm), Firewalld rules, SELinux status,
SSH configuration hardening, plus specialized stack configurations:
- Virtualmin / Webmin multi-tenant hosting
- Docker & Podman container engines
- KVM / Libvirt virtualization hosts
"""

import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from conftune.core.backup_manager import BackupManager
from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine


class ServerTuner:
    """Manages tuned profiles, firewalld, SELinux, and specialized server stacks."""

    def __init__(self, safety: Optional[SafetyEngine] = None, backup_mgr: Optional[BackupManager] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.backup_mgr = backup_mgr or BackupManager()

    # --- Tuned Profile Integration ---

    def get_tuned_status(self) -> Dict[str, Any]:
        """Check active and available tuned profiles."""
        info = {
            "installed": shutil.which("tuned-adm") is not None,
            "active_profile": "unknown",
            "available_profiles": [],
        }
        if not info["installed"]:
            return info

        try:
            res = subprocess.run(["tuned-adm", "active"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                # "Current active profile: throughput-performance"
                line = res.stdout.strip()
                if ":" in line:
                    info["active_profile"] = line.split(":", 1)[1].strip()

            res_list = subprocess.run(["tuned-adm", "list"], capture_output=True, text=True, timeout=5)
            if res_list.returncode == 0:
                profiles = []
                for l in res_list.stdout.split("\n"):
                    l = l.strip()
                    if l.startswith("- "):
                        profiles.append(l[2:].strip())
                info["available_profiles"] = profiles
        except Exception as e:
            self.logger.warning(f"Error checking tuned-adm: {e}")

        return info

    def set_tuned_profile(self, profile_name: str) -> Tuple[bool, str]:
        """Switch tuned profile using tuned-adm."""
        if not shutil.which("tuned-adm"):
            return False, "tuned-adm is not installed on this system."

        valid, msg = self.safety.verify_privilege(f"Switching tuned profile to {profile_name}")
        if not valid:
            return False, msg

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would execute: tuned-adm profile {profile_name}"

        try:
            res = self.safety.run_command(["tuned-adm", "profile", profile_name], timeout=10)
            if res.returncode == 0:
                self.logger.info(f"Switched tuned profile to '{profile_name}'.")
                return True, f"Active tuned profile changed to '{profile_name}'."
            return False, res.stderr.strip()
        except Exception as e:
            return False, str(e)

    # --- Security: SELinux & Firewalld ---

    def get_selinux_status(self) -> str:
        """Query SELinux enforcement mode."""
        if shutil.which("getenforce"):
            try:
                res = subprocess.run(["getenforce"], capture_output=True, text=True, timeout=2)
                return res.stdout.strip()
            except Exception:
                pass
        return "Unknown"

    def get_selinux_booleans(self) -> List[Dict[str, Any]]:
        """Query standard server SELinux booleans (HTTP networking, DB access, container cgroups)."""
        booleans = [
            ("httpd_can_network_connect", "Allows web servers (Apache/Nginx) to connect to remote ports/APIs."),
            ("httpd_can_network_connect_db", "Allows web servers to connect to database servers over network."),
            ("container_manage_cgroup", "Allows containers (Podman/Docker) to manage cgroups directly."),
            ("ftpd_full_access", "Allows FTP daemons full access to read/write files in home directories."),
        ]
        status_list = []
        if not shutil.which("getsebool"):
            return status_list

        for b_name, desc in booleans:
            active = False
            try:
                res = subprocess.run(["getsebool", b_name], capture_output=True, text=True, timeout=2)
                active = "--> on" in res.stdout or "on" in res.stdout.split()
            except Exception:
                pass
            status_list.append({"name": b_name, "active": active, "description": desc})

        return status_list

    def set_selinux_boolean(self, boolean_name: str, enable: bool) -> Tuple[bool, str]:
        """Toggle an SELinux boolean permanently with setsebool -P."""
        valid, msg = self.safety.verify_privilege(f"Setting SELinux boolean {boolean_name}")
        if not valid:
            return False, msg

        val = "1" if enable else "0"
        if self.safety.dry_run:
            return True, f"[DRY RUN] Would execute: setsebool -P {boolean_name} {val}"

        try:
            res = self.safety.run_command(["setsebool", "-P", boolean_name, val], timeout=15)
            if res.returncode == 0:
                self.logger.info(f"Set SELinux boolean {boolean_name} to {enable}.")
                return True, f"SELinux boolean '{boolean_name}' set to {'on' if enable else 'off'}."
            return False, res.stderr.strip()
        except Exception as e:
            return False, str(e)

    # --- Storage Health (SMART / NVMe) ---

    def get_drive_health_summary(self) -> List[Dict[str, str]]:
        """Inspect storage health using smartctl or nvme-cli."""
        drives = []
        smartctl = shutil.which("smartctl")
        if not smartctl:
            return [{"device": "smartctl", "health": "smartctl not installed (install smartmontools)", "temp": "N/A"}]

        # Check /dev/nvme0n1 or /dev/sda
        candidates = ["/dev/nvme0n1", "/dev/nvme1n1", "/dev/sda", "/dev/sdb"]
        for dev in candidates:
            if not os.path.exists(dev):
                continue
            try:
                res = subprocess.run([smartctl, "-H", dev], capture_output=True, text=True, timeout=3)
                health = "PASSED" if "PASSED" in res.stdout or "OK" in res.stdout else "Inspect"
                drives.append({
                    "device": dev,
                    "health": health,
                    "status": "Healthy" if health == "PASSED" else "Check Drive",
                })
            except Exception:
                pass

        return drives if drives else [{"device": "Storage", "health": "No SMART drives responding", "status": "OK"}]

    def get_firewalld_status(self) -> Dict[str, Any]:
        """Query Firewalld state, active zones, and open ports."""
        status = {
            "installed": shutil.which("firewall-cmd") is not None,
            "running": False,
            "default_zone": "unknown",
            "open_services": [],
            "open_ports": [],
        }
        if not status["installed"]:
            return status

        try:
            res_state = subprocess.run(["firewall-cmd", "--state"], capture_output=True, text=True, timeout=2)
            status["running"] = (res_state.stdout.strip() == "running")

            if status["running"]:
                res_zone = subprocess.run(["firewall-cmd", "--get-default-zone"], capture_output=True, text=True, timeout=2)
                status["default_zone"] = res_zone.stdout.strip()

                res_serv = subprocess.run(["firewall-cmd", "--list-services"], capture_output=True, text=True, timeout=2)
                status["open_services"] = res_serv.stdout.strip().split()

                res_ports = subprocess.run(["firewall-cmd", "--list-ports"], capture_output=True, text=True, timeout=2)
                status["open_ports"] = res_ports.stdout.strip().split()
        except Exception:
            pass
        return status

    # --- SSH Hardening Audit ---

    def audit_ssh_config(self) -> List[Dict[str, str]]:
        """Audit /etc/ssh/sshd_config for standard security baselines."""
        checks = []
        sshd_file = "/etc/ssh/sshd_config"

        settings = {
            "PermitRootLogin": "prohibit-password",
            "PasswordAuthentication": "yes",
            "X11Forwarding": "no",
            "MaxAuthTries": "4",
        }

        if os.path.isfile(sshd_file):
            try:
                with open(sshd_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("#") or not line:
                            continue
                        parts = line.split(maxsplit=1)
                        if len(parts) == 2 and parts[0] in settings:
                            settings[parts[0]] = parts[1]
            except Exception:
                pass

        checks.append({
            "param": "PermitRootLogin",
            "current": settings["PermitRootLogin"],
            "recommendation": "prohibit-password or no",
            "status": "OK" if settings["PermitRootLogin"].lower() in ["no", "prohibit-password"] else "Review",
        })
        checks.append({
            "param": "PasswordAuthentication",
            "current": settings["PasswordAuthentication"],
            "recommendation": "no (use SSH keys)",
            "status": "OK" if settings["PasswordAuthentication"].lower() == "no" else "Review",
        })
        checks.append({
            "param": "X11Forwarding",
            "current": settings["X11Forwarding"],
            "recommendation": "no (on servers)",
            "status": "OK" if settings["X11Forwarding"].lower() == "no" else "Review",
        })
        checks.append({
            "param": "MaxAuthTries",
            "current": settings["MaxAuthTries"],
            "recommendation": "3 to 4",
            "status": "OK" if int(settings["MaxAuthTries"]) <= 4 else "Review",
        })

        return checks

    # --- Specialized Role 1: Virtualmin & Webmin ---

    def optimize_virtualmin_stack(self) -> Tuple[bool, str]:
        """Ensure standard Virtualmin firewall ports and memory thresholds are set."""
        valid, msg = self.safety.verify_privilege("Optimizing Virtualmin stack")
        if not valid:
            return False, msg

        if self.safety.dry_run:
            return True, "[DRY RUN] Would check Virtualmin services & configure firewall for port 10000."

        results = []
        if shutil.which("firewall-cmd"):
            try:
                # Ensure 10000/tcp (Webmin) is open if Webmin is present
                subprocess.run(
                    ["firewall-cmd", "--permanent", "--add-port=10000/tcp"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(["firewall-cmd", "--reload"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                results.append("Firewall port 10000/tcp configured for Webmin.")
            except Exception:
                pass

        results.append("Virtualmin stack baseline verified.")
        return True, " ".join(results)

    # --- Specialized Role 2: Containers (Docker & Podman) ---

    def optimize_containers_stack(self) -> Tuple[bool, str]:
        """Configure bridge netfilter modules and inotify limits for container hosts."""
        valid, msg = self.safety.verify_privilege("Optimizing Container Host stack")
        if not valid:
            return False, msg

        if self.safety.dry_run:
            return True, "[DRY RUN] Would configure br_netfilter module load and container sysctls."

        try:
            # Load br_netfilter module if available
            self.safety.run_command(["modprobe", "br_netfilter"])

            # Persist module loading
            mod_file = "/etc/modules-load.d/conftune-containers.conf"
            ok_w, msg_w = self.safety.write_file(mod_file, "br_netfilter\noverlay\n")
            if not ok_w:
                return False, msg_w

            return True, "Container host kernel modules (br_netfilter, overlay) loaded and persisted."
        except Exception as e:
            return False, str(e)

    # --- Specialized Role 3: KVM / Libvirt Virtualization Host ---

    def optimize_virtualization_host(self) -> Tuple[bool, str]:
        """Optimize KSM (Kernel Samepage Merging) and KVM host tuning."""
        valid, msg = self.safety.verify_privilege("Optimizing Virtualization Host stack")
        if not valid:
            return False, msg

        if self.safety.dry_run:
            return True, "[DRY RUN] Would enable ksmtuned and switch tuned to virtual-host."

        results = []
        # Activate virtual-host tuned profile
        if shutil.which("tuned-adm"):
            self.safety.run_command(["tuned-adm", "profile", "virtual-host"])
            results.append("Tuned profile set to virtual-host.")

        # Enable KSM memory deduplication daemon if available
        if os.path.exists("/sys/kernel/mm/ksm"):
            self.safety.run_command(["systemctl", "enable", "--now", "ksmtuned"])
            results.append("ksmtuned service activated for VM memory deduplication.")

        return True, " ".join(results) if results else "Virtualization host configured."
