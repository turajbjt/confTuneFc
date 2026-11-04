#!/usr/bin/env python3
"""
ConfTune FC - Fedora, Rocky Linux & CentOS System Setup, Configuration & Performance Tuner.
Entry point for GUI application and headless CLI workflows.
"""

import argparse
import os
import sys

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def main():
    parser = argparse.ArgumentParser(
        description="ConfTune FC - System setup, configuration and performance tuner for Fedora, Rocky Linux, and CentOS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                               # Launch graphical interface (default)
  python3 main.py --status                      # View hardware specs, role & performance score
  python3 main.py --list-profiles               # List available tuning profiles
  python3 main.py --profile workstation         # Simulate Fedora desktop optimization (dry-run)
  python3 main.py --profile server --apply      # Apply Enterprise Server tuning permanently
  python3 main.py --tune-dnf --apply            # Optimize DNF parallel downloads & fastest mirrors
  python3 main.py --tune-containers --apply     # Configure Docker/Podman bridge network & inotify
  python3 main.py --tune-virt --apply           # Configure KVM/Libvirt hypervisor & KSM
  python3 main.py --tune-virtualmin --apply     # Optimize Virtualmin / Webmin hosting stack
  python3 main.py --trim                        # Trigger immediate SSD/NVMe filesystem TRIM
  python3 main.py --snapshots                   # List all pre-tune configuration snapshots
  python3 main.py --rollback <SNAPSHOT_ID>      # Restore original files from a snapshot
        """,
    )

    parser.add_argument("--gui", action="store_true", help="Launch the graphical interface (default if display server detected)")
    parser.add_argument("--elevated-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--status", action="store_true", help="Print system summary and tuning readiness")
    parser.add_argument("--list-profiles", action="store_true", help="List all available tuning presets")
    parser.add_argument("--profile", metavar="NAME", help="Apply a tuning profile (e.g. workstation, gaming, server, web_server, database, container_host, virtualization_host, virtualmin)")
    parser.add_argument("--tune-dnf", action="store_true", help="Optimize /etc/dnf/dnf.conf with parallel downloads and fastest mirrors")
    parser.add_argument("--tune-containers", action="store_true", help="Set up kernel modules and sysctls for Docker & Podman")
    parser.add_argument("--tune-virt", action="store_true", help="Set up KVM/Libvirt host profile and memory deduplication (KSM)")
    parser.add_argument("--tune-virtualmin", action="store_true", help="Configure Virtualmin / Webmin hosting stack and firewall")
    parser.add_argument("--trim", action="store_true", help="Run filesystem TRIM across all SSD/NVMe drives")
    parser.add_argument("--snapshots", action="store_true", help="List all past configuration snapshots")
    parser.add_argument("--rollback", metavar="ID", help="Roll back system configuration to a specified snapshot ID")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Simulate tuning changes without writing files")
    parser.add_argument("--apply", action="store_true", default=False, help="Commit actual changes to system files (disables dry-run)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()

    # Determine execution mode: CLI or GUI
    cli_flags = [
        args.status,
        args.list_profiles,
        bool(args.profile),
        args.tune_dnf,
        args.tune_containers,
        args.tune_virt,
        args.tune_virtualmin,
        args.trim,
        args.snapshots,
        bool(args.rollback),
        args.dry_run,
    ]
    is_cli_requested = any(cli_flags)

    if is_cli_requested and not args.gui:
        from conftune.cli import run_cli
        run_cli(args)
    else:
        # Check display server availability
        has_display = bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))
        if not has_display:
            if args.gui or args.elevated_child:
                print(
                    "Error: Graphical interface requested, but no WAYLAND_DISPLAY or DISPLAY environment variable was found.",
                    file=sys.stderr,
                )
                sys.exit(1)
            print("No Wayland or X11 display detected. Falling back to CLI status mode...")
            from conftune.cli import run_cli
            args.status = True
            run_cli(args)
            return

        try:
            from conftune.gui.app import run_gui
            run_gui(ready_signal=args.elevated_child)
        except ImportError as e:
            err_msg = (
                "\n"
                "=================================================================\n"
                "ConfTune FC: PyQt6 is required to run the Graphical Interface.\n"
                "=================================================================\n"
                "To install PyQt6 on Fedora, Rocky Linux, or CentOS Stream:\n"
                "    sudo dnf install python3-pyqt6\n\n"
                "Or via Python package manager:\n"
                "    pip install PyQt6\n\n"
                "You can also use ConfTune FC completely headless via the CLI:\n"
                "    python3 main.py --help\n"
                "=================================================================\n"
            )
            print(err_msg, file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
