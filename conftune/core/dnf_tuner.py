"""
DNF Package Manager Accelerator for ConfTune FC.
Optimizes /etc/dnf/dnf.conf for maximum download concurrency, fastest mirrors,
and reliable package caching across Fedora (DNF5/DNF4), Rocky Linux, and CentOS Stream.
"""

import configparser
import os
import shutil
import subprocess
from typing import Any, Dict, Optional, Tuple

from conftune.core.backup_manager import BackupManager
from conftune.core.logger import get_logger
from conftune.core.safety import SafetyEngine

DNF_CONF_PATH = "/etc/dnf/dnf.conf"
DNF5_CONF_PATH = "/etc/dnf/dnf5.conf"


class DNFTuner:
    """Manages DNF performance tweaks and cache maintenance."""

    def __init__(self, safety: Optional[SafetyEngine] = None, backup_mgr: Optional[BackupManager] = None):
        self.logger = get_logger()
        self.safety = safety or SafetyEngine()
        self.backup_mgr = backup_mgr or BackupManager()

    def get_current_settings(self) -> Dict[str, Any]:
        """Read and parse /etc/dnf/dnf.conf and /etc/dnf/dnf5.conf."""
        settings = {
            "max_parallel_downloads": "3",  # default in standard DNF
            "fastestmirror": "False",
            "defaultyes": "False",
            "keepcache": "False",
            "clean_requirements_on_remove": "True",
            "exists": os.path.isfile(DNF_CONF_PATH) or os.path.isfile(DNF5_CONF_PATH),
            "is_dnf5": bool(shutil.which("dnf5") or os.path.isfile(DNF5_CONF_PATH)),
        }

        # Check primary config paths
        for conf_file in [DNF_CONF_PATH, DNF5_CONF_PATH]:
            if not os.path.isfile(conf_file):
                continue

            try:
                parser = configparser.ConfigParser()
                parser.read(conf_file)
                section = "main" if parser.has_section("main") else parser.sections()[0] if parser.sections() else None
                if section:
                    for k in ["max_parallel_downloads", "fastestmirror", "defaultyes", "keepcache", "clean_requirements_on_remove"]:
                        if parser.has_option(section, k):
                            settings[k] = parser.get(section, k)
            except Exception as e:
                self.logger.warning(f"Error reading {conf_file}: {e}")

        return settings

    def apply_optimizations(
        self,
        max_parallel_downloads: int = 10,
        fastestmirror: bool = True,
        defaultyes: bool = True,
        keepcache: bool = True,
    ) -> Tuple[bool, str]:
        """Apply recommended DNF acceleration settings with pre-backup for DNF4 and DNF5."""
        valid, msg = self.safety.verify_privilege("Optimizing DNF configuration")
        if not valid:
            return False, msg

        targets = [DNF_CONF_PATH]
        if os.path.isfile(DNF5_CONF_PATH) or shutil.which("dnf5"):
            targets.append(DNF5_CONF_PATH)

        # Snapshot before modifying
        self.backup_mgr.create_snapshot(
            profile_name="dnf_optimization",
            target_paths=targets,
            notes="DNF acceleration tweaks (DNF4/DNF5)",
            dry_run=self.safety.dry_run,
        )

        if self.safety.dry_run:
            self.logger.info(
                f"[DRY RUN] Would set in {', '.join(targets)}: max_parallel_downloads={max_parallel_downloads}, "
                f"fastestmirror={fastestmirror}, defaultyes={defaultyes}, keepcache={keepcache}"
            )
            return True, "[DRY RUN] DNF configuration simulated successfully."

        try:
            for conf_file in targets:
                parser = configparser.ConfigParser()
                if os.path.isfile(conf_file):
                    parser.read(conf_file)

                if not parser.has_section("main"):
                    parser.add_section("main")

                parser.set("main", "max_parallel_downloads", str(max_parallel_downloads))
                parser.set("main", "fastestmirror", "True" if fastestmirror else "False")
                parser.set("main", "defaultyes", "True" if defaultyes else "False")
                parser.set("main", "keepcache", "True" if keepcache else "False")
                parser.set("main", "clean_requirements_on_remove", "True")

                os.makedirs(os.path.dirname(conf_file), exist_ok=True)
                with open(conf_file, "w", encoding="utf-8") as f:
                    parser.write(f)

                self.logger.info(f"Successfully tuned DNF configuration in {conf_file}.")

            dnf_version_note = " (DNF4 & DNF5)" if len(targets) > 1 else ""
            return True, f"DNF acceleration applied{dnf_version_note}: {max_parallel_downloads} concurrent downloads, fastestmirror=True."

        except Exception as e:
            err = f"Failed to update DNF configuration: {e}"
            self.logger.error(err)
            return False, err

    def clean_cache(self) -> Tuple[bool, str]:
        """Run DNF clean all / metadata purge."""
        dnf_cmd = shutil.which("dnf5") or shutil.which("dnf")
        if not dnf_cmd:
            return False, "Neither dnf5 nor dnf command found."

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would execute: {dnf_cmd} clean all"

        try:
            res = subprocess.run([dnf_cmd, "clean", "all"], capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                self.logger.info("Successfully cleaned DNF package and metadata cache.")
                return True, "DNF package cache and metadata cleaned."
            return False, f"DNF clean error: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Failed to clean DNF cache: {e}"
