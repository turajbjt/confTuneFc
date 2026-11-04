# ConfTune FC Safety Engine & Principles 🛡️

System tuning involves modifying low-level operating system parameters. To ensure rock-solid stability and zero downtime, ConfTune FC adheres to strict safety principles.

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

5. **Privilege Boundary Enforcement**:
   - Read-only inspection (`--status`, `--list-profiles`, `--snapshots`, and dry-run simulations) does not require root privileges.
   - System modifications verify UID 0 (`os.geteuid() == 0`) or offer Polkit elevation (`pkexec`) via `packaging/io.github.conftune_fc.policy`.

---

## 🗄️ Snapshot Storage Locations

| Execution Mode | Snapshot Directory | Log Directory |
| :--- | :--- | :--- |
| **Root (`sudo` / `pkexec`)** | `/var/lib/conftune/backups` | `/var/log/conftune` |
| **Unprivileged User** | `~/.local/share/conftune/backups` | `~/.local/share/conftune/logs` |

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
