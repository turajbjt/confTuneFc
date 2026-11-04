"""
System and Environment Detector for ConfTune FC.
Profiles distribution, desktop vs server roles, hardware specs,
and specialized stacks (Webmin/Virtualmin, Containers, Virtualization).
"""

import json
import os
import platform
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional


class SystemDetector:
    """Discovers distribution details, hardware configuration, and installed server/desktop stacks."""

    def __init__(self, refresh_on_init: bool = True):
        self.os_info: Dict[str, str] = {}
        self.hardware_info: Dict[str, Any] = {}
        self.role_info: Dict[str, Any] = {}
        self.specialized_stacks: Dict[str, Any] = {}
        if refresh_on_init:
            self.refresh()

    def refresh(self) -> None:
        """Scan system and cache all detection data."""
        self.os_info = self._detect_os()
        self.hardware_info = self._detect_hardware()
        self.role_info = self._detect_roles()
        self.specialized_stacks = self._detect_specialized()

    def _detect_os(self) -> Dict[str, str]:
        """Parse /etc/os-release and platform metadata."""
        info = {
            "id": "unknown",
            "version_id": "",
            "name": platform.system(),
            "pretty_name": "Linux",
            "kernel": platform.release(),
            "arch": platform.machine(),
            "is_rpm": False,
            "is_fedora": False,
            "is_rocky": False,
            "is_centos": False,
            "is_rhel_family": False,
            "dnf_version": "unknown",
        }

        if os.path.isfile("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            v = v.strip('"\'')
                            if k == "ID":
                                info["id"] = v.lower()
                            elif k == "VERSION_ID":
                                info["version_id"] = v
                            elif k == "NAME":
                                info["name"] = v
                            elif k == "PRETTY_NAME":
                                info["pretty_name"] = v
            except Exception:
                pass

        # Identify RPM family
        distro_id = info["id"]
        if distro_id in ["fedora"]:
            info["is_fedora"] = True
            info["is_rpm"] = True
        elif distro_id in ["rocky"]:
            info["is_rocky"] = True
            info["is_rhel_family"] = True
            info["is_rpm"] = True
        elif distro_id in ["centos"]:
            info["is_centos"] = True
            info["is_rhel_family"] = True
            info["is_rpm"] = True
        elif distro_id in ["rhel", "almalinux", "ol"]:
            info["is_rhel_family"] = True
            info["is_rpm"] = True

        # Check DNF version (DNF5 vs DNF4)
        if shutil.which("dnf5"):
            info["dnf_version"] = "dnf5"
        elif shutil.which("dnf"):
            info["dnf_version"] = "dnf4"

        return info

    def _detect_hardware(self) -> Dict[str, Any]:
        """Detect CPU, RAM, Swap, Disks, and Network."""
        hw = {
            "cpu_model": "Unknown CPU",
            "cpu_cores": os.cpu_count() or 1,
            "cpu_governor": "unknown",
            "ram_total_gb": 0.0,
            "ram_avail_gb": 0.0,
            "swap_total_gb": 0.0,
            "has_zram": False,
            "zram_size_gb": 0.0,
            "disks": [],
            "has_nvme": False,
            "has_ssd": False,
            "root_fs": "unknown",
            "virtualization": "none",
        }

        # CPU Model & Governor
        try:
            if os.path.isfile("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if "model name" in line:
                            hw["cpu_model"] = line.split(":", 1)[1].strip()
                            break
            gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
            if os.path.isfile(gov_file):
                with open(gov_file, "r") as f:
                    hw["cpu_governor"] = f.read().strip()
        except Exception:
            pass

        # RAM & Swap via /proc/meminfo
        try:
            if os.path.isfile("/proc/meminfo"):
                mem = {}
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            val = parts[1].strip().split()[0]
                            mem[parts[0].strip()] = int(val)
                total_kb = mem.get("MemTotal", 0)
                avail_kb = mem.get("MemAvailable", 0)
                swap_kb = mem.get("SwapTotal", 0)
                hw["ram_total_gb"] = round(total_kb / (1024 * 1024), 2)
                hw["ram_avail_gb"] = round(avail_kb / (1024 * 1024), 2)
                hw["swap_total_gb"] = round(swap_kb / (1024 * 1024), 2)
        except Exception:
            pass

        # ZRAM detection via /proc/swaps or zramctl
        try:
            if os.path.isfile("/proc/swaps"):
                with open("/proc/swaps", "r") as f:
                    for line in f:
                        if "/dev/zram" in line:
                            hw["has_zram"] = True
                            parts = line.split()
                            if len(parts) >= 3 and parts[2].isdigit():
                                hw["zram_size_gb"] += round(int(parts[2]) / (1024 * 1024), 2)
        except Exception:
            pass

        # Disks & Root Filesystem
        try:
            res = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,TYPE,SIZE,ROTA,MODEL,FSTYPE,MOUNTPOINT"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                data = json.loads(res.stdout)
                devices = data.get("blockdevices", [])
                hw["disks"] = devices

                def scan_devs(dev_list):
                    for dev in dev_list:
                        name = dev.get("name", "")
                        rota = str(dev.get("rota", "1"))
                        mp = dev.get("mountpoint", "")
                        fstype = dev.get("fstype", "")
                        if mp == "/":
                            hw["root_fs"] = fstype or "unknown"
                        if "nvme" in name:
                            hw["has_nvme"] = True
                        elif rota == "0":
                            hw["has_ssd"] = True
                        if "children" in dev:
                            scan_devs(dev["children"])

                scan_devs(devices)
        except Exception:
            pass

        # Virtualization detection (KVM, VMware, etc.)
        try:
            virt_cmd = shutil.which("systemd-detect-virt")
            if virt_cmd:
                res = subprocess.run([virt_cmd], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    hw["virtualization"] = res.stdout.strip()
        except Exception:
            pass

        return hw

    def _detect_roles(self) -> Dict[str, Any]:
        """Check whether system is a Desktop workstation or Headless Server."""
        role = {
            "is_desktop": False,
            "desktop_env": "none",
            "display_server": "none",
            "is_server": True,
        }

        # Check Display environment variables or running desktop components
        wayland = os.environ.get("WAYLAND_DISPLAY")
        x11 = os.environ.get("DISPLAY")
        desktop_session = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION")

        if desktop_session:
            role["is_desktop"] = True
            role["desktop_env"] = desktop_session.lower()
            role["is_server"] = False
        elif wayland or x11:
            role["is_desktop"] = True
            role["is_server"] = False

        if wayland:
            role["display_server"] = "wayland"
        elif x11:
            role["display_server"] = "x11"

        # Check for GNOME / KDE package existence if headless session
        if not role["is_desktop"]:
            if shutil.which("gnome-shell"):
                role["desktop_env"] = "gnome (installed)"
            elif shutil.which("kwin_wayland") or shutil.which("kwin_x11"):
                role["desktop_env"] = "kde (installed)"

        return role

    def _detect_specialized(self) -> Dict[str, Any]:
        """Detect presence and status of Webmin/Virtualmin, Containers (Docker/Podman), and KVM Virtualization."""
        stacks = {
            "virtualmin": {
                "detected": False,
                "has_webmin": False,
                "services": {},
            },
            "containers": {
                "has_podman": False,
                "has_docker": False,
                "ip_forwarding": False,
                "has_subuid": False,
            },
            "virtualization_host": {
                "is_kvm_host": False,
                "has_libvirt": False,
                "has_ksm": False,
            },
        }

        # 1. Virtualmin / Webmin
        webmin_installed = os.path.isdir("/etc/webmin") or os.path.isfile("/usr/libexec/webmin/miniserv.pl")
        virtualmin_installed = os.path.isdir("/etc/webmin/virtual-server") or os.path.isfile("/usr/sbin/virtualmin")

        stacks["virtualmin"]["has_webmin"] = webmin_installed
        stacks["virtualmin"]["detected"] = virtualmin_installed or webmin_installed

        services_to_check = ["webmin", "httpd", "nginx", "mariadb", "named", "postfix", "dovecot", "php-fpm"]
        for s in services_to_check:
            stacks["virtualmin"]["services"][s] = self._is_service_active(s)

        # 2. Containers (Podman & Docker)
        stacks["containers"]["has_podman"] = shutil.which("podman") is not None
        stacks["containers"]["has_docker"] = shutil.which("docker") is not None
        stacks["containers"]["has_subuid"] = os.path.isfile("/etc/subuid") and os.path.getsize("/etc/subuid") > 0

        # Check ip_forwarding
        try:
            if os.path.isfile("/proc/sys/net/ipv4/ip_forward"):
                with open("/proc/sys/net/ipv4/ip_forward", "r") as f:
                    stacks["containers"]["ip_forwarding"] = (f.read().strip() == "1")
        except Exception:
            pass

        # 3. KVM / Libvirt Virtualization Host
        stacks["virtualization_host"]["is_kvm_host"] = os.path.exists("/dev/kvm")
        stacks["virtualization_host"]["has_libvirt"] = (
            shutil.which("virsh") is not None or self._is_service_active("libvirtd") or self._is_service_active("virtqemud")
        )
        stacks["virtualization_host"]["has_ksm"] = os.path.isdir("/sys/kernel/mm/ksm")

        return stacks

    def _is_service_active(self, service_name: str) -> bool:
        """Check if a systemd unit is active."""
        try:
            res = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return res.stdout.strip() == "active"
        except Exception:
            return False
