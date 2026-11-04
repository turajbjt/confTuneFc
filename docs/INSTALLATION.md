# ConfTune FC Installation & Setup Guide 📥⚙️

This guide provides instructions for installing, configuring, running, and uninstalling **ConfTune FC** across supported Fedora, Rocky Linux, CentOS Stream, AlmaLinux, and RHEL environments.

---

## 📋 System Requirements

- **Supported Linux Distributions**:
  - **Fedora Workstation & Server**: Fedora 40, 41, 42, 43, 44, 45+
  - **Rocky Linux**: 8.x, 9.x, 10.x
  - **CentOS Stream / RHEL**: 8, 9, 10
  - **AlmaLinux / Oracle Linux**: 8.x, 9.x, 10.x
- **Python**: Version 3.9 or newer.
- **GUI Dependency**: `python3-pyqt6` (required for graphical interface; headless CLI runs on the Python standard library with no extra packages needed).
- **Optional Recommended Packages**:
  - `tuned` (dynamic profile switcher)
  - `smartmontools` (SMART drive and NVMe health inspection)
  - `gamemode` (low-latency process governor for gaming workloads)

---

## 📥 Installation Methods

### Method 1: Run Directly from Source (Fastest)

ConfTune FC can be run directly from source without installing anything into system directories:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/turajbjt/confTuneFc.git
   cd confTuneFc
   ```

2. **Install GUI dependencies (if using graphical mode)**:
   ```bash
   # Fedora / Rocky Linux / CentOS Stream / RHEL:
   sudo dnf install python3-pyqt6
   ```

3. **Launch the application**:
   ```bash
   # Launch GUI:
   python3 main.py

   # Or run headless CLI status check:
   python3 main.py --status
   ```

---

### Method 2: Install Desktop Launcher (Local User)

To integrate ConfTune FC into your GNOME, KDE, or XFCE application menu:

```bash
cd confTuneFc
./install-desktop.sh
```

This installs:
- Desktop launcher into `~/.local/share/applications/conftune-fc.desktop`
- High-resolution SVG vector icon into `~/.local/share/icons/hicolor/scalable/apps/conftune-fc.svg`
- Updates the local XDG desktop database.

---

### Method 3: Build & Install Native RPM Package

To package ConfTune FC as a system-wide RPM package:

1. **Install RPM build tools**:
   ```bash
   sudo dnf install rpm-build python3-setuptools
   ```

2. **Run the build script**:
   ```bash
   ./packaging/build-rpm.sh
   ```

3. **Install the generated package**:
   ```bash
   sudo dnf install dist/conftune-fc-*.noarch.rpm
   ```

The universal package is compatible across **Fedora 40+**, **Rocky Linux 8/9/10**, **CentOS Stream 8/9/10**, **AlmaLinux**, and **RHEL**. It installs:
- Executables: `/usr/bin/conftune` and `/usr/bin/conftune-fc`
- App core: `/usr/share/conftune-fc/` (Python bytecode is compiled on-target during `%post`)
- Polkit policy: `/usr/share/polkit-1/actions/io.github.conftune_fc.policy`
- Desktop entry: `/usr/share/applications/conftune-fc.desktop`
- Full icons hierarchy: `/usr/share/icons/hicolor/` (16x16 through 512x512 raster PNGs + scalable SVG)

---

## 🗑️ Uninstallation

### Uninstall Local Desktop Launcher
```bash
./uninstall-desktop.sh
```

### Uninstall RPM Package
```bash
sudo dnf remove conftune-fc
```

### Clean Up Local Snapshots and Logs (Optional)
```bash
# User mode snapshots:
rm -rf ~/.local/share/conftune

# System root snapshots and logs (if elevated tuning was executed):
sudo rm -rf /var/lib/conftune /var/log/conftune
```
