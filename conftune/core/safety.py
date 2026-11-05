"""
Safety Engine for ConfTune FC.
Provides privilege checks, dry-run mode protections, and configuration sanity checks.
Supports in-process sudo elevation and safe privileged file/command execution.
"""

import os
import shutil
import subprocess
from typing import List, Optional, Tuple


class SafetyEngine:
    """Safeguards tuning operations and manages simulation/privilege requirements."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._is_root_override: Optional[bool] = None
        self.sudo_password: Optional[str] = None

    @property
    def is_root(self) -> bool:
        """Return True if running under root (UID 0) or elevated with valid sudo."""
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

    def authenticate_sudo(self, password: str) -> Tuple[bool, str]:
        """
        Verify the provided password against sudo using 'sudo -S -v'.
        If successful, caches the password and marks the session as elevated.
        """
        if not self.has_sudo:
            return False, "The 'sudo' command is not available on this system."

        try:
            res = subprocess.run(
                ["sudo", "-S", "-v"],
                input=f"{password}\n".encode("utf-8"),
                capture_output=True,
                timeout=8,
            )
            if res.returncode == 0:
                self.sudo_password = password
                self.is_root = True
                return True, "Administrator authentication verified successfully."
            err = res.stderr.decode("utf-8", errors="ignore").strip()
            return False, err or "Incorrect password or user not authorized in sudoers."
        except subprocess.TimeoutExpired:
            return False, "Authentication timed out. Please try again."
        except Exception as e:
            return False, f"Authentication error: {e}"

    def check_passwordless_sudo(self) -> bool:
        """Check if user has passwordless sudo authorization (sudo -n true)."""
        if not self.has_sudo:
            return False
        try:
            res = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=3)
            if res.returncode == 0:
                self.is_root = True
                return True
        except Exception:
            pass
        return False

    def write_file(self, file_path: str, content: str) -> Tuple[bool, str]:
        """
        Safely write content to a file.
        In dry-run mode, logs the simulation without modifying the filesystem.
        If running as root (UID 0) or user has write permissions, writes directly.
        If unprivileged and requires elevated access, writes using 'sudo tee'.
        """
        if self.dry_run:
            return True, f"[DRY RUN] Would write to {file_path}"

        parent_dir = os.path.dirname(file_path) or "."
        is_user_writable = os.access(file_path, os.W_OK) if os.path.exists(file_path) else os.access(parent_dir, os.W_OK)
        if os.geteuid() == 0 or is_user_writable:
            try:
                if os.path.dirname(file_path):
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True, f"Successfully wrote {file_path}."
            except PermissionError:
                pass  # Fall through to sudo elevation
            except Exception as e:
                return False, str(e)

        # Unprivileged execution: write via sudo tee
        dirname = os.path.dirname(file_path)
        try:
            if dirname:
                if self.sudo_password:
                    subprocess.run(
                        ["sudo", "-S", "mkdir", "-p", dirname],
                        input=f"{self.sudo_password}\n".encode("utf-8"),
                        capture_output=True,
                        timeout=5,
                    )
                else:
                    subprocess.run(["sudo", "-n", "mkdir", "-p", dirname], capture_output=True, timeout=5)

            cmd = ["sudo", "-S" if self.sudo_password else "-n", "tee", file_path]
            input_bytes = (f"{self.sudo_password}\n" if self.sudo_password else "").encode("utf-8") + content.encode("utf-8")
            res = subprocess.run(cmd, input=input_bytes, capture_output=True, timeout=10)
            if res.returncode == 0:
                return True, f"Successfully wrote {file_path} via sudo."
            err = res.stderr.decode("utf-8", errors="ignore").strip()
            return False, err or f"Failed to write {file_path} via sudo (code {res.returncode})"
        except Exception as e:
            # Fallback to direct write attempt if sudo failed or unavailable
            try:
                if os.path.dirname(file_path):
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True, f"Successfully wrote {file_path}."
            except Exception:
                return False, str(e)

    def copy_file(self, src: str, dst: str) -> Tuple[bool, str]:
        """Copy a file, using sudo if unprivileged."""
        if self.dry_run:
            return True, f"[DRY RUN] Would copy {src} -> {dst}"

        dst_dir = os.path.dirname(dst) or "."
        is_dst_writable = os.access(dst, os.W_OK) if os.path.exists(dst) else os.access(dst_dir, os.W_OK)
        if os.geteuid() == 0 or is_dst_writable:
            try:
                if os.path.dirname(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                return True, f"Copied {src} to {dst}."
            except PermissionError:
                pass  # Fall through to sudo
            except Exception as e:
                return False, str(e)

        try:
            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.write_file(dst, content)
        except Exception as e:
            return False, str(e)

    def remove_file(self, file_path: str) -> Tuple[bool, str]:
        """Remove a file, using sudo if unprivileged."""
        if self.dry_run:
            return True, f"[DRY RUN] Would remove {file_path}"

        parent_dir = os.path.dirname(file_path) or "."
        if os.geteuid() == 0 or (os.path.exists(file_path) and os.access(parent_dir, os.W_OK)):
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                return True, f"Removed {file_path}."
            except PermissionError:
                pass  # Fall through to sudo
            except Exception as e:
                return False, str(e)

        try:
            res = self.run_command(["rm", "-f", file_path])
            return res.returncode == 0, f"Removed {file_path}."
        except Exception as e:
            return False, str(e)

    def run_command(self, cmd: List[str], check_privilege: bool = True, timeout: int = 30) -> subprocess.CompletedProcess:
        """
        Run a system command. If unprivileged and privilege is required,
        prefixes the command with sudo.
        """
        if check_privilege and os.geteuid() != 0 and self.has_sudo and cmd[0] != "sudo":
            if self.sudo_password:
                full_cmd = ["sudo", "-S"] + cmd
                return subprocess.run(
                    full_cmd,
                    input=f"{self.sudo_password}\n".encode("utf-8"),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            else:
                full_cmd = ["sudo", "-n"] + cmd
                return subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def verify_privilege(self, action_name: str = "Tuning operation") -> Tuple[bool, str]:
        """Check if current execution has required privileges."""
        if self.dry_run:
            return True, "Simulation mode (dry-run) active. No elevated privileges required."
        if self.is_root:
            return True, "Root privileges verified."
        return False, (
            f"{action_name} requires root privileges to modify system configuration files. "
            "Please authenticate with sudo or use --dry-run."
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
