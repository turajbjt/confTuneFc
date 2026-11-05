# ConfTune FC Safety Engine & Principles 🛡️

System tuning involves modifying low-level operating system parameters. To ensure rock-solid stability and zero downtime, ConfTune FC adheres to strict safety principles.

---

> [!CAUTION]
> ## ⚠️ BETA STATUS, DISCLAIMER & USE AT YOUR OWN RISK
>
> **ConfTune FC is currently in active BETA.**
>
> While every feature has been built with defense-in-depth safety checks and backed by comprehensive unit tests, system tuning inherently interacts with low-level kernel parameters, systemd units, hardware scaling governors, and core `/etc/` configuration files.
>
> **Please read and understand this disclaimer prior to using the application:**
> 1. **USE STRICTLY AT YOUR OWN RISK**: The software is provided "as is", without warranty of any kind, express or implied.
> 2. **NO LIABILITY**: Under no legal theory (contract, tort, negligence, or otherwise) shall the authors, maintainers, or contributors be liable for any damages, data loss, operating system unbootability, kernel panics, package manager issues, desktop environment crashes, or system downtime arising from the operation of this software.
> 3. **INDEPENDENT BACKUP REQUIREMENT**: Although ConfTune FC automatically generates configuration snapshots with JSON manifests prior to applying changes, **automated snapshots do not replace an external, independent backup strategy**. Maintain full backups of your system and critical configurations prior to executing non-dry-run operations.
> 4. **USER RESPONSIBILITY**: It is the user's sole responsibility to inspect candidate parameters and profile diffs presented during dry-run simulations before approving system tuning or service changes.

---

## 🔒 Core Safety Principles

1. **Non-Destructive Defaults**:
   - Running ConfTune FC without `--apply` defaults to **simulation mode (dry-run)**.
   - Files are never modified or overwritten without explicit user confirmation.

2. **Pre-Tune Snapshots**:
   - Before any file is modified (`/etc/sysctl.d/99-conftune.conf`, `/etc/dnf/dnf.conf`, `/etc/systemd/journald.conf.d/`, etc.), an exact snapshot of existing files is captured.
   - If a target file didn't exist prior to tuning, the snapshot records that fact so rollback can safely clean it up.

3. **1-Click Rollback**:
   - Any tuning session can be reverted instantly.
   - Rollback restores original file contents, removes newly generated files, and runs `sysctl --system` and `systemctl daemon-reload`.

4. **Input Sanitization & Injection Defense**:
   - All sysctl identifiers and values are validated against strict alphanumeric and dotted format patterns (`^[a-zA-Z0-9_\.\-]+$`).
   - Semicolons, pipes, backticks, dollar signs, and newline characters are rejected.

5. **Privilege Boundary Enforcement & UI Locking**:
   - Read-only inspection (`--status`, `--list-profiles`, `--snapshots`, monitoring dashboards) and dry-run simulations do not require root privileges.
   - User space configurations (subpixel font hinting in `~/.config/fontconfig`, GNOME tweaks via `gsettings`, login autostart entries in `~/.config/autostart`, preset export, deploy.sh generation, and Kickstart creation) are fully accessible to casual users without root.
   - System modifications writing to `/etc/` or `/sys/` require UID 0. In the GUI, administrative actions display visual locks (`🔒`) and open a native PolicyKit elevation dialog (`pkexec`) or provide instructions for `sudo conftune-fc`.
   - In CLI mode, administrative actions invoked without root are intercepted upfront and rejected with exit code `1`, displaying the exact `sudo` command required.

---

## 🗄️ Snapshot Storage Locations

| Execution Mode | Snapshot Directory | Log Directory | Fallback (Sandboxed / Read-Only Home) |
| :--- | :--- | :--- | :--- |
| **Root (`sudo` / `pkexec`)** | `/var/lib/conftune/backups` | `/var/log/conftune` | `/tmp/conftune/backups` & `/tmp/conftune/logs` |
| **Unprivileged User** | `~/.local/share/conftune/backups` | `~/.local/share/conftune/logs` | `/tmp/conftune/backups` & `/tmp/conftune/logs` |

---

## ⏪ Restoring from a Snapshot

To restore a previous configuration via CLI:
```bash
# 1. List available snapshots:
conftune --snapshots

# 2. Revert to a specific snapshot:
sudo conftune --rollback <SNAPSHOT_ID> --apply
```

Or via GUI:
1. Open the **Snapshots & Rollback** tab from the sidebar.
2. Select the snapshot from the table.
3. Review the file manifest in the preview box.
4. Click **Rollback to Snapshot**.
