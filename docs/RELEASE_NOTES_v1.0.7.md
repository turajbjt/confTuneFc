# ConfTune FC v1.0.7 Release Notes ⚡

**ConfTune FC** is the open-source system optimization, kernel tuning, and automated deployment suite for Fedora Linux, Red Hat Enterprise Linux (RHEL), Rocky Linux, AlmaLinux, and CentOS Stream.

---

## 🚀 Key Improvements in v1.0.7

### 1. Autostart Manager ABRT Live Status & Dynamic Toggle
- **Live Status Indicator**: Added real-time status label (`lbl_abrt_status`) to the ABRT Bug Reporting Daemons card:
  - `Status: 🟢 ABRT Services Active / Running` (green) when any ABRT daemon is active.
  - `Status: ⚪ ABRT Services Inactive / Disabled` (muted gray) when all ABRT daemons are stopped and disabled.
- **Dynamic Action Button**: The action button now reflects live status dynamically:
  - Shows `"Disable ABRT Daemons"` with destructive red highlight when ABRT services are running.
  - Shows `"Enable ABRT Daemons"` when ABRT services are disabled.
- **Instant Live Refresh**: Automatically queries `systemctl is-active` on page load, refresh, and immediately after toggling ABRT state.

### 2. systemd-coredump Storage Ceiling Default / Undo & Live Status
- **Storage Ceiling Default (Undo) Button**: Added a dedicated `↺ Default (Undo)` button alongside `Apply Ceiling`.
  - Removes the custom drop-in override `/etc/systemd/coredump.conf.d/99-conftune.conf` safely with automatic pre-tune snapshot creation.
  - Instantly restores default systemd storage behavior without requiring full system rollbacks.
- **Live Coredump Status Badge**: Added real-time status badge (`lbl_cd_status`):
  - `Status: 🟢 Custom ceiling active (<limit>)` (green) when an override drop-in file is present.
  - `Status: ⚪ System default storage ceiling active (unlimited / 10% root)` (muted gray) when running stock defaults.
- **Active Limit Selector Sync**: The combo box automatically pre-selects the currently active custom limit (`50M`, `100M`, `200M`, `500M`, `1G`) on tab load and refresh.

### 3. Non-Root Security & Privilege Hardening
- **Autostart Manager Gray-Out**: In non-root mode, `btn_apply_cd`, `btn_reset_cd`, `combo_cd`, and `btn_toggle_abrt` are disabled with clear lock indicators (`🔒 Requires Root`).
- **Safety Engine Verification**: Integrated automatic PolicyKit privilege escalation prompt if an unprivileged user attempts modification.

### 4. Comprehensive Test Suite Expansion
- Added unit tests in `tests/test_defaults_and_undo.py` for coredump default/undo restore and ABRT active status detection.
- Added non-root privilege grayout assertions for `AutostartTab` in `tests/test_non_root_grayout.py`.

---

## 📦 Package Artifacts & Checksums (v1.0.7)

| File | SHA256 Checksum |
| :--- | :--- |
| `conftune-fc-1.0.7-1.noarch.rpm` | `30238392e20d72ee2ca402c355646fdfde36702858824cb124fa1175b3c142f3` |
| `conftune-fc-1.0.7-1.src.rpm` | `64e23da088b605d654c8810c9729606f97ace207a97aecb0d57e2ad5acda55d1` |

---

## 📥 Installation & Upgrade Instructions

To upgrade to **v1.0.7** on Fedora, Rocky Linux, CentOS Stream, or RHEL:

```bash
sudo dnf update -y ./conftune-fc-1.0.7-1.noarch.rpm
```
*(or via rpm: `sudo rpm -Uvh ./conftune-fc-1.0.7-1.noarch.rpm`)*
