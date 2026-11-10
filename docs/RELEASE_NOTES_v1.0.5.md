# ConfTune FC v1.0.5 Release Notes ⚡

**ConfTune FC** is the open-source system optimization, kernel tuning, and automated deployment suite for Fedora Linux, Red Hat Enterprise Linux (RHEL), Rocky Linux, AlmaLinux, and CentOS Stream.

---

## 🚀 Key Improvements in v1.0.5

### 1. Unprivileged User Safety Mode (Non-Root Grayscale Protection)
- **Automatic Privilege-Aware UI**: When launched as a regular unprivileged user (non-root), all system-modifying controls across all 12 GUI tabs are automatically grayed out and disabled.
- **Informative Tooltips**: Hovering over any disabled control clearly indicates: *"Root privileges required for this action. Click 'Run as Root' in the header to elevate."*
- **Dedicated Disabled Styling**: Enhanced `ADWAITA_DARK_STYLE` with explicit `:disabled` rules for push buttons, checkboxes, radio buttons, spinboxes, text inputs, and table cells to visually communicate non-interactive states.
- **Safe Read-Only Exploration**: Users can safely navigate profiles, inspect boot times, review hardware diagnostics, and export deployment presets without accidental permission errors.

### 2. Granular 1-Click "Reset to Default" / Undo Engine
- **Per-Option Rollbacks**: Every tuning module now provides dedicated Default / Undo controls, allowing users to restore individual settings back to stock Fedora / upstream defaults without performing a full snapshot rollback.
- **Dynamic Active Status Badges**: Added live status indicators and override detection across modules:
  - **DNF Accelerator**: Live badge indicating *"Default Settings Active"* vs *"Optimized Overrides Active"*, plus "Reset DNF to Defaults" action.
  - **Fedy Essentials**: Live status badges and "Reset Fedy Tweaks to Defaults" (restores default font rendering, GNOME button layout, and night light).
  - **Privacy & Telemetry**: Live status badges and "Restore Default Telemetry" button.
  - **Process Priority & Memory**: Live status badges and "Reset Process Settings to Defaults" (systemd-oomd and ZRAM defaults).
  - **Storage & Filesystems**: Live status badges and "Reset Storage Settings to Defaults" (stock elevator schedulers).
  - **Kernel Sysctl**: Live status badges and "Reset All Sysctl to Default" action.
  - **Systemd & Boot Services**: Live status badges and "Reset Systemd Tuning to Defaults" (stock journald and coredump configs).

### 3. DNF Accelerator Live Configuration Loading
- **Live Disk Inspection**: Corrected `get_current_settings()` to dynamically query both `/etc/dnf/dnf5.conf` and `/etc/dnf/dnf.conf`.
- **Accurate Parallel Downloads**: The maximum concurrent downloads spinbox now populates with the actual active value on disk rather than defaulting to 3.
- **Accurate Checkbox Status**: Fastest Mirror, Default Yes, and Keep Cache checkboxes accurately reflect current disk state upon tab loading.

### 4. Fedy Essentials UI & Ergonomics
- **Dynamic RPM Fusion Status**: Replaced static gray circle icon with dynamic green (`● Enabled`) and red (`● Disabled`) status indicators.
- **Dynamic Action Button**: Button text toggles dynamically between *"Enable RPM Fusion Repositories"* and *"Disable RPM Fusion Repositories"*.
- **GNOME Titlebar Button Ordering**: Corrected GNOME Desktop Productivity layout from `[max][min][close]` to `[min][max][close]` (`appmenu:minimize,maximize,close`), aligning with upstream GNOME Tweaks standards.

### 5. Layout & Whitespace Optimization
- **Compact Profile Cards**: Reduced excessive vertical white space in the *Tuning Profiles & Workload Presets* card.
- **Expanded Lower Detail View**: Extended the lower configuration detail containers to substantially minimize vertical scrolling when inspecting profile settings.

### 6. Expanded Automated Test Suite
- Added `tests/test_defaults_and_undo.py` (7 tests covering default restore logic across all core tuners).
- Added `tests/test_non_root_grayout.py` (12 tests verifying proper control disabling when unprivileged).
- Total test coverage increased to **134 passing tests** across all core modules, CLI workflows, snapshot rollbacks, and GUI tabs.

---

## 📦 Package Artifacts & Checksums (v1.0.5)

| File | SHA256 Checksum |
| :--- | :--- |
| `conftune-fc-1.0.5-1.noarch.rpm` | `e93ec9e32d7b157b64ae82baf9855da33cb7286587c6ece8ec28146e79dd634e` |
| `conftune-fc-1.0.5-1.src.rpm` | `85dbd515effa1decc7a733b613a36b00cae335423ffc821b28ca545389ba1614` |

---

## 📥 Installation & Upgrade Instructions

To upgrade to **v1.0.5** on Fedora, Rocky Linux, CentOS Stream, or RHEL:

```bash
sudo dnf update -y ./conftune-fc-1.0.5-1.noarch.rpm
```
*(or via rpm: `sudo rpm -Uvh ./conftune-fc-1.0.5-1.noarch.rpm`)*
