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
        Core --> Presets[preset_manager.py: Bundles, Deploy Scripts, ISOs]
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

### 5. Fedy Post-Install & Media Engine (`conftune/core/fedy_tuner.py`)
- Automated RPM Fusion Free & Nonfree enablement.
- Comprehensive multimedia codec bundle installation (GStreamer, FFmpeg, OpenH264, VA-API).
- Subpixel RGB font rendering & LCD filter deployment.
- GNOME desktop window header buttons and battery display toggles.

---

### 6. CPU Power & Governance (`conftune/core/power_tuner.py`)
- Manages hardware energy preference hints (EPP) across AMD Zen and Intel Core CPUs.
- Dynamic CPU scaling governor controls (`performance`, `powersave`, `schedutil`).
- Transparent Huge Pages (THP) mode switcher (`always`, `madvise`, `never`).
- Power-profiles-daemon and Feral GameMode status integration.

---

### 7. Process Scheduling & OOM Protection (`conftune/core/process_tuner.py`)
- Configures `systemd-oomd` memory pressure ceilings to prevent premature task termination.
- Exposes `oom_score_adj` adjustment to protect mission-critical databases, IDEs, and desktop processes.

---

### 8. Autostart & Crash Diagnostics (`conftune/core/autostart_tuner.py`)
- Discovers and toggles login autostart launchers (`~/.config/autostart`, `/etc/xdg/autostart`).
- Caps `systemd-coredump` disk consumption in `/etc/systemd/coredump.conf.d/`.
- Controls Automatic Bug Reporting Tool (ABRT) background daemons.

---

### 9. Privacy & Telemetry Guard (`conftune/core/privacy_tuner.py`)
- 1-click opt-out from GNOME software usage statistics and automated bug transmission.
- Core dump collection disablement for privacy-conscious installations.

---

### 10. Snapshot & Rollback Engine (`conftune/core/backup_manager.py`)
- Before modifying any system target file, a snapshot directory is created under `/var/lib/conftune/backups` (or `~/.local/share/conftune/backups`).
- Stores copies of original files and writes a `metadata.json` manifest.
- Rollback re-copies original files, deletes newly generated files, and reloads `sysctl --system` and `systemctl daemon-reload`.

---

### 11. Presets, Standalone Deploy & ISO Engine (`conftune/core/preset_manager.py`)
- **System Capture & Portable Archives**: Inspects active sysctls, `/etc/dnf/dnf.conf`, journald limits, tuned profile, and CPU governors; bundles them into portable compressed `.conftune.tar.gz` archives with JSON manifests.
- **Standalone 1-File Deployment Script**: Generates self-contained Bash scripts (`deploy.sh`) containing embedded configuration payloads that can be copied over SSH and run on fresh headless machines with zero dependencies.
- **Anaconda Kickstart Generator**: Generates clean `.ks` configuration files with `%post` install directives for automated Red Hat / Fedora OS provisioning.
- **Bootable ISO Customization**: Integrates with official `mkksiso` (from `lorax`) to non-destructively inject Kickstart files into Fedora, Rocky Linux, or CentOS ISO images for bootable USB deployment.

---

### 12. Threading Model (`conftune/gui/workers.py`)
All asynchronous operations (profile application, TRIM execution, log vacuuming, ISO generation) run on background `QThread` instances using `run_async_task()`. The GUI main thread handles rendering and user interaction without blocking.
