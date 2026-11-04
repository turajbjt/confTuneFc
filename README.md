# ConfTune FC ⚡
### Fedora, Rocky Linux & CentOS System Setup, Configuration & Performance Tuner

[![Linux](https://img.shields.io/badge/Platform-Fedora%20%7C%20Rocky%20%7C%20CentOS%20%7C%20RHEL-blue?logo=fedora)](https://getfedora.org)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![GUI](https://img.shields.io/badge/GUI-PyQt6%20Adwaita-3584e4?logo=qt)](https://pypi.org/project/PyQt6/)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Safety](https://img.shields.io/badge/Safety-Pre--Tune%20Snapshots%20%26%201--Click%20Rollback-26a269)](#safety--snapshots)

**ConfTune FC** is a safety-first configuration, setup, and performance tuning application designed specifically for RPM-based Linux distributions, including **Fedora Workstation & Server** (Fedora 40, 41, 44, 45+), **Rocky Linux** (8, 9, 10), and **CentOS Stream / RHEL**.

ConfTune FC bridges the gap between desktop workstations and headless server nodes, featuring both a modern **GNOME 45+ Adwaita Dark GUI** and a full-featured **headless CLI** for remote SSH administration.

---

## 🌟 Key Highlights

- **Desktop & Server Role Awareness**: Automatically distinguishes between desktop workstations (GNOME/KDE/Wayland) and headless rack/cloud server nodes.
- **Tailored Tuning Presets**: Workstation, Gaming/Proton low-latency, Enterprise Server, High-Concurrency Web/API, Database I/O, Container Host (Docker/Podman), KVM Hypervisor, and Virtualmin / Webmin hosting.
- **Kernel & Sysctl Engine**: Automatically manages `/etc/sysctl.d/99-conftune.conf` with documented impact, safety bounds, and live application.
- **DNF Package Manager Accelerator**: Accelerates DNF4 and DNF5 downloads by configuring multi-threaded parallel downloads (`max_parallel_downloads=10`), fastest mirrors, and cache retention.
- **Systemd Boot Optimizer**: Analyzes `systemd-analyze blame` bottlenecks and optimizes background daemons.
- **Journald Log Cap**: Safely restricts systemd journal storage (`SystemMaxUse=200M`/`300M`/`500M`) to stop unbounded log growth.
- **Storage & NVMe/SSD Discard**: Automates weekly background SSD TRIM (`fstrim.timer`), inspects block device I/O schedulers, and tunes ZRAM compressed swap.
- **Specialized Server Stacks**:
  - **Virtualmin & Webmin**: Multi-tenant hosting, firewall port 10000, high socket backlogs (`somaxconn=65535`), and rapid socket recycling.
  - **Docker & Podman**: Kernel packet forwarding (`net.ipv4.ip_forward=1`), `br_netfilter` module persistence, and inotify watcher expansion (1,048,576).
  - **KVM & Libvirt Virtualization**: Tuned `virtual-host` profile, KSM (Kernel Samepage Merging) memory deduplication, and reduced swappiness.
- **Automatic Pre-Tune Snapshots & Rollback**: Every change creates a timestamped snapshot with JSON metadata. Revert any change with **1-click rollback**.
- **Dual Mode (GUI & Headless CLI)**: Beautiful Adwaita UI for desktop users; clean, non-interactive CLI with `--dry-run` and `--apply` flags for server administrators.

---

## 🎯 Tuning Presets Catalog

| Profile ID | Profile Name | Target Environment | Key Optimizations |
| :--- | :--- | :--- | :--- |
| `workstation` | **Fedora Desktop / Workstation** | Fedora Desktop (GNOME/KDE) | UI responsiveness, lower swappiness (`15`), dirty ratios (`5/15`), BBR TCP congestion, 512k inotify watches. |
| `gaming` | **Gaming & Low Latency** | Desktop Workstation | `vm.max_map_count=2147483642` (essential for Steam/Proton/Wine), `split_lock_mitigate=0`, low scheduling jitter. |
| `server` | **General Enterprise Server** | Rocky Linux, CentOS, Fedora Server | High connection backlogs (`somaxconn=32768`), TCP keepalives, `throughput-performance` tuned profile, 2M open file descriptors. |
| `web_server` | **High-Throughput Web / API** | Nginx, Caddy, Node, Go, Microservices | `somaxconn=65535`, 16MB socket TCP buffer ceilings, BBR congestion control, fast `tcp_tw_reuse`. |
| `database` | **Database & Heavy I/O** | PostgreSQL, MariaDB, Redis | `vm.swappiness=1` (protects DB buffer pool), dirty background ratio `3%` for smooth writeback. |
| `container_host` | **Docker & Podman Host** | Container Nodes / Dev | `net.ipv4.ip_forward=1`, `br_netfilter` module load, 1M inotify watches, doubled PID limits (`4194304`). |
| `virtualization_host` | **KVM / Libvirt Hypervisor** | Bare-Metal VM Hosts | `virtual-host` tuned profile, KSM memory deduplication active, network bridge proxy ARP. |
| `virtualmin` | **Virtualmin / Webmin Hosting** | Multi-Tenant Hosting | Port 10000 firewall configuration, scaled Apache/Nginx + PHP-FPM socket queues, MariaDB read-ahead. |
| `balanced` | **Balanced Default** | Everyday Computing | Safe baseline optimizations for everyday general use. |

---

## 🚀 Quick Start & Installation

### Requirements
- **Fedora 40/41/44/45+**, **Rocky Linux 8/9/10**, or **CentOS Stream 9/10**
- Python 3.9+
- `python3-pyqt6` (required for graphical interface; CLI runs on standard Python standard library)

### Install Dependencies
```bash
# Fedora / Rocky Linux / CentOS Stream / RHEL:
sudo dnf install python3-pyqt6
```

### Run ConfTune FC
```bash
# Clone the repository
git clone https://github.com/turajbjt/confTuneFc.git
cd confTuneFc

# Launch Graphical Desktop Interface:
python3 main.py

# Or install desktop launcher into your GNOME / KDE Application Menu:
./install-desktop.sh
```

---

## 💻 Headless Server & CLI Usage

ConfTune FC works completely headless over SSH on remote Rocky Linux, CentOS, or Fedora servers.

```bash
# Check host hardware, role, and performance score:
python3 main.py --status

# List all available workload tuning profiles:
python3 main.py --list-profiles

# Simulate applying the Enterprise Server profile (dry run - safe without root):
python3 main.py --profile server

# Apply Enterprise Server profile permanently:
sudo python3 main.py --profile server --apply

# Accelerate DNF package manager (multi-threaded downloads + fastest mirror):
sudo python3 main.py --tune-dnf --apply

# Optimize Docker & Podman container host stack:
sudo python3 main.py --tune-containers --apply

# Optimize KVM / Libvirt virtualization hypervisor:
sudo python3 main.py --tune-virt --apply

# Optimize Virtualmin & Webmin hosting server:
sudo python3 main.py --tune-virtualmin --apply

# Trigger SSD/NVMe TRIM discard:
sudo python3 main.py --trim

# View configuration snapshot history:
python3 main.py --snapshots

# Roll back system configuration to a previous snapshot:
sudo python3 main.py --rollback <SNAPSHOT_ID> --apply
```

---

## 🛡️ Safety Architecture & Rollback Engine

Modifying low-level system settings should never be risky. ConfTune FC enforces multi-tiered safety:

1. **Pre-Tune Snapshots**: Before modifying `/etc/sysctl.d/99-conftune.conf`, `/etc/dnf/dnf.conf`, `/etc/systemd/journald.conf.d/`, or `/etc/systemd/zram-generator.conf`, original copies are archived with metadata into `/var/lib/conftune/backups` (or `~/.local/share/conftune/backups`).
2. **Simulation Mode (Dry Run)**: All CLI commands and GUI buttons support a dry run mode (`--dry-run`) allowing administrators to inspect exact file diffs before committing changes.
3. **1-Click Rollback**: Any previous state can be restored instantly via the GUI **Snapshots & Rollback** tab or via `conftune --rollback <SNAPSHOT_ID>`. Newly created files are cleaned up and original files are restored with automatic sysctl/systemd reloads.

---

## 📦 RPM Packaging

To build a native `.rpm` package for Fedora, Rocky Linux, or CentOS Stream:

```bash
# Install rpm-build tools
sudo dnf install rpm-build

# Build binary and source RPMs
./packaging/build-rpm.sh

# Install generated RPM
sudo dnf install dist/conftune-fc-*.noarch.rpm
```

---

## 👥 Authors & License

- **Author**: James Turansky (`turajb@gmail.com`)
- **License**: [GNU General Public License v3.0 or later (GPL-3.0-or-later)](LICENSE)
- **Sister Application**: [ConfClean FC](https://github.com/turajbjt/confCleanFc)
