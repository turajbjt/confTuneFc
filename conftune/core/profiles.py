"""
Tuning Profiles Catalog for ConfTune FC.
Defines optimized presets for Fedora Desktop, Gaming, Enterprise Servers (Rocky/CentOS),
Web Servers, Database Servers, Docker/Podman Hosts, Virtualization Hosts, and Virtualmin.
"""

from typing import Any, Dict, List, Optional


PROFILES: Dict[str, Dict[str, Any]] = {
    "balanced": {
        "id": "balanced",
        "name": "Balanced Default",
        "category": "General",
        "description": "Safe, balanced configuration suitable for daily desktop or light server usage.",
        "icon": "⚖️",
        "tuned_profile": "balanced",
        "journald_max": "300M",
        "sysctl": {
            "vm.swappiness": "30",
            "vm.vfs_cache_pressure": "100",
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr",
            "fs.file-max": "1048576",
        },
        "dnf_settings": {
            "max_parallel_downloads": 10,
            "fastestmirror": True,
            "defaultyes": True,
            "keepcache": True,
        },
        "notes": "Good baseline for standard workloads without aggressive memory or network caching.",
    },

    "workstation": {
        "id": "workstation",
        "name": "Fedora Desktop / Workstation",
        "category": "Desktop",
        "description": "Optimized for desktop responsiveness, low UI stutter, fast DNF packages, and efficient ZRAM usage.",
        "icon": "💻",
        "tuned_profile": "desktop",
        "journald_max": "200M",
        "sysctl": {
            "vm.swappiness": "15",
            "vm.vfs_cache_pressure": "50",
            "vm.dirty_background_ratio": "5",
            "vm.dirty_ratio": "15",
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr",
            "fs.inotify.max_user_watches": "524288",
            "fs.inotify.max_user_instances": "4096",
        },
        "dnf_settings": {
            "max_parallel_downloads": 10,
            "fastestmirror": True,
            "defaultyes": True,
            "keepcache": True,
        },
        "notes": "Reduces swappiness to favor RAM, increases file watcher limits for IDEs, and enables BBR for faster web browsing.",
    },

    "gaming": {
        "id": "gaming",
        "name": "Gaming & Low Latency Workstation",
        "category": "Desktop",
        "description": "Tuned for Steam, Proton/Wine compatibility, low scheduling jitter, and optimal frame pacing.",
        "icon": "🎮",
        "tuned_profile": "throughput-performance",
        "journald_max": "200M",
        "sysctl": {
            "vm.max_map_count": "2147483642",
            "vm.swappiness": "10",
            "vm.vfs_cache_pressure": "50",
            "kernel.split_lock_mitigate": "0",
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr",
            "fs.file-max": "2097152",
        },
        "dnf_settings": {
            "max_parallel_downloads": 10,
            "fastestmirror": True,
            "defaultyes": True,
            "keepcache": True,
        },
        "notes": "Essential vm.max_map_count (2M+) for modern Proton/Steam titles, disabled split-lock mitigation for high FPS.",
    },

    "server": {
        "id": "server",
        "name": "General Enterprise Server (Rocky / CentOS / Fedora)",
        "category": "Server",
        "description": "Solid enterprise server profile tuned for high network uptime, stability, and higher system limits.",
        "icon": "🏢",
        "tuned_profile": "throughput-performance",
        "journald_max": "500M",
        "sysctl": {
            "vm.swappiness": "10",
            "vm.vfs_cache_pressure": "100",
            "fs.file-max": "2097152",
            "net.core.somaxconn": "32768",
            "net.ipv4.tcp_max_syn_backlog": "8192",
            "net.ipv4.tcp_tw_reuse": "1",
            "net.ipv4.tcp_fin_timeout": "15",
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr",
            "net.ipv4.tcp_keepalive_time": "300",
            "net.ipv4.tcp_keepalive_probes": "5",
            "net.ipv4.tcp_keepalive_intvl": "15",
        },
        "dnf_settings": {
            "max_parallel_downloads": 10,
            "fastestmirror": True,
            "defaultyes": True,
            "keepcache": True,
        },
        "notes": "Expands connection backlog, shortens dead socket recycling, and scales max file handles.",
    },

    "web_server": {
        "id": "web_server",
        "name": "High-Throughput Web / API Server",
        "category": "Server",
        "description": "Optimized for reverse proxies (Nginx, Caddy, HAProxy) and web microservices (Node.js, Go, Python).",
        "icon": "🌐",
        "tuned_profile": "network-throughput",
        "journald_max": "500M",
        "sysctl": {
            "net.core.somaxconn": "65535",
            "net.core.netdev_max_backlog": "16384",
            "net.ipv4.tcp_max_syn_backlog": "16384",
            "net.ipv4.tcp_tw_reuse": "1",
            "net.ipv4.tcp_fin_timeout": "10",
            "net.ipv4.tcp_rmem": "4096 87380 16777216",
            "net.ipv4.tcp_wmem": "4096 65536 16777216",
            "net.core.rmem_max": "16777216",
            "net.core.wmem_max": "16777216",
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr",
            "fs.file-max": "2097152",
            "vm.swappiness": "10",
        },
        "dnf_settings": {
            "max_parallel_downloads": 10,
            "fastestmirror": True,
            "defaultyes": True,
            "keepcache": True,
        },
        "notes": "Max connection queues (65k), 16MB socket TCP buffer ceilings, and BBR congestion for massive concurrent HTTP(S) requests.",
    },

    "database": {
        "id": "database",
        "name": "Database & Heavy I/O Server",
        "category": "Server",
        "description": "Designed for PostgreSQL, MariaDB/MySQL, and Redis workloads requiring sustained storage write throughput.",
        "icon": "🗄️",
        "tuned_profile": "throughput-performance",
        "journald_max": "500M",
        "sysctl": {
            "vm.swappiness": "1",
            "vm.dirty_background_ratio": "3",
            "vm.dirty_ratio": "10",
            "vm.vfs_cache_pressure": "50",
            "fs.file-max": "2097152",
            "net.core.somaxconn": "32768",
            "net.ipv4.tcp_tw_reuse": "1",
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr",
        },
        "dnf_settings": {
            "max_parallel_downloads": 10,
            "fastestmirror": True,
            "defaultyes": True,
            "keepcache": True,
        },
        "notes": "Reduces swappiness to 1 to lock database memory in physical RAM; smooths out disk sync write stalls.",
    },

    "container_host": {
        "id": "container_host",
        "name": "Docker & Podman Container Host",
        "category": "Containers & Cloud",
        "description": "Tuned for dense multi-container hosts, rootless Podman, bridge networking, and microservice watchers.",
        "icon": "🐳",
        "tuned_profile": "throughput-performance",
        "journald_max": "500M",
        "sysctl": {
            "net.ipv4.ip_forward": "1",
            "net.ipv6.conf.all.forwarding": "1",
            "net.bridge.bridge-nf-call-iptables": "1",
            "net.bridge.bridge-nf-call-ip6tables": "1",
            "fs.inotify.max_user_watches": "1048576",
            "fs.inotify.max_user_instances": "8192",
            "fs.file-max": "2097152",
            "kernel.pid_max": "4194304",
            "net.core.somaxconn": "32768",
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr",
        },
        "dnf_settings": {
            "max_parallel_downloads": 10,
            "fastestmirror": True,
            "defaultyes": True,
            "keepcache": True,
        },
        "notes": "Enables IP forwarding, sets inotify watchers to 1M+ for container dev, and doubles PID limits to prevent thread exhaustion.",
    },

    "virtualization_host": {
        "id": "virtualization_host",
        "name": "KVM / QEMU Virtualization Host",
        "category": "Virtualization",
        "description": "Optimized for dense hypervisors running virtual machines with Libvirt, QEMU, and KVM.",
        "icon": "🖥️",
        "tuned_profile": "virtual-host",
        "journald_max": "500M",
        "sysctl": {
            "net.ipv4.ip_forward": "1",
            "net.ipv4.conf.all.proxy_arp": "1",
            "vm.swappiness": "1",
            "vm.vfs_cache_pressure": "50",
            "fs.file-max": "2097152",
            "net.core.somaxconn": "32768",
            "net.core.rmem_max": "16777216",
            "net.core.wmem_max": "16777216",
        },
        "dnf_settings": {
            "max_parallel_downloads": 10,
            "fastestmirror": True,
            "defaultyes": True,
            "keepcache": True,
        },
        "notes": "Uses virtual-host profile, enables network bridge ARP forwarding, and reduces host swapping for VM memory stability.",
    },

    "virtualmin": {
        "id": "virtualmin",
        "name": "Virtualmin & Webmin Hosting Server",
        "category": "Hosting & Webmin",
        "description": "Tailored for multi-tenant web, DNS, and mail servers running Virtualmin on Rocky, CentOS, or Fedora Server.",
        "icon": "🌐",
        "tuned_profile": "throughput-performance",
        "journald_max": "400M",
        "sysctl": {
            "net.core.somaxconn": "65535",
            "net.ipv4.tcp_max_syn_backlog": "16384",
            "net.ipv4.tcp_tw_reuse": "1",
            "net.ipv4.tcp_fin_timeout": "15",
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr",
            "fs.file-max": "2097152",
            "vm.swappiness": "10",
            "vm.vfs_cache_pressure": "75",
        },
        "dnf_settings": {
            "max_parallel_downloads": 10,
            "fastestmirror": True,
            "defaultyes": True,
            "keepcache": True,
        },
        "notes": "Handles high volume Apache/Nginx + PHP-FPM requests, Postfix/Dovecot connections, and MariaDB queries without socket bottlenecks.",
    },
}


def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve profile dictionary by ID."""
    return PROFILES.get(profile_id)


def list_profiles() -> List[Dict[str, Any]]:
    """Return all tuning profile definitions."""
    return list(PROFILES.values())
