"""
Backup and Snapshot Manager for ConfTune FC.
Automatically snapshots system configuration files before any tuning changes,
enabling reliable 1-click rollback and verification.
"""

import datetime
import json
import os
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

from conftune.core.logger import get_logger


class BackupManager:
    """Manages pre-tune configuration snapshots and rollbacks."""

    def __init__(self, backup_dir: Optional[str] = None):
        self.logger = get_logger()
        if backup_dir:
            self.base_dir = backup_dir
        elif os.geteuid() == 0:
            self.base_dir = "/var/lib/conftune/backups"
        else:
            self.base_dir = os.path.expanduser("~/.local/share/conftune/backups")
        os.makedirs(self.base_dir, exist_ok=True)

    def create_snapshot(self, profile_name: str, target_paths: List[str], notes: str = "") -> Optional[str]:
        """
        Create a timestamped snapshot of targeted files before applying tuning.
        Returns the snapshot directory ID, or None if snapshot could not be created.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snap_{timestamp}_{profile_name.replace(' ', '_').lower()}"
        snap_dir = os.path.join(self.base_dir, snapshot_id)

        try:
            os.makedirs(snap_dir, exist_ok=True)
            files_meta = []

            for path in target_paths:
                exists = os.path.isfile(path)
                rel_clean = path.lstrip("/")
                dest_file = os.path.join(snap_dir, rel_clean)

                if exists:
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(path, dest_file)
                    files_meta.append({
                        "original_path": path,
                        "backup_rel_path": rel_clean,
                        "existed": True,
                        "size": os.path.getsize(path),
                    })
                else:
                    files_meta.append({
                        "original_path": path,
                        "backup_rel_path": rel_clean,
                        "existed": False,
                        "size": 0,
                    })

            meta = {
                "id": snapshot_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "profile": profile_name,
                "notes": notes,
                "files": files_meta,
            }

            with open(os.path.join(snap_dir, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

            self.logger.info(f"Created configuration snapshot {snapshot_id} ({len(files_meta)} targets tracked).")
            return snapshot_id

        except Exception as e:
            self.logger.error(f"Failed to create configuration snapshot: {e}")
            return None

    def list_snapshots(self) -> List[Dict]:
        """List all available snapshots ordered from newest to oldest."""
        snapshots = []
        if not os.path.isdir(self.base_dir):
            return snapshots

        for name in sorted(os.listdir(self.base_dir), reverse=True):
            snap_path = os.path.join(self.base_dir, name)
            meta_path = os.path.join(snap_path, "metadata.json")
            if os.path.isdir(snap_path) and os.path.isfile(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        meta["directory"] = snap_path
                        snapshots.append(meta)
                except Exception as e:
                    self.logger.warning(f"Could not read metadata for snapshot {name}: {e}")
        return snapshots

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Retrieve a specific snapshot by ID."""
        for snap in self.list_snapshots():
            if snap.get("id") == snapshot_id:
                return snap
        return None

    def rollback_snapshot(self, snapshot_id: str, dry_run: bool = False) -> Tuple[bool, str]:
        """
        Restore system files from a given snapshot.
        If a file didn't exist prior to tuning, it will be removed.
        """
        snap = self.get_snapshot(snapshot_id)
        if not snap:
            return False, f"Snapshot ID '{snapshot_id}' not found."

        snap_dir = snap.get("directory")
        files = snap.get("files", [])
        restored = 0
        removed = 0

        self.logger.info(f"Initiating rollback for snapshot {snapshot_id} (dry_run={dry_run})...")

        for f_info in files:
            orig_path = f_info["original_path"]
            existed = f_info["existed"]
            backup_file = os.path.join(snap_dir, f_info["backup_rel_path"])

            if existed:
                if not os.path.isfile(backup_file):
                    self.logger.warning(f"Backup file missing: {backup_file}")
                    continue
                if not dry_run:
                    os.makedirs(os.path.dirname(orig_path), exist_ok=True)
                    shutil.copy2(backup_file, orig_path)
                restored += 1
                self.logger.info(f"{'[DRY RUN] Would restore' if dry_run else 'Restored'}: {orig_path}")
            else:
                # File was newly created by tuning, remove it
                if os.path.isfile(orig_path):
                    if not dry_run:
                        os.remove(orig_path)
                    removed += 1
                    self.logger.info(f"{'[DRY RUN] Would remove newly created' if dry_run else 'Removed'}: {orig_path}")

        # Re-apply sysctl and systemd if applicable
        if not dry_run:
            self._reload_subsystems()

        status_msg = f"Rollback complete: {restored} files restored, {removed} newly created files removed."
        self.logger.info(status_msg)
        return True, status_msg

    def _reload_subsystems(self) -> None:
        """Trigger reload of sysctl and systemd after configuration rollback."""
        try:
            if shutil.which("sysctl"):
                subprocess.run(["sysctl", "--system"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if shutil.which("systemctl"):
                subprocess.run(["systemctl", "daemon-reload"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self.logger.warning(f"Error refreshing subsystems during rollback: {e}")
