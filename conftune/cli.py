"""
Command-Line Interface for ConfTune FC.
Provides comprehensive headless administration for Fedora Server, Rocky Linux, and CentOS.
"""

import argparse
import json
import os
import sys
from typing import Optional

from conftune import __version__
from conftune.core.autostart_tuner import AutostartTuner
from conftune.core.backup_manager import BackupManager
from conftune.core.detector import SystemDetector
from conftune.core.dnf_tuner import DNFTuner
from conftune.core.fedy_tuner import FedyTuner
from conftune.core.logger import get_logger, setup_logger
from conftune.core.power_tuner import PowerTuner
from conftune.core.preset_manager import PresetManager
from conftune.core.privacy_tuner import PrivacyTuner
from conftune.core.process_tuner import ProcessTuner
from conftune.core.profiles import PROFILES, get_profile, list_profiles
from conftune.core.safety import SafetyEngine
from conftune.core.server_tuner import ServerTuner
from conftune.core.storage_tuner import StorageTuner
from conftune.core.sysctl_tuner import SysctlTuner
from conftune.core.systemd_tuner import SystemdTuner


def run_cli(args: argparse.Namespace) -> None:
    """Execute command-line workflows."""
    setup_logger(verbose=getattr(args, "verbose", False))
    logger = get_logger()

    write_actions = [
        getattr(args, "trim", False),
        bool(args.profile),
        args.tune_dnf,
        args.tune_containers,
        args.tune_virt,
        args.tune_virtualmin,
        getattr(args, "fedy_codecs", False),
        getattr(args, "fedy_fonts", False),
        bool(getattr(args, "governor", None)),
        bool(getattr(args, "epp", None)),
        bool(getattr(args, "thp", None)),
        bool(getattr(args, "protect_process", None)),
        getattr(args, "tune_oomd", False),
        getattr(args, "disable_telemetry", False),
        bool(getattr(args, "import_preset", None)),
    ]
    safety = SafetyEngine(dry_run=not args.apply if any(write_actions) else args.dry_run)
    # If user explicitly specifies --dry-run or omits --apply on write operations
    if args.dry_run:
        safety.dry_run = True

    backup_mgr = BackupManager()
    detector = SystemDetector()
    sysctl_tuner = SysctlTuner(safety=safety, backup_mgr=backup_mgr)
    dnf_tuner = DNFTuner(safety=safety, backup_mgr=backup_mgr)
    systemd_tuner = SystemdTuner(safety=safety, backup_mgr=backup_mgr)
    storage_tuner = StorageTuner(safety=safety, backup_mgr=backup_mgr)
    server_tuner = ServerTuner(safety=safety, backup_mgr=backup_mgr)
    fedy_tuner = FedyTuner(safety=safety, backup_mgr=backup_mgr)
    power_tuner = PowerTuner(safety=safety)
    process_tuner = ProcessTuner(safety=safety, backup_mgr=backup_mgr)
    autostart_tuner = AutostartTuner(safety=safety, backup_mgr=backup_mgr)
    privacy_tuner = PrivacyTuner(safety=safety)
    preset_mgr = PresetManager(safety=safety, backup_mgr=backup_mgr)

    # 1. Status / Overview
    if args.status:
        print_system_status(detector, server_tuner, systemd_tuner)
        return

    # 2. List Profiles
    if args.list_profiles:
        print("\n==================== ConfTune FC - Tuning Presets ====================")
        for p in list_profiles():
            print(f"[{p['id']}] {p['icon']} {p['name']} ({p['category']})")
            print(f"    Description: {p['description']}")
            print(f"    Tuned: {p['tuned_profile']} | Journald: {p['journald_max']}")
            print()
        return

    # 3. Apply Profile
    if args.profile:
        profile_key = args.profile.lower().replace("-", "_")
        prof = get_profile(profile_key)
        if not prof:
            print(f"Error: Unknown profile '{args.profile}'. Use --list-profiles to view valid options.", file=sys.stderr)
            sys.exit(1)

        print(f"\n==> Applying Profile: {prof['name']} (dry-run: {safety.dry_run})")
        # 1. Sysctl
        ok, msg = sysctl_tuner.apply_parameters(prof["sysctl"], profile_name=prof["name"])
        print(f"  [Sysctl] {msg}")

        # 2. DNF
        dnf_cfg = prof.get("dnf_settings", {})
        ok, msg = dnf_tuner.apply_optimizations(
            max_parallel_downloads=dnf_cfg.get("max_parallel_downloads", 10),
            fastestmirror=dnf_cfg.get("fastestmirror", True),
            defaultyes=dnf_cfg.get("defaultyes", True),
            keepcache=dnf_cfg.get("keepcache", True),
        )
        print(f"  [DNF] {msg}")

        # 3. Systemd Journald
        ok, msg = systemd_tuner.configure_journald_limit(prof.get("journald_max", "300M"))
        print(f"  [Journald] {msg}")

        # 4. Tuned profile
        if prof.get("tuned_profile"):
            ok, msg = server_tuner.set_tuned_profile(prof["tuned_profile"])
            print(f"  [Tuned] {msg}")

        print(f"\nProfile application completed. {'(Simulation mode - no files modified)' if safety.dry_run else 'All changes applied safely.'}")
        if safety.dry_run:
            print("To commit these changes permanently to the system, re-run with: --apply")
        return

    # 4. DNF Acceleration
    if args.tune_dnf:
        print(f"\n==> Tuning DNF package manager (dry-run: {safety.dry_run})...")
        ok, msg = dnf_tuner.apply_optimizations()
        print(f"  {msg}")
        return

    # 5. Specialized: Containers (Podman / Docker)
    if args.tune_containers:
        print(f"\n==> Configuring Container Host stack (dry-run: {safety.dry_run})...")
        ok, msg = server_tuner.optimize_containers_stack()
        print(f"  {msg}")
        # Apply container host sysctl
        c_prof = get_profile("container_host")
        if c_prof:
            ok, msg = sysctl_tuner.apply_parameters(c_prof["sysctl"], profile_name=c_prof["name"])
            print(f"  {msg}")
        return

    # 6. Specialized: Virtualization Host (KVM / QEMU / Libvirt)
    if args.tune_virt:
        print(f"\n==> Configuring Virtualization Host stack (dry-run: {safety.dry_run})...")
        ok, msg = server_tuner.optimize_virtualization_host()
        print(f"  {msg}")
        v_prof = get_profile("virtualization_host")
        if v_prof:
            ok, msg = sysctl_tuner.apply_parameters(v_prof["sysctl"], profile_name=v_prof["name"])
            print(f"  {msg}")
        return

    # 7. Specialized: Virtualmin & Webmin
    if args.tune_virtualmin:
        print(f"\n==> Configuring Virtualmin / Webmin stack (dry-run: {safety.dry_run})...")
        ok, msg = server_tuner.optimize_virtualmin_stack()
        print(f"  {msg}")
        vm_prof = get_profile("virtualmin")
        if vm_prof:
            ok, msg = sysctl_tuner.apply_parameters(vm_prof["sysctl"], profile_name=vm_prof["name"])
            print(f"  {msg}")
        return

    # 8. Storage: Trim
    if args.trim:
        print("\n==> Running filesystem TRIM across all SSD/NVMe drives...")
        ok, msg = storage_tuner.run_fstrim_now()
        print(msg)
        return

    # 9. Snapshots & Rollback
    if args.snapshots:
        snaps = backup_mgr.list_snapshots()
        print(f"\n================ Configuration Snapshots ({len(snaps)}) ================")
        if not snaps:
            print("No snapshots recorded yet.")
        for s in snaps:
            print(f"ID: {s.get('id')} | Time: {s.get('timestamp')} | Profile: {s.get('profile')}")
            print(f"    Tracked Files: {len(s.get('files', []))}")
            for f in s.get("files", []):
                print(f"      - {f.get('original_path')}")
            print()
        return

    if args.rollback:
        snap_id = args.rollback
        print(f"\n==> Rolling back to snapshot: {snap_id} (dry-run: {safety.dry_run})...")
        ok, msg = backup_mgr.rollback_snapshot(snap_id, dry_run=safety.dry_run)
        print(msg)
        return

    # Fedy: RPM Fusion & Codecs
    if getattr(args, "fedy_codecs", False):
        print("\n==> Installing RPM Fusion & Multimedia Codecs (dry-run: %s)..." % safety.dry_run)
        ok1, msg1 = fedy_tuner.install_rpmfusion()
        print("  [RPM Fusion] %s" % msg1)
        ok2, msg2 = fedy_tuner.install_multimedia_codecs()
        print("  [Codecs] %s" % msg2)
        return

    # Fedy: Fonts
    if getattr(args, "fedy_fonts", False):
        print("\n==> Configuring Font Rendering (Subpixel RGB)...")
        ok, msg = fedy_tuner.configure_font_rendering()
        print("  %s" % msg)
        return

    # Power: Governor
    if getattr(args, "governor", None):
        gov = args.governor
        print(f"\n==> Setting CPU Governor to '{gov}' across all cores (dry-run: {safety.dry_run})...")
        ok, msg = power_tuner.set_governor_all_cores(gov)
        print(f"  {msg}")
        return

    # Power: EPP
    if getattr(args, "epp", None):
        epp = args.epp
        print(f"\n==> Setting CPU EPP to '{epp}' across all cores (dry-run: {safety.dry_run})...")
        ok, msg = power_tuner.set_epp_all_cores(epp)
        print(f"  {msg}")
        return

    # Power: THP
    if getattr(args, "thp", None):
        thp_mode = args.thp
        print(f"\n==> Setting Transparent Huge Pages (THP) to '{thp_mode}' (dry-run: {safety.dry_run})...")
        ok, msg = power_tuner.set_thp_mode(thp_mode)
        print(f"  {msg}")
        return

    # Process: Protect OOM
    if getattr(args, "protect_process", None):
        pname = args.protect_process
        score = getattr(args, "oom_score", -500)
        print(f"\n==> Setting OOM Killer Score ({score}) on '{pname}' (dry-run: {safety.dry_run})...")
        ok, msg = process_tuner.protect_process_by_name(pname, score)
        print(f"  {msg}")
        return

    # Process: Tune oomd
    if getattr(args, "tune_oomd", False):
        print(f"\n==> Configuring systemd-oomd limits (dry-run: {safety.dry_run})...")
        ok, msg = process_tuner.configure_oomd_limits()
        print(f"  {msg}")
        return

    # Privacy: Disable telemetry
    if getattr(args, "disable_telemetry", False):
        print("\n==> Disabling System & Desktop Telemetry...")
        ok, msg = privacy_tuner.disable_all_telemetry()
        print(f"  {msg}")
        return

    # Autostart: List
    if getattr(args, "list_autostart", False):
        entries = autostart_tuner.list_autostart_entries()
        print(f"\n================ Autostart Applications ({len(entries)}) ================")
        for e in entries:
            stat = "Enabled" if e["enabled"] else "Disabled"
            print(f"[{stat}] {e['name']} ({e['scope']}) -> {e['exec']}")
        return

    # Server: Drive Health
    if getattr(args, "drive_health", False):
        drives = server_tuner.get_drive_health_summary()
        print(f"\n================ Drive Health (SMART / NVMe) ================")
        for d in drives:
            print(f"  • {d.get('device')}: Health={d.get('health')} (Status: {d.get('status')})")
        return

    # Preset: Export Archive
    if getattr(args, "export_preset", None):
        out_f = args.export_preset
        print(f"\n==> Exporting Host Configuration to '{out_f}'...")
        ok, msg = preset_mgr.export_preset_archive(out_f)
        print(f"  {msg}")
        return

    # Preset: Import Archive
    if getattr(args, "import_preset", None):
        in_f = args.import_preset
        print(f"\n==> Importing Preset from '{in_f}' (dry-run: {safety.dry_run})...")
        ok, msg, pdata = preset_mgr.import_preset_archive(in_f)
        if not ok:
            print(f"  Error: {msg}", file=sys.stderr)
            sys.exit(1)
        print(f"  Loaded preset: {pdata.get('name')}")
        ok_a, msg_a = preset_mgr.apply_preset(pdata)
        print(f"  {msg_a}")
        return

    # Preset: Standalone Script
    if getattr(args, "export_deploy_script", None):
        out_sh = args.export_deploy_script
        print(f"\n==> Generating Standalone Deployment Script to '{out_sh}'...")
        current_data = preset_mgr.capture_current_settings(name="Host Tuning")
        ok, msg = preset_mgr.generate_standalone_script(current_data, out_sh)
        print(f"  {msg}")
        return

    # Preset: Kickstart
    if getattr(args, "export_kickstart", None):
        out_ks = args.export_kickstart
        print(f"\n==> Generating Anaconda Kickstart Configuration to '{out_ks}'...")
        current_data = preset_mgr.capture_current_settings(name="Host Tuning")
        ok, msg = preset_mgr.generate_kickstart(current_data, out_ks)
        print(f"  {msg}")
        return

    # Preset: Build ISO
    if getattr(args, "build_iso", False):
        base_iso = getattr(args, "base_iso", None)
        out_iso = getattr(args, "output_iso", None)
        if not base_iso or not out_iso:
            print("Error: --build-iso requires both --base-iso <FILE> and --output-iso <FILE>.", file=sys.stderr)
            sys.exit(1)
        print(f"\n==> Injecting Kickstart into '{base_iso}' -> '{out_iso}' (dry-run: {safety.dry_run})...")
        tmp_ks = "/tmp/conftune_cli_temp.ks"
        current_data = preset_mgr.capture_current_settings(name="Host Tuning")
        preset_mgr.generate_kickstart(current_data, tmp_ks)
        ok, msg = preset_mgr.build_custom_iso(base_iso, tmp_ks, out_iso)
        if os.path.exists(tmp_ks):
            os.remove(tmp_ks)
        print(f"  {msg}")
        return

    # Default fallback: Print status
    print_system_status(detector, server_tuner, systemd_tuner)


