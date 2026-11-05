"""
Safety Engine for ConfTune FC.
Provides privilege checks, dry-run mode protections, and configuration sanity checks.
"""

import os
import shutil
import subprocess
from typing import Optional, Tuple


class SafetyEngine:
    """Safeguards tuning operations and manages simulation/privilege requirements."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._is_root_override: Optional[bool] = None

    @property
    def is_root(self) -> bool:
        """Return True if running under root (UID 0)."""
        if self._is_root_override is not None:
            return self._is_root_override
        return os.geteuid() == 0

    @is_root.setter
    def is_root(self, value: Optional[bool]) -> None:
        self._is_root_override = value

    @property
    def has_pkexec(self) -> bool:
        """Check if pkexec is available for GUI Polkit elevation."""
        return shutil.which("pkexec") is not None

    @property
    def has_sudo(self) -> bool:
        """Check if sudo is available."""
        return shutil.which("sudo") is not None

    def verify_privilege(self, action_name: str = "Tuning operation") -> Tuple[bool, str]:
        """Check if current execution has required privileges."""
        if self.dry_run:
            return True, "Simulation mode (dry-run) active. No elevated privileges required."
        if self.is_root:
            return True, "Root privileges verified."
        return False, (
            f"{action_name} requires root privileges to modify system configuration files. "
            "Please run with sudo/pkexec or use --dry-run."
        )

    def sanitize_sysctl_value(self, key: str, val: str) -> bool:
        """Basic sanity check on sysctl key-value pairs."""
        if not key or not re_match_key(key):
            return False
        # Do not allow newlines or shell command injections
        if any(char in val for char in [";", "&", "|", "`", "$", "\n", "\r"]):
            return False
        return True


def re_match_key(key: str) -> bool:
    """Validate sysctl identifier."""
    import re
    return bool(re.match(r"^[a-zA-Z0-9_\.\-]+$", key))
