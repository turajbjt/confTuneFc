#!/usr/bin/env bash
# ConfTune FC - Universal RPM Packaging Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PKG_NAME="conftune-fc"
PKG_VERSION="${PKG_VERSION:-$(PYTHONPATH="${ROOT_DIR}" python3 -c "import conftune; print(conftune.__version__)")}"
DIST_DIR="${ROOT_DIR}/dist"
RPMBUILD_DIR="${ROOT_DIR}/rpmbuild"

echo "==> ConfTune FC RPM Packaging (v${PKG_VERSION})"

# 1. Ensure raster icon hierarchy exists
echo "==> Checking application raster icons..."
for size in 16 24 32 48 64 128 256 512; do
    icon_file="${ROOT_DIR}/assets/icons/${size}x${size}/conftune-fc.png"
    if [ ! -f "${icon_file}" ]; then
        mkdir -p "${ROOT_DIR}/assets/icons/${size}x${size}"
        if command -v magick >/dev/null 2>&1; then
            magick -background none -density 384 "${ROOT_DIR}/assets/icon.svg" -resize "${size}x${size}" "${icon_file}"
        elif command -v convert >/dev/null 2>&1; then
            convert -background none -density 384 "${ROOT_DIR}/assets/icon.svg" -resize "${size}x${size}" "${icon_file}"
        fi
    fi
done

# 2. Determine RPM build tool
if command -v rpmbuild >/dev/null 2>&1; then
    RPMBUILD_BIN="$(command -v rpmbuild)"
else
    # Build or use native rpmbuild-runner using librpmbuild
    RUNNER_BIN="${SCRIPT_DIR}/rpmbuild-runner"
    if [ ! -x "${RUNNER_BIN}" ]; then
        echo "==> Compiling native librpmbuild runner..."
        gcc -O2 -o "${RUNNER_BIN}" "${SCRIPT_DIR}/rpmbuild-runner.c" -lrpm -lrpmbuild -lrpmio
    fi
    RPMBUILD_BIN="${RUNNER_BIN}"
fi

echo "==> Using RPM builder: ${RPMBUILD_BIN}"
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
cp -r "${ROOT_DIR}/docs" "${TMP_SRC}/"
cp "${ROOT_DIR}/main.py" "${TMP_SRC}/"
cp "${ROOT_DIR}/README.md" "${TMP_SRC}/"
cp "${ROOT_DIR}/LICENSE" "${TMP_SRC}/"
cp "${ROOT_DIR}/CONTRIBUTING.md" "${TMP_SRC}/"
cp "${ROOT_DIR}/requirements.txt" "${TMP_SRC}/"
cp "${ROOT_DIR}/pyproject.toml" "${TMP_SRC}/"
cp "${ROOT_DIR}/conftune.desktop" "${TMP_SRC}/"

find "${TMP_SRC}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${TMP_SRC}" -name "*.pyc" -delete 2>/dev/null || true

tar -czf "${RPMBUILD_DIR}/SOURCES/${PKG_NAME}-${PKG_VERSION}.tar.gz" -C "/tmp" "${PKG_NAME}-${PKG_VERSION}"
cp "${ROOT_DIR}/packaging/conftune-fc.spec" "${RPMBUILD_DIR}/SPECS/"

echo "==> Building universal binary RPM package..."
"${RPMBUILD_BIN}" -ba \
    --define "_topdir ${RPMBUILD_DIR}" \
    --define "_tmppath /tmp" \
    --define "dist %{nil}" \
    "${RPMBUILD_DIR}/SPECS/conftune-fc.spec"

echo "==> Moving generated RPM artifacts to dist/..."
# Purge older RPMs so only the current release artifacts exist
rm -f "${DIST_DIR}"/*.rpm "${DIST_DIR}"/SHA256SUMS

find "${RPMBUILD_DIR}/RPMS" -type f -name "*.rpm" -exec cp {} "${DIST_DIR}/" \;
find "${RPMBUILD_DIR}/SRPMS" -type f -name "*.src.rpm" -exec cp {} "${DIST_DIR}/" \;

# Generate SHA256 checksums for the current release
echo "==> Generating SHA256SUMS..."
(
    cd "${DIST_DIR}"
    sha256sum *.rpm > SHA256SUMS
    cp SHA256SUMS "${ROOT_DIR}/SHA256SUMS"
)

# Clean up build tree intermediates
rm -rf "${RPMBUILD_DIR}"

echo "==> Universal RPM Build Complete! Current Release Artifacts:"
ls -lh "${DIST_DIR}"/*.rpm
