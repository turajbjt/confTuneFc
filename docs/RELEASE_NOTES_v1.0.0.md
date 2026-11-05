# ConfTune FC v1.0.0 Release Notes

**ConfTune FC** is the premier open-source system optimization, kernel tuning, and automated deployment suite for Fedora Linux, Red Hat Enterprise Linux (RHEL), Rocky Linux, AlmaLinux, and CentOS Stream.

Designed for modern workstations, cloud servers, virtualization hosts, and gaming rigs, ConfTune FC combines a native GTK3 Adwaita Dark interface with a headless, scriptable CLI engine.

---

## 🚀 Key Features in v1.0.0

### 1. 16 Modular Optimization Tabs & Native Adwaita Dark GUI
- **Overview**: System metrics, CPU topology, kernel parameters, active profile banner.
- **Kernel / Sysctl**: Live sysctl inspection, safe parameter validation, injection prevention, and one-click presets.
- **DNF Acceleration**: Dual DNF4 (`/etc/dnf/dnf.conf`) and DNF5 (`/etc/dnf/dnf5.conf`) parallel downloads, fastest mirror ranking, and persistent cache retention.
- **Storage & ZRAM**: Real-time I/O scheduler switcher (BFQ, Kyber, mq-deadline, none), ZRAM memory compression generator, and automated fstrim timers.
- **Systemd & Boot**: `systemd-analyze` boot blame, journald log quotas, and enterprise-grade service management.
- **Power & CPU**: Live governor tuning (performance, powersave, schedutil), AMD P-State & Intel EPP control, GameMode integration, and Transparent Hugepages (THP).
- **Dynamic Power Daemon (`conftune-powerd`)**: Automated AC vs Battery state detection with automatic power profile transitions and systemd service integration.
- **Process & OOM**: `systemd-oomd` fine-tuning, swap thresholds, and process OOM score adj protector.
- **Fedy Post-Install**: RPM Fusion free/nonfree enablement, multimedia codecs (H.264, HEVC, AAC), subpixel RGB font rendering, and GNOME Tweaks.
- **Server Hardening**: FirewallD zone inspections, SELinux booleans, Tuned enterprise profile switcher, and OpenSSH CIS security auditing.
- **Privacy & Telemetry**: One-click disabling of GNOME telemetry, Fedora usage stats, and ABRT crash reporting.
- **Live System Monitor**: Real-time multi-core CPU & RAM consumption graphs.
- **Drive Health (S.M.A.R.T.)**: NVMe and SATA health reporting and temperature monitoring.
- **Autostart Manager**: Interactive desktop autostart entry auditor and toggler.
- **Profiles & Fleet Provisioning**: Custom preset manager, compressed preset archive import/export (`.conftune.tar.gz`), shell deploy scripts, Kickstart configs (`%post`), and automated Ansible Playbooks.
- **Rollback & Snapshots**: Automated differential configuration snapshots with one-click restore.
- **Real-time Diagnostic Logs**: In-app streaming audit trail with timestamps and log rotation.

### 2. Dual-Tier Privilege Isolation
- Fine-grained security model distinguishing **User-Safe** read-only analysis and user-space operations from **Privileged** system configuration.
- Privileged operations are clearly badged `[Requires Sudo]` and locked in normal user sessions with helpful elevation banners, preventing partial permission failures.

### 3. Dynamic Power & Battery Daemon (`conftune-powerd`)
- Includes `conftune-powerd.service` hardened with systemd sandboxing (`ProtectHome=read-only`, restricted write paths).
- Auto-detects AC power connection / disconnect events and seamlessly switches CPU frequency governors and EPP registers without polling overhead.

### 4. Enterprise Fleet Deployment
- **Kickstart Integration**: Generate standalone `%post` snippets for Anaconda automated OS installations.
- **Ansible Automation**: Generate self-contained Ansible playbooks (`tasks/playbook.yml`) with idempotent configuration directives.
- **Offline Shell Bundles**: Export self-contained `deploy.sh` scripts suitable for air-gapped environments.

### 5. Fedora Packaging & AppStream Specification
- Conforms to Fedora Packaging Guidelines and AppStream metadata specifications (`io.github.conftune_fc.metainfo.xml`).
- Automated RPM build pipeline (`packaging/build-rpm.sh`) generating universal `noarch.rpm` packages compatible with Fedora 40-45+, Rocky Linux 8-10, AlmaLinux, and CentOS Stream.
- Complete Fedora COPR deployment guide (`docs/COPR_GUIDE.md`).

---

## 📦 Package Artifacts & Checksums

Integrity checksums for this release can be verified using `sha256sum -c SHA256SUMS`:

```
dist/conftune-fc-1.0.0-1.noarch.rpm
dist/conftune-fc-1.0.0-1.src.rpm
```

---

## 🛠️ Quick Installation

### Fedora / Rocky Linux / RHEL / CentOS Stream
```bash
sudo dnf install ./dist/conftune-fc-1.0.0-1.noarch.rpm
```

### Running ConfTune FC
```bash
# Launch GTK3 graphical interface
conftune-fc

# Inspect system status via CLI
conftune-fc --status

# Start background dynamic power daemon
sudo systemctl enable --now conftune-powerd.service
```

---

## 🧪 Quality Assurance & Test Verification
- **113 Unit & Integration Tests**: 100% passing across CLI, Core Tuners, GTK3 GUI Tabs, Privilege Enforcement, and Fleet Provisioning.
- **AppStream Metainfo**: Validated with `appstreamcli validate --no-net` (Code 0, zero errors).
- **Code Coverage**: Complete isolation with mock safety engines and dry-run guarantees.
