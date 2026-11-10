#!/usr/bin/env bash
# ConfTune FC - Universal RPM Packaging Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PKG_NAME="conftune-fc"
PKG_VERSION="${PKG_VERSION:-$(PYTHONPATH="${ROOT_DIR}" python3 -c "import conftune; print(conftune.__version__)")}"
RPMBUILD_DIR="${ROOT_DIR}/rpmbuild"
DIST_DIR="${ROOT_DIR}/dist"

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
        RPM_LIBS=""
        for lib in /usr/lib64/librpm.so* /usr/lib64/librpmbuild.so* /usr/lib64/librpmio.so*; do
            if [ -f "$lib" ] && [[ "$lib" =~ \.so\.[0-9]+$ ]]; then
                RPM_LIBS="$RPM_LIBS $lib"
            fi
        done
        if [ -z "$RPM_LIBS" ]; then
            RPM_LIBS="-lrpm -lrpmbuild -lrpmio"
        fi
        gcc -O2 -o "${RUNNER_BIN}" "${SCRIPT_DIR}/rpmbuild-runner.c" ${RPM_LIBS}
    fi
    RPMBUILD_BIN="${RUNNER_BIN}"
fi

echo "==> Using RPM builder: ${RPMBUILD_BIN}"
echo "==> Preparing build environment for ${PKG_NAME}-${PKG_VERSION}..."

rm -rf "${RPMBUILD_DIR}"
mkdir -p "${RPMBUILD_DIR}"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

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

echo "==> Building universal binary and source RPM packages..."
"${RPMBUILD_BIN}" -ba \
    --define "_topdir ${RPMBUILD_DIR}" \
    --define "_tmppath /tmp" \
    --define "dist %{nil}" \
    "${RPMBUILD_DIR}/SPECS/conftune-fc.spec"

# Find generated RPMs
RPM_FILE="$(find "${RPMBUILD_DIR}/RPMS" -name "*.rpm" | head -n 1)"
SRPM_FILE="$(find "${RPMBUILD_DIR}/SRPMS" -name "*.src.rpm" | head -n 1)"

if [ -z "${RPM_FILE}" ] || [ ! -f "${RPM_FILE}" ]; then
    echo "Error: RPM build failed to produce a binary rpm package." >&2
    exit 1
fi

RPM_FILENAME="$(basename "${RPM_FILE}")"

# Purge any older RPMs in root to ensure only the latest unified RPMs exist
find "${ROOT_DIR}" -maxdepth 1 -name "conftune-fc-*.noarch.rpm" ! -name "${RPM_FILENAME}" -delete 2>/dev/null || true
cp "${RPM_FILE}" "${ROOT_DIR}/${RPM_FILENAME}"

SRPM_FILENAME=""
if [ -n "${SRPM_FILE}" ] && [ -f "${SRPM_FILE}" ]; then
    SRPM_FILENAME="$(basename "${SRPM_FILE}")"
    find "${ROOT_DIR}" -maxdepth 1 -name "conftune-fc-*.src.rpm" ! -name "${SRPM_FILENAME}" -delete 2>/dev/null || true
    cp "${SRPM_FILE}" "${ROOT_DIR}/${SRPM_FILENAME}"
fi

# Clean up legacy dist/ directory if present
rm -rf "${DIST_DIR}"

# Generate SHA256 checksums
echo "==> Generating SHA256SUMS..."
cd "${ROOT_DIR}"
if [ -n "${SRPM_FILENAME}" ]; then
    sha256sum "${RPM_FILENAME}" "${SRPM_FILENAME}" > "${ROOT_DIR}/SHA256SUMS"
else
    sha256sum "${RPM_FILENAME}" > "${ROOT_DIR}/SHA256SUMS"
fi

# Clean up build tree intermediates so only the current release artifacts are retained
rm -rf "${RPMBUILD_DIR}"

echo ""
echo "============================================================"
echo "  RPM BUILD SUCCESSFUL!"
echo "  Binary Package: ${ROOT_DIR}/${RPM_FILENAME}"
if [ -n "${SRPM_FILENAME}" ]; then
    echo "  Source Package: ${ROOT_DIR}/${SRPM_FILENAME}"
fi
echo "============================================================"
echo ""
echo "To install binary package on your system:"
echo "  sudo dnf install ./${RPM_FILENAME}"
echo "  # or:"
echo "  sudo rpm -ivh ./${RPM_FILENAME}"
if [ -n "${SRPM_FILENAME}" ]; then
    echo ""
    echo "To rebuild from source RPM:"
    echo "  rpmbuild --rebuild ./${SRPM_FILENAME}"
fi
echo ""
echo "Package Details:"
rpm -qip "${ROOT_DIR}/${RPM_FILENAME}"
echo ""
echo "Package File List:"
rpm -qlp "${ROOT_DIR}/${RPM_FILENAME}"
