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
        """Read and parse live DNF/DNF5 configuration and /etc/dnf/ configuration files."""
        is_dnf5 = bool(shutil.which("dnf5") or os.path.isfile(DNF5_CONF_PATH))
        settings = {
            "max_parallel_downloads": "3",  # default in standard DNF
            "fastestmirror": "False",
            "defaultyes": "False",
            "keepcache": "False",
            "clean_requirements_on_remove": "True",
            "exists": os.path.isfile(DNF_CONF_PATH) or os.path.isfile(DNF5_CONF_PATH),
            "is_dnf5": is_dnf5,
        }

        # 1. Query live runtime DNF configuration via CLI if available
        queried = False
        if shutil.which("dnf5"):
            try:
                res = subprocess.run(
                    ["dnf5", "--dump-main-config"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3,
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if "=" in line:
                            k, v = [x.strip() for x in line.split("=", 1)]
                            if k == "max_parallel_downloads" and v:
                                settings[k] = v
                            elif k in ["fastestmirror", "defaultyes", "keepcache", "clean_requirements_on_remove"]:
                                settings[k] = "True" if v.lower() in ("1", "true", "yes", "on") else "False"
                    queried = True
            except Exception as e:
                self.logger.debug(f"dnf5 --dump-main-config query failed: {e}")

        if not queried and shutil.which("dnf"):
            try:
                res = subprocess.run(
                    ["dnf", "config-manager", "--dump"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3,
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if "=" in line:
                            k, v = [x.strip() for x in line.split("=", 1)]
                            if k == "max_parallel_downloads" and v:
                                settings[k] = v
                            elif k in ["fastestmirror", "defaultyes", "keepcache", "clean_requirements_on_remove"]:
                                settings[k] = "True" if v.lower() in ("1", "true", "yes", "on") else "False"
                    queried = True
            except Exception as e:
                self.logger.debug(f"dnf config-manager --dump query failed: {e}")

        # 2. Check configuration files and drop-in dirs for explicit overrides or fallback
        conf_candidates = [DNF_CONF_PATH, DNF5_CONF_PATH]
        for dropin_dir in ["/etc/dnf/libdnf5.conf.d", "/etc/dnf/dnf.conf.d"]:
            if os.path.isdir(dropin_dir):
                try:
                    for fname in sorted(os.listdir(dropin_dir)):
                        if fname.endswith(".conf"):
                            conf_candidates.append(os.path.join(dropin_dir, fname))
                except Exception:
                    pass

        for conf_file in conf_candidates:
            if not os.path.isfile(conf_file):
                continue

            try:
                parser = configparser.ConfigParser()
                parser.read(conf_file)
                section = "main" if parser.has_section("main") else parser.sections()[0] if parser.sections() else None
                if section:
                    for k in ["max_parallel_downloads", "fastestmirror", "defaultyes", "keepcache", "clean_requirements_on_remove"]:
                        if parser.has_option(section, k):
                            raw_val = parser.get(section, k).strip()
                            if k in ["fastestmirror", "defaultyes", "keepcache", "clean_requirements_on_remove"]:
                                settings[k] = "True" if raw_val.lower() in ("1", "true", "yes", "on") else "False"
                            else:
                                settings[k] = raw_val
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

                import io
                buf = io.StringIO()
                parser.write(buf)
                ok_w, msg_w = self.safety.write_file(conf_file, buf.getvalue())
                if not ok_w:
                    return False, f"Failed to write {conf_file}: {msg_w}"

                self.logger.info(f"Successfully tuned DNF configuration in {conf_file}.")

            dnf_version_note = " (DNF4 & DNF5)" if len(targets) > 1 else ""
            return True, f"DNF acceleration applied{dnf_version_note}: {max_parallel_downloads} concurrent downloads, fastestmirror=True."

        except Exception as e:
            err = f"Failed to update DNF configuration: {e}"
            self.logger.error(err)
            return False, err

    def is_customized(self) -> bool:
        """Check whether non-default DNF performance settings are active."""
        settings = self.get_current_settings()
        try:
            dl = int(str(settings.get("max_parallel_downloads", "3")).strip())
        except (ValueError, TypeError):
            dl = 3
        fastest = str(settings.get("fastestmirror", "False")).lower() in ("true", "1", "yes")
        defyes = str(settings.get("defaultyes", "False")).lower() in ("true", "1", "yes")
        keepcache = str(settings.get("keepcache", "False")).lower() in ("true", "1", "yes")
        return dl != 3 or fastest or defyes or keepcache

    def restore_defaults(self) -> Tuple[bool, str]:
        """Restore standard Fedora DNF defaults (3 downloads, fastestmirror=False, defaultyes=False, keepcache=False)."""
        valid, msg = self.safety.verify_privilege("Restoring DNF default configuration")
        if not valid:
            return False, msg

        ok, msg_opt = self.apply_optimizations(
            max_parallel_downloads=3,
            fastestmirror=False,
            defaultyes=False,
            keepcache=False,
        )
        if ok:
            return True, "DNF configuration restored to standard Fedora defaults (3 parallel downloads, mirrors/cache defaults)."
        return False, msg_opt

    def clean_cache(self) -> Tuple[bool, str]:
        """Run DNF clean all / metadata purge."""
        dnf_cmd = shutil.which("dnf5") or shutil.which("dnf")
        if not dnf_cmd:
            return False, "Neither dnf5 nor dnf command found."

        if self.safety.dry_run:
            return True, f"[DRY RUN] Would execute: {dnf_cmd} clean all"

        try:
            res = self.safety.run_command([dnf_cmd, "clean", "all"], timeout=30)
            if res.returncode == 0:
                self.logger.info("Successfully cleaned DNF package and metadata cache.")
                return True, "DNF package cache and metadata cleaned."
            return False, f"DNF clean error: {res.stderr.strip()}"
        except Exception as e:
            return False, f"Failed to clean DNF cache: {e}"
