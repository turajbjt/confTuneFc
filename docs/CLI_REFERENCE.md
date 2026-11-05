# ConfTune FC Command-Line Interface (CLI) Reference 💻

ConfTune FC includes a headless CLI designed for automated deployments, container nodes, and headless Rocky Linux, CentOS Stream, and Fedora servers over SSH.

---

> ### ⚠️ BETA SOFTWARE WARNING & DISCLAIMER
> ConfTune FC is **BETA** software. Executing commands with `--apply` will commit real modifications to `/etc/` and `/sys/`. **Use entirely at your own risk.** Always run operations in default simulation mode first to inspect the dry-run output, and verify that you maintain independent backups before applying changes.

---

## 🚀 Basic Syntax

```bash
python3 main.py [OPTIONS]
# or (if installed via RPM):
conftune [OPTIONS]
```

---

## 🛡️ Privilege Model & Security Guard

ConfTune FC enforces strict boundary separation between casual read-only tasks and administrative modifications:

- **`[User Safe]`**: Any unprivileged user can safely execute these commands without `sudo` (e.g. status queries, profile simulation, user font rendering, desktop tweaks, preset export, deploy script generation, Kickstart generation).
- **`[Requires Sudo]`**: Modifies protected kernel parameters in `/sys/`, daemons in `/etc/systemd/`, sysctls in `/etc/sysctl.d/`, or repositories in `/etc/dnf/`. Requires root or `sudo`.

> **Automatic Elevation Guard**: If a non-root user executes an administrative command with `--apply` (or non-dry-run actions like `--trim`, `--governor`, `--rollback`), ConfTune FC cleanly halts execution with exit code `1`, displaying the exact `sudo` command required.

---

## 📌 Command Reference

### 1. System Status & Inspection

#### `--status`
Profiles the host system and prints an overview of operating system, kernel, hardware topology, desktop vs server role, active tuned profile, and specialized stack status (Containers, Virtualization, Virtualmin).

```bash
conftune --status
```

#### `--list-profiles`
Displays all available performance profiles with categories, descriptions, and recommended daemon settings.

```bash
conftune --list-profiles
```

---

### 2. Applying Tuning Profiles

ConfTune FC operates in **simulation mode (dry-run)** by default unless `--apply` is explicitly passed.

```bash
# Simulate applying the Fedora Desktop Workstation profile:
conftune --profile workstation

# Permanently apply the Workstation profile:
sudo conftune --profile workstation --apply

# Permanently apply the Gaming & Low Latency profile:
sudo conftune --profile gaming --apply

# Permanently apply the General Enterprise Server profile:
sudo conftune --profile server --apply

# Permanently apply the High-Throughput Web / API Server profile:
sudo conftune --profile web_server --apply

# Permanently apply the Database Server profile:
sudo conftune --profile database --apply
```

---

### 3. Specialized Stack Configurations

#### `--tune-containers`
Configures host kernel parameters and persistent modules for Docker and Podman container hosts:
- Enables `net.ipv4.ip_forward = 1` and `net.ipv6.conf.all.forwarding = 1`
- Persists `br_netfilter` and `overlay` module loading in `/etc/modules-load.d/conftune-containers.conf`
- Sets `fs.inotify.max_user_watches = 1048576` and `fs.inotify.max_user_instances = 8192`
- Scales `kernel.pid_max = 4194304` to prevent PID exhaustion in dense containers

```bash
# Dry run:
conftune --tune-containers

# Apply:
sudo conftune --tune-containers --apply
```

#### `--tune-virt`
Configures bare-metal Rocky, CentOS, or Fedora hypervisors:
- Sets Red Hat tuned profile to `virtual-host`
- Enables KSM (Kernel Samepage Merging) memory deduplication daemon (`ksmtuned`)
- Enables network bridge proxy ARP for virtual tap routing
- Sets `vm.swappiness = 1` to protect virtual machine allocations from host swapping

```bash
# Dry run:
conftune --tune-virt

# Apply:
sudo conftune --tune-virt --apply
```

#### `--tune-virtualmin`
Optimizes multi-tenant hosting servers running Virtualmin & Webmin:
- Configures firewalld to ensure port `10000/tcp` (Webmin) is open
- Tunes socket connection backlogs (`net.core.somaxconn = 65535`, `net.ipv4.tcp_max_syn_backlog = 16384`)
- Enables rapid TIME_WAIT socket recycling (`net.ipv4.tcp_tw_reuse = 1`)
- Shortens TCP FIN timeouts to 15 seconds to prevent connection starvation

```bash
# Dry run:
conftune --tune-virtualmin

# Apply:
sudo conftune --tune-virtualmin --apply
```

---

### 4. Fedy Essentials, Codecs & Desktop Tweaks

#### `--fedy-codecs`
Installs RPM Fusion Free & Nonfree repositories, followed by comprehensive multimedia codecs: GStreamer plugins (ugly, bad, libav), OpenH264, FFmpeg, and VA-API hardware video acceleration.
```bash
sudo conftune --fedy-codecs --apply
```

#### `--fedy-fonts`
Deploys subpixel RGB antialiasing and slight LCD filtering configuration to `~/.config/fontconfig/fonts.conf` for maximum typography clarity.
```bash
conftune --fedy-fonts
```

---

### 5. CPU Power, Governor & Energy Management

