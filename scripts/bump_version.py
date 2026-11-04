#!/usr/bin/env python3
"""
ConfTune FC - Automatic Version Management Script.
Synchronizes SemVer across:
  - conftune/__init__.py
  - pyproject.toml
  - packaging/conftune-fc.spec (%changelog and Version)
  - README.md
Optionally rebuilds the RPM package immediately.
"""

import argparse
import datetime
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) == "scripts" else SCRIPT_DIR


def get_current_version() -> str:
    init_path = os.path.join(ROOT_DIR, "conftune", "__init__.py")
    with open(init_path, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not m:
        raise ValueError("Could not find __version__ in conftune/__init__.py")
    return m.group(1)


def parse_semver(version_str: str):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str.strip())
    if not m:
        raise ValueError(f"Invalid SemVer string: {version_str}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def calculate_next_version(current: str, bump_type: str) -> str:
    major, minor, patch = parse_semver(current)
    bump_lower = bump_type.lower()
    if bump_lower == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif bump_lower == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_lower == "major":
        return f"{major + 1}.0.0"
    else:
        parse_semver(bump_type)
        return bump_type


def update_init_py(new_version: str):
    path = os.path.join(ROOT_DIR, "conftune", "__init__.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    updated = re.sub(r'__version__\s*=\s*["\'][^"\']+["\']', f'__version__ = "{new_version}"', content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"  ✓ Updated conftune/__init__.py -> {new_version}")


def update_pyproject_toml(new_version: str):
    path = os.path.join(ROOT_DIR, "pyproject.toml")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    updated = re.sub(r'version\s*=\s*["\'][^"\']+["\']', f'version = "{new_version}"', content, count=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"  ✓ Updated pyproject.toml -> {new_version}")


def update_spec_file(new_version: str, message: str, author: str = "James Turansky <turajb@gmail.com>"):
    path = os.path.join(ROOT_DIR, "packaging", "conftune-fc.spec")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    updated = re.sub(r"^Version:\s+.*$", f"Version:        {new_version}", content, flags=re.MULTILINE)
    updated = re.sub(r"^Release:\s+\d+", "Release:        1", updated, flags=re.MULTILINE)

    today = datetime.datetime.now().strftime("%a %b %d %Y")
    changelog_entry = f"* {today} {author} - {new_version}-1\n- {message}\n"
    if "%changelog" in updated:
        parts = updated.split("%changelog", 1)
        updated = f"{parts[0]}%changelog\n{changelog_entry}{parts[1].lstrip()}"

    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"  ✓ Updated packaging/conftune-fc.spec -> {new_version}")


def main():
    parser = argparse.ArgumentParser(description="ConfTune FC SemVer Bump Script")
    parser.add_argument("bump", nargs="?", default="patch", help="patch, minor, major, or explicit X.Y.Z")
    parser.add_argument("-m", "--message", default="Release update", help="Changelog message")
    parser.add_argument("--build-rpm", action="store_true", help="Build RPM package immediately after bumping")
    args = parser.parse_args()

    curr = get_current_version()
    next_ver = calculate_next_version(curr, args.bump)
    print(f"==> Bumping version: {curr} -> {next_ver}")

    update_init_py(next_ver)
    update_pyproject_toml(next_ver)
    update_spec_file(next_ver, args.message)

    if args.build_rpm:
        build_script = os.path.join(ROOT_DIR, "packaging", "build-rpm.sh")
        if os.path.isfile(build_script):
            print("\n==> Launching RPM build script...")
            subprocess.run([build_script], check=True)


if __name__ == "__main__":
    main()
