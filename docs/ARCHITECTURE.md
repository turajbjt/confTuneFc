# ConfTune FC Architecture & Design Specification 🏛️

ConfTune FC is engineered to provide safe, deterministic, and workload-tailored system tuning across modern RPM distributions. This document outlines the internal architecture, threading model, subsystem components, and configuration lifecycle.

---

## 🏗️ High-Level System Architecture

```mermaid
flowchart TD
    User([User / Administrator]) --> Main{main.py}

    subgraph Entrypoint & Execution
        Main -->|Display Available| GUI[PyQt6 Adwaita GUI]
        Main -->|Headless / CLI Flag| CLI[Headless CLI conftune.cli]
    end

    subgraph Core Subsystems
        GUI --> Core[Core Engine]
        CLI --> Core

        Core --> Detector[detector.py: OS, HW & Stack Profiling]
        Core --> Profiles[profiles.py: Workload Presets]
        Core --> Sysctl[sysctl_tuner.py: /etc/sysctl.d/99-conftune.conf]
        Core --> DNF[dnf_tuner.py: /etc/dnf/dnf.conf]
        Core --> Systemd[systemd_tuner.py: Blame, Services, journald]
        Core --> Storage[storage_tuner.py: TRIM, Schedulers, ZRAM]
        Core --> Server[server_tuner.py: tuned-adm, Firewalld, SELinux, SSH]
    end

    subgraph Safety & State Management
        Core --> Safety[safety.py: Privilege Checks & Sanitization]
        Core --> Backup[backup_manager.py: Snapshots & Rollback Engine]
        Core --> Logger[logger.py: Rotating Disk & UI Signal Stream]
    end

    subgraph System Target Files
        Sysctl --> F1[/etc/sysctl.d/99-conftune.conf]
        DNF --> F2[/etc/dnf/dnf.conf]
        Systemd --> F3[/etc/systemd/journald.conf.d/99-conftune.conf]
        Storage --> F4[/etc/systemd/zram-generator.conf]
        Server --> F5[tuned-adm active profile]
    end
```

---

## 🧩 Subsystem Breakdown

### 1. Hardware & Environment Intelligence (`conftune/core/detector.py`)
Profiles the host system using non-destructive inspection:
- **Operating System**: Reads `/etc/os-release` to identify distribution flavor (Fedora, Rocky Linux, CentOS Stream, AlmaLinux, RHEL) and architecture.
- **Role Detection**: Checks `$WAYLAND_DISPLAY`, `$DISPLAY`, `$XDG_CURRENT_DESKTOP`, and installed desktop binaries (`gnome-shell`, `kwin`) to classify system as a desktop workstation or headless server.
- **Hardware Topology**:
  - CPU: Model, logical thread count, frequency scaling governor.
  - Memory: Total RAM, available RAM, swap total, and active ZRAM devices.
  - Storage: Block devices via `lsblk -J`, rotational status (`ROTA=0` for SSD/NVMe vs `1` for HDD), and root filesystem type (Btrfs, XFS, ext4).
  - Virtualization: Hypervisor detection via `systemd-detect-virt` (KVM, VMware, QEMU, bare-metal).
- **Specialized Stacks**:
  - Virtualmin / Webmin: Checks `/etc/webmin` and related daemons (Apache/Nginx, MariaDB, Postfix, Dovecot, BIND).
  - Containers: Discovers Podman and Docker binaries, checks `net.ipv4.ip_forward`, and verifies `/etc/subuid` mappings.
  - Virtualization Host: Inspects `/dev/kvm`, `libvirtd`, and KSM kernel support.

---

### 2. Kernel Sysctl Engine (`conftune/core/sysctl_tuner.py`)
- Maintains a parameter catalog with descriptions, categories, default values, and safety boundaries.
- Reads runtime values from `/proc/sys/*` or `sysctl -n`.
- Generates `/etc/sysctl.d/99-conftune.conf` with categorized comments.
- Applies parameters live using `sysctl -p /etc/sysctl.d/99-conftune.conf`.

---

### 3. DNF Package Manager Accelerator (`conftune/core/dnf_tuner.py`)
- Configures `/etc/dnf/dnf.conf` using Python's `configparser`.
- Automatically works across DNF4 (Rocky 8/9, CentOS 9) and modern DNF5 (Fedora 41/44/45+).
- Optimizes `max_parallel_downloads=10`, `fastestmirror=True`, `defaultyes=True`, and `keepcache=True`.

---

### 4. Storage & ZRAM Optimizer (`conftune/core/storage_tuner.py`)
- Checks and activates `fstrim.timer` to schedule weekly TRIM discards.
- Inspects `/sys/block/*/queue/scheduler` and provides fine-grained control over I/O schedulers (`none`, `mq-deadline`, `bfq`).
- Generates `/etc/systemd/zram-generator.conf` with modern `zstd` compression.

---

### 5. Snapshot & Rollback Engine (`conftune/core/backup_manager.py`)
- Before modifying any system target file, a snapshot directory is created under `/var/lib/conftune/backups` (or `~/.local/share/conftune/backups`).
- Stores copies of original files and writes a `metadata.json` manifest.
- Rollback re-copies original files, deletes newly generated files, and reloads `sysctl --system` and `systemctl daemon-reload`.

---

### 6. Threading Model (`conftune/gui/workers.py`)
All asynchronous operations (profile application, TRIM execution, log vacuuming) run on background `QThread` instances using `run_async_task()`. The GUI main thread handles rendering and user interaction without blocking.
