#!/usr/bin/env bash
# ConfTune FC - Desktop Launcher Installer
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_DIR="${HOME}/.local/share/applications"
ICONS_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"

mkdir -p "${APPS_DIR}"
mkdir -p "${ICONS_DIR}"

# Check for GUI dependency (PyQt6)
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo "⚠️  Warning: PyQt6 was not found in python3."
    echo "   The graphical user interface requires PyQt6."
    echo "   To install on Fedora / RHEL / CentOS / Rocky:"
    echo "     sudo dnf install python3-pyqt6"
    echo "   Or via pip:"
    echo "     pip install PyQt6"
    echo ""
fi

# Copy icon
cp "${SCRIPT_DIR}/assets/icon.svg" "${ICONS_DIR}/conftune-fc.svg"

# Generate desktop file with absolute path to main.py
cat <<EOF > "${APPS_DIR}/conftune-fc.desktop"
[Desktop Entry]
Name=ConfTune FC
GenericName=System Performance Tuner
Comment=Setup, configuration & performance tuning for Fedora, Rocky Linux, and CentOS
Exec=${SCRIPT_DIR}/main.py
Icon=${ICONS_DIR}/conftune-fc.svg
Terminal=false
Type=Application
Categories=System;Settings;HardwareSettings;
StartupNotify=true
Keywords=performance;tune;tuner;fedora;rocky;centos;rhel;sysctl;dnf;zram;docker;podman;kvm;virtualmin;webmin;
EOF

chmod +x "${APPS_DIR}/conftune-fc.desktop"
update-desktop-database "${APPS_DIR}" 2>/dev/null || true

echo "ConfTune FC desktop entry installed successfully to ${APPS_DIR}/conftune-fc.desktop!"
echo "You can now launch ConfTune FC from GNOME Application Menu or run: ${SCRIPT_DIR}/main.py"