def print_system_status(detector: SystemDetector, server_tuner: ServerTuner, systemd_tuner: SystemdTuner) -> None:
    """Print clean terminal summary of host system configuration."""
    os_info = detector.os_info
    hw = detector.hardware_info
    role = detector.role_info
    stacks = detector.specialized_stacks
    tuned = server_tuner.get_tuned_status()

    print(f"\n╔══════════════════════════════════════════════════════════════════════════╗")
    print(f"║                   ConfTune FC - System Performance Status                ║")
    print(f"║                   Version {__version__:<10} (Fedora / RPM Edition)                 ║")
    print(f"╚══════════════════════════════════════════════════════════════════════════╝\n")

    print(f"  Operating System  : {os_info.get('pretty_name')} ({os_info.get('arch')})")
    print(f"  Kernel Release    : {os_info.get('kernel')}")
    print(f"  Role Detection    : {'Desktop Workstation (' + role.get('desktop_env', 'GUI') + ')' if role.get('is_desktop') else 'Headless Server / Cloud Node'}")
    print(f"  Virtualization    : {hw.get('virtualization', 'none')}")
    print(f"  CPU Hardware      : {hw.get('cpu_model')} ({hw.get('cpu_cores')} cores)")
    print(f"  CPU Governor      : {hw.get('cpu_governor')}")
    print(f"  Memory (RAM)      : {hw.get('ram_avail_gb')} GB avail / {hw.get('ram_total_gb')} GB total")
    print(f"  ZRAM Swap         : {'Active (' + str(hw.get('zram_size_gb')) + ' GB)' if hw.get('has_zram') else 'None'}")
    print(f"  Storage Devices   : {'NVMe present' if hw.get('has_nvme') else 'SATA SSD/HDD'} (Root FS: {hw.get('root_fs')})")
    print(f"  Active Tuned Prof : {tuned.get('active_profile')}")
    print(f"  SELinux Mode      : {server_tuner.get_selinux_status()}")
    print(f"  Boot Time Summary : {systemd_tuner.get_boot_time_summary()}")

    print("\n  --- Specialized Stack Detection ---")
    vm = stacks.get("virtualmin", {})
    print(f"  Virtualmin/Webmin : {'Detected (Installed)' if vm.get('detected') else 'Not detected'}")
    c = stacks.get("containers", {})
    print(f"  Container Engines : {'Podman ' if c.get('has_podman') else ''}{'Docker ' if c.get('has_docker') else ''}{'None' if not (c.get('has_podman') or c.get('has_docker')) else ''} (IP Forwarding: {c.get('ip_forwarding')})")
    v = stacks.get("virtualization_host", {})
    print(f"  Virtualization    : {'KVM Host (/dev/kvm ready)' if v.get('is_kvm_host') else 'No hardware KVM'} (Libvirt: {v.get('has_libvirt')})")

    print("\n  Tip: Run 'conftune --list-profiles' or 'conftune --profile <name> --apply' to tune.")
    print("       Run 'conftune --gui' to launch the graphical desktop interface.\n")