#### `--governor <GOVERNOR>`
Applies a CPU scaling governor (`performance`, `powersave`, `schedutil`, `ondemand`) across all available CPU cores.
```bash
# Dry run:
conftune --governor performance

# Apply:
sudo conftune --governor performance --apply
```

#### `--epp <MODE>`
Sets CPU Energy Performance Preference (`performance`, `balance_performance`, `balance_power`, `power`) across all modern AMD Zen and Intel Core cores.
```bash
sudo conftune --epp performance --apply
```

#### `--thp <MODE>`
Configures Transparent Huge Pages (THP) mode (`always`, `madvise`, `never`).
```bash
sudo conftune --thp madvise --apply
```

---

### 6. Process Scheduling & OOM Defense

#### `--protect-process <NAME> [--oom-score <SCORE>]`
Protects a critical daemon from Linux Out-Of-Memory termination by adjusting `oom_score_adj` (default -500; -1000 is completely immune).
```bash
sudo conftune --protect-process postgres --oom-score -500 --apply
sudo conftune --protect-process code --oom-score -200 --apply
```

#### `--tune-oomd`
Configures `/etc/systemd/oomd.conf.d/99-conftune.conf` with balanced memory pressure and swap thresholds to prevent premature desktop app kills.
```bash
sudo conftune --tune-oomd --apply
```

---

### 7. Autostart, Privacy & Diagnostics

#### `--list-autostart`
Discovers and lists all user and system login autostart applications (`~/.config/autostart`, `/etc/xdg/autostart`).
```bash
conftune --list-autostart
```

#### `--disable-telemetry`
Enforces strict privacy: disables GNOME Software usage statistics, crash reporting, and external problem telemetry.
```bash
conftune --disable-telemetry
```

#### `--drive-health`
Queries storage devices (NVMe & SATA SSDs) for SMART health status and wear assessment.
```bash
sudo conftune --drive-health
```

---

### 8. DNF & Storage Maintenance

#### `--tune-dnf`
Accelerates package manager operations by updating `/etc/dnf/dnf.conf` with:
- `max_parallel_downloads = 10`
- `fastestmirror = True`
- `defaultyes = True`
- `keepcache = True`

```bash
sudo conftune --tune-dnf --apply
```

#### `--trim`
Executes an immediate manual discard operation (`fstrim -av`) across all mounted SSD and NVMe filesystems.

```bash
sudo conftune --trim
```

---

### 5. Snapshots & Rollback

#### `--snapshots`
Lists all available configuration snapshots recorded before tuning sessions, including timestamp, profile name, and number of tracked files.

```bash
conftune --snapshots
```

#### `--rollback <SNAPSHOT_ID>`
Restores original configuration files from a specific snapshot ID and cleans up newly generated overrides.

```bash
# Dry run simulation:
conftune --rollback snap_20261103_211334_server

# Permanent rollback:
sudo conftune --rollback snap_20261103_211334_server --apply
```

---

### 9. Presets, Standalone Scripts & ISO Deployment

#### `--export-preset <FILE>`
Captures active host tuning (sysctls, DNF settings, journald cap, tuned profile, CPU governor) and packages it into a portable, compressed archive (`.conftune.tar.gz`).

```bash
conftune --export-preset /tmp/my-fedora-workstation.conftune.tar.gz
```

#### `--import-preset <FILE>`
Imports and applies a `.conftune.tar.gz` preset archive to the target machine. Creates pre-tune snapshots before writing. Runs in dry-run mode by default unless `--apply` is specified.

```bash
# Preview changes:
conftune --import-preset /tmp/my-fedora-workstation.conftune.tar.gz

# Apply to machine:
sudo conftune --import-preset /tmp/my-fedora-workstation.conftune.tar.gz --apply
```

#### `--export-deploy-script <FILE>`
Generates a standalone, self-contained `deploy.sh` script containing all active sysctls and DNF tuning parameters. The resulting script requires zero dependencies and can be run directly on any fresh server via SSH.

```bash
# Generate script:
conftune --export-deploy-script /tmp/deploy-webserver.sh

# Deploy to remote host:
scp /tmp/deploy-webserver.sh admin@192.168.1.150:/tmp/
ssh admin@192.168.1.150 "sudo bash /tmp/deploy-webserver.sh"
```

#### `--export-kickstart <FILE>`
Generates an automated Red Hat / Fedora Kickstart (`.ks`) post-install snippet containing `%post` script hooks to automatically tune fresh OS installations.

```bash
conftune --export-kickstart /tmp/conftune-postinstall.ks
```

#### `--build-iso --base-iso <ISO> --output-iso <ISO>`
Injects a Kickstart file into an official Fedora Workstation/Server, Rocky Linux, or CentOS Stream ISO image using `mkksiso` (from package `lorax`). The resulting ISO can be flashed to a USB drive for hands-off, auto-tuned installations.

```bash
# Inject kickstart into official ISO:
conftune --build-iso \
    --base-iso Fedora-Workstation-Live-x86_64-44.iso \
    --output-iso Fedora-44-ConfTune-Automated.iso
```

---

## 🤖 Automation & CI/CD Examples

### Automated Server Bootstrap (Cloud-Init / Bash Script)
```bash
#!/bin/bash
set -e

# Clone and tune
git clone https://github.com/turajbjt/confTuneFc.git /opt/confTuneFc
cd /opt/confTuneFc

# Apply Enterprise Server profile & DNF acceleration:
python3 main.py --profile server --apply
python3 main.py --tune-dnf --apply
```
