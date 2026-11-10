"""
Kernel Sysctl Engine for ConfTune FC.
Reads active sysctl values, maintains a catalog of tunable parameters with safety bounds,
and writes optimized /etc/sysctl.d/99-conftune.conf files with live application.
"""

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from conftune.core.backup_manager import BackupManager
from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine

SYSCTL_CONF_PATH = "/etc/sysctl.d/99-conftune.conf"

PARAMETER_CATALOG: Dict[str, Dict[str, str]] = {
    "vm.swappiness": {
        "category": "Memory & VM",
        "description": "Tendency of the kernel to swap memory pages to disk (0-100). Lower values favor physical RAM.",
        "default": "60",
        "impact": "High",
    },
    "vm.vfs_cache_pressure": {
        "category": "Memory & VM",
        "description": "Kernel reclaim rate of directory and inode cache entries. Lower values (50) preserve cached file metadata.",
        "default": "100",
        "impact": "Medium",
    },
    "vm.dirty_background_ratio": {
        "category": "Memory & VM",
        "description": "Percentage of system memory at which background writeback flusher threads start flushing dirty data.",
        "default": "10",
        "impact": "Medium",
    },
    "vm.dirty_ratio": {
        "category": "Memory & VM",
        "description": "Percentage of total memory where process generating disk writes will block until writes are flushed.",
        "default": "20",
        "impact": "High",
    },
    "vm.max_map_count": {
        "category": "Memory & VM",
        "description": "Maximum number of memory map areas a process may have. Essential for Proton, Wine, and large Elasticsearch/DBs.",
        "default": "65530",
        "impact": "High",
    },
    "net.core.somaxconn": {
        "category": "Network & TCP",
        "description": "Maximum socket listen backlog for accepting incoming network connections (Nginx, HTTP, Microservices).",
        "default": "4096",
        "impact": "High",
    },
    "net.core.netdev_max_backlog": {
        "category": "Network & TCP",
        "description": "Maximum number of packets queued on the input side when the network card receives packets faster than the kernel processes them.",
        "default": "1000",
        "impact": "Medium",
    },
    "net.ipv4.tcp_max_syn_backlog": {
        "category": "Network & TCP",
        "description": "Maximum queued SYN requests before dropping new connection attempts (SYN flood defense & burst tolerance).",
        "default": "1024",
        "impact": "High",
    },
    "net.ipv4.tcp_tw_reuse": {
        "category": "Network & TCP",
        "description": "Allows recycling of TIME_WAIT sockets for outgoing connections when safe from a protocol viewpoint.",
        "default": "2",
        "impact": "Medium",
    },
    "net.ipv4.tcp_fin_timeout": {
        "category": "Network & TCP",
        "description": "Seconds to wait for a final FIN packet before closing a socket. Lower values clean up idle sockets quicker.",
        "default": "60",
        "impact": "Medium",
    },
    "net.core.default_qdisc": {
        "category": "Network & TCP",
        "description": "Default queuing discipline. 'fq' (Fair Queueing) is required for BBR congestion control.",
        "default": "fq_codel",
        "impact": "High",
    },
    "net.ipv4.tcp_congestion_control": {
        "category": "Network & TCP",
        "description": "TCP Congestion Control algorithm. 'bbr' improves bandwidth and drops latency on lossy connections.",
        "default": "cubic",
        "impact": "High",
    },
    "net.ipv4.tcp_keepalive_time": {
        "category": "Network & TCP",
        "description": "Interval (seconds) between the last data packet sent and the first keepalive probe on an idle connection.",
        "default": "7200",
        "impact": "Low",
    },
    "fs.file-max": {
        "category": "File System",
        "description": "System-wide limit on the total number of open file descriptors across all processes.",
        "default": "524288",
        "impact": "High",
    },
    "fs.inotify.max_user_watches": {
        "category": "File System",
        "description": "Maximum number of filesystem directories/files that can be watched by inotify (vital for IDEs & containers).",
        "default": "8192",
        "impact": "High",
    },
    "fs.inotify.max_user_instances": {
        "category": "File System",
        "description": "Maximum number of inotify instances a user ID can spawn.",
        "default": "128",
        "impact": "Medium",
    },
    "net.ipv4.ip_forward": {
        "category": "Containers & Cloud",
        "description": "IPv4 packet forwarding. Required for Docker, Podman bridge networks, and KVM guest routing.",
        "default": "0",
        "impact": "High",
    },
    "kernel.pid_max": {
        "category": "Kernel & System",
        "description": "System-wide ceiling for maximum process identifiers (prevents fork failures in dense container nodes).",
        "default": "4194304",
        "impact": "Medium",
    },
    "kernel.split_lock_mitigate": {
        "category": "Kernel & System",
        "description": "Disables CPU penalty on misaligned atomic accesses, improving gaming & emulated title performance.",
        "default": "1",
        "impact": "Medium",
    },
}


