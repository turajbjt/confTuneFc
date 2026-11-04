#!/usr/bin/env bash
# ConfTune FC - Desktop Launcher Uninstaller
set -e

APPS_DIR="${HOME}/.local/share/applications"
ICONS_DIR="${HOME}/.local/share/icons/hicolor/scalable/apps"

rm -f "${APPS_DIR}/conftune-fc.desktop"
rm -f "${APPS_DIR}/conftune.desktop"
rm -f "${ICONS_DIR}/conftune-fc.svg"

update-desktop-database "${APPS_DIR}" 2>/dev/null || true

echo "ConfTune FC desktop shortcuts and icons uninstalled."
