# ConfTune FC Command-Line Interface (CLI) Reference 💻

ConfTune FC includes a headless CLI designed for automated deployments, container nodes, and headless Rocky Linux, CentOS Stream, and Fedora servers over SSH.

---

## 🚀 Basic Syntax

```bash
python3 main.py [OPTIONS]
# or (if installed via RPM):
conftune [OPTIONS]
```

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

### 4. DNF & Storage Maintenance

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
