#!/usr/bin/env bash
# ConfTune FC - RPM Packaging Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PKG_NAME="conftune-fc"
PKG_VERSION="${PKG_VERSION:-$(PYTHONPATH="${ROOT_DIR}" python3 -c "import conftune; print(conftune.__version__)")}"
DIST_DIR="${ROOT_DIR}/dist"
RPMBUILD_DIR="${ROOT_DIR}/rpmbuild"

if command -v rpmbuild >/dev/null 2>&1; then
    RPMBUILD_BIN="$(command -v rpmbuild)"
else
    echo "Error: rpmbuild binary not found. Please install rpm-build (sudo dnf install rpm-build)." >&2
    exit 1
fi

echo "==> Using rpmbuild: ${RPMBUILD_BIN}"
echo "==> Preparing build environment for ${PKG_NAME}-${PKG_VERSION}..."

rm -rf "${RPMBUILD_DIR}"
mkdir -p "${RPMBUILD_DIR}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
mkdir -p "${DIST_DIR}"

TMP_SRC="/tmp/${PKG_NAME}-${PKG_VERSION}"
rm -rf "${TMP_SRC}"
mkdir -p "${TMP_SRC}"

cp -r "${ROOT_DIR}/conftune" "${TMP_SRC}/"
cp -r "${ROOT_DIR}/assets" "${TMP_SRC}/"
cp -r "${ROOT_DIR}/packaging" "${TMP_SRC}/"
cp "${ROOT_DIR}/main.py" "${TMP_SRC}/"
cp "${ROOT_DIR}/README.md" "${TMP_SRC}/"
cp "${ROOT_DIR}/LICENSE" "${TMP_SRC}/"
cp "${ROOT_DIR}/requirements.txt" "${TMP_SRC}/"
cp "${ROOT_DIR}/pyproject.toml" "${TMP_SRC}/"
cp "${ROOT_DIR}/conftune.desktop" "${TMP_SRC}/"

find "${TMP_SRC}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${TMP_SRC}" -name "*.pyc" -delete 2>/dev/null || true

tar -czf "${RPMBUILD_DIR}/SOURCES/${PKG_NAME}-${PKG_VERSION}.tar.gz" -C "/tmp" "${PKG_NAME}-${PKG_VERSION}"
cp "${ROOT_DIR}/packaging/conftune-fc.spec" "${RPMBUILD_DIR}/SPECS/"

echo "==> Building binary RPM package..."
"${RPMBUILD_BIN}" -ba \
    --define "_topdir ${RPMBUILD_DIR}" \
    "${RPMBUILD_DIR}/SPECS/conftune-fc.spec"

echo "==> Moving generated RPM artifacts to dist/..."
find "${RPMBUILD_DIR}/RPMS" -type f -name "*.rpm" -exec cp {} "${DIST_DIR}/" \;
find "${RPMBUILD_DIR}/SRPMS" -type f -name "*.src.rpm" -exec cp {} "${DIST_DIR}/" \;

echo "==> RPM Build Complete! Artifacts:"
ls -lh "${DIST_DIR}"/*.rpm
