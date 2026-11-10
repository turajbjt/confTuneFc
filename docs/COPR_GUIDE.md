# Fedora COPR Deployment & Packaging Guide

This guide details how to build, publish, and maintain **ConfTune FC** on [Fedora COPR](https://copr.fedorainfracloud.org/) (Cool Other Package Repo), as well as how end-users on Fedora, EPEL, Rocky Linux, AlmaLinux, and CentOS Stream install and update ConfTune FC.

---

## 1. Overview

Fedora COPR provides automated build infrastructure for RPM-based distributions. Because ConfTune FC is packaged as an architecture-independent (`noarch`) RPM conforming strictly to Fedora Packaging Guidelines, a single source RPM (`.src.rpm`) builds cleanly across all active Fedora and Enterprise Linux targets.

### Supported Chroots:
- **Fedora**: `fedora-40-x86_64`, `fedora-41-x86_64`, `fedora-42-x86_64`, `fedora-rawhide-x86_64`, `fedora-rawhide-aarch64`
- **Enterprise Linux (EPEL)**: `epel-8-x86_64`, `epel-9-x86_64`, `epel-10-x86_64` (Rocky Linux, AlmaLinux, RHEL, CentOS Stream)

---

## 2. Prerequisites for Maintainers

1. **Fedora Account**: An active [Fedora Accounts System (FAS)](https://accounts.fedoraproject.org/) account.
2. **COPR CLI**:
   ```bash
   sudo dnf install -y copr-cli
   ```
3. **COPR API Token**:
   - Log into https://copr.fedorainfracloud.org/api/
   - Copy the API configuration into `~/.config/copr`.

---

## 3. Creating the COPR Project

Maintainers can create the project via the COPR Web UI or CLI:

```bash
copr-cli create conftune-fc \
  --chroot fedora-40-x86_64 \
  --chroot fedora-41-x86_64 \
  --chroot fedora-42-x86_64 \
  --chroot fedora-rawhide-x86_64 \
  --chroot epel-8-x86_64 \
  --chroot epel-9-x86_64 \
  --chroot epel-10-x86_64 \
  --description "Enterprise & Workstation Linux Optimizer for Fedora, Rocky, AlmaLinux, and CentOS Stream." \
  --instructions "Install with: dnf copr enable <username>/conftune-fc && dnf install conftune-fc"
```

---

## 4. Building from Source RPM (SRPM)

### Step 1: Generate the Source RPM locally
Using the automated build script in the repository:
```bash
./packaging/build-rpm.sh
```
This produces:
- `conftune-fc-1.0.5-1.src.rpm` (Source RPM)
- `conftune-fc-1.0.5-1.noarch.rpm` (Local binary RPM)
- `SHA256SUMS` (Integrity checksums)

### Step 2: Submit the Build to COPR
```bash
copr-cli build conftune-fc conftune-fc-1.0.5-1.src.rpm
```
You can monitor the build status in real-time:
```bash
copr-cli monitor conftune-fc
```

---

## 5. Automated Git SCM Builds (Continuous Delivery)

COPR can automatically build new releases directly from GitHub when a tag is pushed:

1. Open your project on https://copr.fedorainfracloud.org/
2. Navigate to **Packages** -> **New Package**
3. Set **Package Name**: `conftune-fc`
4. Set **Source Type**: `SCM`
5. Configure SCM settings:
   - **Clone URL**: `https://github.com/your-org/confTuneFc.git`
   - **Committish**: `main` (or tag format `v*`)
   - **Spec file path**: `packaging/conftune-fc.spec`
   - **Source build method**: `tmt` or `rpkg` / `make_srpm`
6. Under **Webhooks**, copy the rebuild webhook URL and add it to your GitHub repository under **Settings -> Webhooks** (trigger on `Release` or `Push`).

---

## 6. End-User Installation Instructions

### Fedora Workstation / Silverblue / Server (Fedora 40+)
```bash
# Enable the COPR repository
sudo dnf copr enable <username>/conftune-fc -y

# Install ConfTune FC
sudo dnf install conftune-fc -y
```

*(On Fedora Silverblue / Kinoite / Atomic Desktop)*:
```bash
sudo rpm-ostree install --apply-live conftune-fc
```

### RHEL, Rocky Linux, AlmaLinux & CentOS Stream (EL 8 / 9 / 10)
```bash
# Ensure EPEL and DNF plugins are enabled
sudo dnf install -y epel-release dnf-plugins-core

# Enable COPR repository
sudo dnf copr enable <username>/conftune-fc -y

# Install ConfTune FC
sudo dnf install conftune-fc -y
```

---

## 7. Starting the Dynamic Power Daemon

ConfTune FC includes the `conftune-powerd` background service which automatically switches CPU governors and Energy Performance Preference (EPP) between AC and Battery modes.

```bash
# Enable and start the systemd service
sudo systemctl enable --now conftune-powerd.service

# Check service status and active power state
sudo systemctl status conftune-powerd.service
```

---

## 8. Verifying Package & Metainfo Compliance

Before submitting builds, verify that metadata conforms to the AppStream specification:
```bash
appstreamcli validate --no-net assets/io.github.conftune_fc.metainfo.xml
```
Verify RPM package integrity:
```bash
rpm -Kv conftune-fc-*.noarch.rpm
```
