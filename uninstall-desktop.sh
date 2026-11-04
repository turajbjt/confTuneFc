#!/usr/bin/env bash
# ConfTune FC - Desktop Launcher Uninstaller
set -e

APPS_DIR="${HOME}/.local/share/applications"
ICONS_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"

rm -f "${APPS_DIR}/conftune-fc.desktop"
rm -f "${APPS_DIR}/conftune.desktop"
rm -f "${ICONS_DIR}/conftune-fc.svg"

for size in 16 24 32 48 64 128 256 512; do
    rm -f "${HOME}/.local/share/icons/hicolor/${size}x${size}/apps/conftune-fc.png"
done

update-desktop-database "${APPS_DIR}" 2>/dev/null || true

echo "ConfTune FC desktop shortcuts and icons uninstalled."
