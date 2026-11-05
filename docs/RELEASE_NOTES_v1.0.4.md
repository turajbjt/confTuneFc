# ConfTune FC v1.0.4 Release Notes ⚡

**ConfTune FC** is the open-source system optimization, kernel tuning, and automated deployment suite for Fedora Linux, Red Hat Enterprise Linux (RHEL), Rocky Linux, AlmaLinux, and CentOS Stream.

---

## 🚀 Key Improvements in v1.0.4

### 1. Comprehensive Beta Disclaimers & Safety Alignment with ConfClean FC
- **Explicit Caution Blocks**: Integrated prominent `[!CAUTION]` Beta Software warnings across documentation (`README.md`, `docs/SAFETY.md`, `docs/ARCHITECTURE.md`, `docs/CLI_REFERENCE.md`).
- **Clear Terms of Use & Liability Protections**: Explicitly sets expectations around "AS IS" beta status, user review responsibility, and recommendation of independent system backups.
- **GUI Visual Beta Indicator**: Added high-visibility amber `BETA` pill badge in the application header bar alongside the version tag.
- **Overview Dashboard Safety Card**: Added a dedicated safety notice card in the System Dashboard view reminding administrators to verify dry-run simulation diffs before applying changes.
- **CLI Banner Tag**: Added `[BETA]` identifier to the terminal performance status header.

---

## 🚀 Key Improvements from v1.0.3, v1.0.2 & v1.0.1

### 1. Robust PolicyKit Privilege Escalation (`confclean-fc` Pattern)
- **Wayland / XWayland Display Authorization**: Automatically executes `xhost +SI:localuser:root` to authorize the root user to connect to the active XWayland display server.
- **Environment Forwarding**: Forwards `DISPLAY`, `XAUTHORITY`, and sets `QT_QPA_PLATFORM=xcb` through `/usr/bin/env` so root-level Qt interfaces initialize cleanly without crashing.
- **Asynchronous GUI Readiness Handshake**: Parent process monitors the elevated child process via `ElevationWorker(QThread)`. The parent waits for the `CONFTUNE_ELEVATED_READY` signal before exiting, eliminating blank screens and application terminations.
- **Graceful Cancellation Recovery**: If the user dismisses the PolicyKit dialog or authentication fails, the parent window restores interactive controls and remains running without exiting.

### 2. Seamless Typography & Background Blending
- **Transparent Text Widget Backgrounds**: Added explicit `background-color: transparent` rules for `QLabel`, `QCheckBox`, and `QRadioButton` in `ADWAITA_DARK_STYLE`.
- **Elimination of Background Clipping Artifacts**: Labels placed inside `#2d2d2d` cards, `#2a2a2a` header bars, or `#1e1e1e` dialogs now blend seamlessly with their containers instead of drawing mismatched `#242424` boxes behind words.
- **Badge Capsule Integrity**: Maintained high-contrast capsule backgrounds for `#pill_badge`, `#pill_root`, `#pill_accent`, and `#pill_success`.

### 3. Boot & Systemd Optimizer Presentation Fixes
- **Button Dimension Normalization**: Fixed table action column width to `195px` (`ResizeMode.Fixed`) and table row height to `44px`.
- **Legible Typography**: Applied explicit minimum button width (`150px`), height (`28px`), and bold `12px` font styling to ensure buttons never collapse or display elided dotted lines (`...`).

### 4. Expanded Automated Test Suite
- Maintained **115 passing tests** across core tuning modules, CLI workflows, snapshot rollbacks, and GUI components.

---

## 📦 Package Artifacts & Checksums (v1.0.4)

| File | SHA256 Checksum |
| :--- | :--- |
| `conftune-fc-1.0.4-1.noarch.rpm` | `66c0d18b0f7f541d19ce50509e12fab09e29b3e07d84d833e98c5f7c926c0737` |
| `conftune-fc-1.0.4-1.src.rpm` | `4d68453f0f24ba3bff6d18041fdfcbac87f4122a934b977cb9f83154477e35ba` |

---

## 📥 Installation & Upgrade Instructions

To upgrade to **v1.0.4** on Fedora, Rocky Linux, CentOS Stream, or RHEL:

```bash
sudo dnf update -y ./dist/conftune-fc-1.0.4-1.noarch.rpm
```
*(or via rpm: `sudo rpm -Uvh ./dist/conftune-fc-1.0.4-1.noarch.rpm`)*