class SysctlTuner:
    """Manages kernel sysctl parameters, file generation, and system updates."""

    def __init__(self, safety: Optional[SafetyEngine] = None, backup_mgr: Optional[BackupManager] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.backup_mgr = backup_mgr or BackupManager()

    def get_live_value(self, key: str) -> str:
        """Fetch the current runtime value of a sysctl key."""
        # Check /proc/sys/<path>
        proc_path = "/proc/sys/" + key.replace(".", "/")
        try:
            if os.path.isfile(proc_path):
                with open(proc_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass

        # Fallback to sysctl command
        try:
            res = subprocess.run(
                ["sysctl", "-n", key],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return "N/A"

    def get_all_live_status(self) -> List[Dict[str, Any]]:
        """Return full table of all tunable parameters with live values and metadata."""
        items = []
        for key, meta in PARAMETER_CATALOG.items():
            live_val = self.get_live_value(key)
            items.append({
                "key": key,
                "category": meta["category"],
                "description": meta["description"],
                "default": meta["default"],
                "impact": meta["impact"],
                "current": live_val,
            })
        return items

    def apply_parameters(
        self,
        parameters: Dict[str, str],
        profile_name: str = "custom",
    ) -> Tuple[bool, str]:
        """
        Write /etc/sysctl.d/99-conftune.conf and apply parameters immediately.
        Performs pre-tune snapshot and privilege check.
        """
        valid, msg = self.safety.verify_privilege("Applying sysctl parameters")
        if not valid:
            self.logger.error(msg)
            return False, msg

        # Snapshot before modifying
        self.backup_mgr.create_snapshot(
            profile_name=profile_name,
            target_paths=[SYSCTL_CONF_PATH],
            notes=f"Sysctl profile apply: {profile_name}",
            dry_run=self.safety.dry_run,
        )

        # Generate config file content
        content = [
            "# ConfTune FC - Kernel Performance Configuration",
            f"# Profile: {profile_name}",
            "# Generated automatically by ConfTune FC. Do not edit manually.",
            "",
        ]

        # Group by category
        grouped: Dict[str, List[Tuple[str, str]]] = {}
        for key, val in parameters.items():
            if not self.safety.sanitize_sysctl_value(key, str(val)):
                self.logger.warning(f"Skipping potentially unsafe sysctl key/val: {key} = {val}")
                continue
            cat = PARAMETER_CATALOG.get(key, {}).get("category", "General Tuning")
            grouped.setdefault(cat, []).append((key, str(val)))

        for cat, pairs in sorted(grouped.items()):
            content.append(f"# --- {cat} ---")
            for key, val in sorted(pairs):
                content.append(f"{key} = {val}")
            content.append("")

        full_text = "\n".join(content)

        if self.safety.dry_run:
            self.logger.info(f"[DRY RUN] Would write {SYSCTL_CONF_PATH} with:\n{full_text}")
            return True, f"[DRY RUN] Generated {len(parameters)} parameters for {SYSCTL_CONF_PATH}."

        try:
            ok_w, msg_w = self.safety.write_file(SYSCTL_CONF_PATH, full_text)
            if not ok_w:
                return False, f"Failed to write sysctl configuration: {msg_w}"

            # Apply sysctl settings
            sysctl_cmd = shutil.which("sysctl")
            if sysctl_cmd:
                res = self.safety.run_command(
                    [sysctl_cmd, "-p", SYSCTL_CONF_PATH],
                    timeout=5,
                )
                if res.returncode != 0:
                    self.logger.warning(f"sysctl -p returned warnings: {res.stderr.strip()}")

            self.logger.info(f"Successfully applied {len(parameters)} sysctl settings from profile '{profile_name}'.")
            return True, f"Successfully applied {len(parameters)} sysctl settings."

        except Exception as e:
            err = f"Failed to write or apply sysctl configuration: {e}"
            self.logger.error(err)
            return False, err

    def has_custom_overrides(self) -> bool:
        """Check if custom sysctl override file exists in /etc/sysctl.d/99-conftune.conf."""
        return os.path.isfile(SYSCTL_CONF_PATH)

    def restore_system_defaults(self) -> Tuple[bool, str]:
        """
        Remove /etc/sysctl.d/99-conftune.conf and reload kernel sysctl hierarchy
        from system defaults (/usr/lib/sysctl.d/, /etc/sysctl.conf).
        """
        valid, msg = self.safety.verify_privilege("Restoring default sysctl configuration")
        if not valid:
            return False, msg

        if os.path.isfile(SYSCTL_CONF_PATH):
            self.backup_mgr.create_snapshot(
                profile_name="sysctl_pre_restore",
                target_paths=[SYSCTL_CONF_PATH],
                notes="Backup before restoring default sysctl",
                dry_run=self.safety.dry_run,
            )

        ok_rm, msg_rm = self.safety.remove_file(SYSCTL_CONF_PATH)
        if not ok_rm:
            return False, f"Failed to remove {SYSCTL_CONF_PATH}: {msg_rm}"

        # Reload sysctl defaults across all directories
        sysctl_cmd = shutil.which("sysctl")
        if sysctl_cmd:
            self.safety.run_command([sysctl_cmd, "--system"], timeout=10)

        self.logger.info("Restored kernel sysctl to system defaults.")
        return True, "Removed /etc/sysctl.d/99-conftune.conf and reloaded system defaults (sysctl --system)."
