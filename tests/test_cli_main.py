"""
Comprehensive Unit Tests for ConfTune FC Command-Line Interface and main.py entry point.
"""

import argparse
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from conftune.cli import print_system_status, run_cli
from conftune.core.detector import SystemDetector
from conftune.core.preset_manager import PresetManager
from conftune.core.server_tuner import ServerTuner
from conftune.core.systemd_tuner import SystemdTuner
import main


class TestCLIExecution(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="conftune_cli_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _make_args(self, **kwargs):
        defaults = {
            "status": False,
            "list_profiles": False,
            "profile": None,
            "tune_dnf": False,
            "tune_containers": False,
            "tune_virt": False,
            "tune_virtualmin": False,
            "trim": False,
            "snapshots": False,
            "rollback": None,
            "dry_run": True,
            "apply": False,
            "fedy_codecs": False,
            "fedy_fonts": False,
            "governor": None,
            "epp": None,
            "thp": None,
            "protect_process": None,
            "oom_score": -500,
            "tune_oomd": False,
            "disable_telemetry": False,
            "list_autostart": False,
            "drive_health": False,
            "export_preset": None,
            "import_preset": None,
            "export_deploy_script": None,
            "export_kickstart": None,
            "build_iso": False,
            "base_iso": None,
            "output_iso": None,
            "verbose": False,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_print_system_status(self):
        detector = SystemDetector(refresh_on_init=True)
        server_tuner = ServerTuner()
        systemd_tuner = SystemdTuner()
        out = io.StringIO()
        with patch("sys.stdout", out):
            print_system_status(detector, server_tuner, systemd_tuner)
        output_str = out.getvalue()
        self.assertIn("ConfTune FC - System Performance Status", output_str)
        self.assertIn("Operating System", output_str)
        self.assertIn("Kernel Release", output_str)

    def test_cli_status(self):
        args = self._make_args(status=True)
        out = io.StringIO()
        with patch("sys.stdout", out):
            run_cli(args)
        self.assertIn("ConfTune FC - System Performance Status", out.getvalue())

    def test_cli_list_profiles(self):
        args = self._make_args(list_profiles=True)
        out = io.StringIO()
        with patch("sys.stdout", out):
            run_cli(args)
        val = out.getvalue()
        self.assertIn("ConfTune FC - Tuning Presets", val)
        self.assertIn("workstation", val)
        self.assertIn("server", val)

    def test_cli_profile_apply_simulation(self):
        args = self._make_args(profile="workstation", dry_run=True)
        out = io.StringIO()
        with patch("sys.stdout", out):
            run_cli(args)
        val = out.getvalue()
        self.assertIn("Applying Profile: Fedora Desktop / Workstation", val)
        self.assertIn("[Sysctl]", val)
        self.assertIn("[DNF]", val)
        self.assertIn("[Journald]", val)
        self.assertIn("[Tuned]", val)

    def test_cli_profile_unknown_fails(self):
        args = self._make_args(profile="nonexistent_profile_xyz")
        err = io.StringIO()
        with patch("sys.stderr", err):
            with self.assertRaises(SystemExit) as cm:
                run_cli(args)
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("Unknown profile", err.getvalue())

    def test_cli_tune_dnf(self):
        args = self._make_args(tune_dnf=True, dry_run=True)
        out = io.StringIO()
        with patch("sys.stdout", out):
            run_cli(args)
        self.assertIn("Tuning DNF package manager", out.getvalue())

    def test_cli_tune_containers(self):
        args = self._make_args(tune_containers=True, dry_run=True)
        out = io.StringIO()
        with patch("sys.stdout", out):
            run_cli(args)
        self.assertIn("Configuring Container Host stack", out.getvalue())

    def test_cli_tune_virt(self):
        args = self._make_args(tune_virt=True, dry_run=True)
        out = io.StringIO()
        with patch("sys.stdout", out):
            run_cli(args)
        self.assertIn("Configuring Virtualization Host stack", out.getvalue())

    def test_cli_tune_virtualmin(self):
        args = self._make_args(tune_virtualmin=True, dry_run=True)
        out = io.StringIO()
        with patch("sys.stdout", out):
            run_cli(args)
        self.assertIn("Configuring Virtualmin / Webmin stack", out.getvalue())

    def test_cli_trim(self):
        args = self._make_args(trim=True, dry_run=True)
        out = io.StringIO()
        with patch("sys.stdout", out):
            run_cli(args)
        self.assertIn("Running filesystem TRIM", out.getvalue())

    def test_cli_snapshots_and_rollback(self):
        # Snapshots list
        args = self._make_args(snapshots=True)
        out = io.StringIO()
        with patch("sys.stdout", out):
            run_cli(args)
        self.assertIn("Configuration Snapshots", out.getvalue())

        # Rollback nonexistent
        args_rb = self._make_args(rollback="nonexistent_snap_123", dry_run=True)
        out_rb = io.StringIO()
        with patch("sys.stdout", out_rb):
            run_cli(args_rb)
        self.assertIn("Rolling back to snapshot", out_rb.getvalue())

    def test_cli_fedy_codecs_and_fonts(self):
        args_c = self._make_args(fedy_codecs=True, dry_run=True)
        out_c = io.StringIO()
        with patch("sys.stdout", out_c):
            run_cli(args_c)
        self.assertIn("Installing RPM Fusion & Multimedia Codecs", out_c.getvalue())

        args_f = self._make_args(fedy_fonts=True)
        out_f = io.StringIO()
        with patch("sys.stdout", out_f):
            run_cli(args_f)
        self.assertIn("Configuring Font Rendering", out_f.getvalue())

    def test_cli_power_options(self):
        # Governor
        args_g = self._make_args(governor="powersave", dry_run=True)
        out_g = io.StringIO()
        with patch("sys.stdout", out_g):
            run_cli(args_g)
        self.assertIn("Setting CPU Governor", out_g.getvalue())

        # EPP
        args_e = self._make_args(epp="balance_power", dry_run=True)
        out_e = io.StringIO()
        with patch("sys.stdout", out_e):
            run_cli(args_e)
        self.assertIn("Setting CPU EPP", out_e.getvalue())

        # THP
        args_t = self._make_args(thp="madvise", dry_run=True)
        out_t = io.StringIO()
        with patch("sys.stdout", out_t):
            run_cli(args_t)
        self.assertIn("Setting Transparent Huge Pages", out_t.getvalue())

    def test_cli_process_and_oomd(self):
        # Protect process
        args_p = self._make_args(protect_process="systemd", oom_score=-600, dry_run=True)
        out_p = io.StringIO()
        with patch("sys.stdout", out_p):
            run_cli(args_p)
        self.assertIn("Setting OOM Killer Score", out_p.getvalue())

        # Tune oomd
        args_o = self._make_args(tune_oomd=True, dry_run=True)
        out_o = io.StringIO()
        with patch("sys.stdout", out_o):
            run_cli(args_o)
        self.assertIn("Configuring systemd-oomd limits", out_o.getvalue())

    def test_cli_privacy_and_autostart_and_drive_health(self):
        # Privacy
        args_pr = self._make_args(disable_telemetry=True)
        out_pr = io.StringIO()
        with patch("sys.stdout", out_pr):
            run_cli(args_pr)
        self.assertIn("Disabling System & Desktop Telemetry", out_pr.getvalue())

        # Autostart
        args_a = self._make_args(list_autostart=True)
        out_a = io.StringIO()
        with patch("sys.stdout", out_a):
            run_cli(args_a)
        self.assertIn("Autostart Applications", out_a.getvalue())

        # Drive health
        args_dh = self._make_args(drive_health=True)
        out_dh = io.StringIO()
        with patch("sys.stdout", out_dh):
            run_cli(args_dh)
        self.assertIn("Drive Health", out_dh.getvalue())

    def test_cli_preset_archive_export_and_import(self):
        archive_path = os.path.join(self.test_dir, "export_test.conftune.tar.gz")
        args_exp = self._make_args(export_preset=archive_path)
        out_exp = io.StringIO()
        with patch("sys.stdout", out_exp):
            run_cli(args_exp)
        self.assertIn("Exporting Host Configuration", out_exp.getvalue())
        self.assertTrue(os.path.isfile(archive_path))

        args_imp = self._make_args(import_preset=archive_path, dry_run=True)
        out_imp = io.StringIO()
        with patch("sys.stdout", out_imp):
            run_cli(args_imp)
        self.assertIn("Importing Preset", out_imp.getvalue())

    def test_cli_preset_deploy_script_and_kickstart(self):
        # Deploy script
        sh_path = os.path.join(self.test_dir, "deploy.sh")
        args_sh = self._make_args(export_deploy_script=sh_path)
        out_sh = io.StringIO()
        with patch("sys.stdout", out_sh):
            run_cli(args_sh)
        self.assertIn("Generating Standalone Deployment Script", out_sh.getvalue())
        self.assertTrue(os.path.isfile(sh_path))

        # Kickstart
        ks_path = os.path.join(self.test_dir, "test.ks")
        args_ks = self._make_args(export_kickstart=ks_path)
        out_ks = io.StringIO()
        with patch("sys.stdout", out_ks):
            run_cli(args_ks)
        self.assertIn("Generating Anaconda Kickstart Configuration", out_ks.getvalue())
        self.assertTrue(os.path.isfile(ks_path))

    def test_cli_build_iso_missing_arguments(self):
        args = self._make_args(build_iso=True)
        err = io.StringIO()
        with patch("sys.stderr", err):
            with self.assertRaises(SystemExit) as cm:
                run_cli(args)
            self.assertEqual(cm.exception.code, 1)
        self.assertIn("--build-iso requires both --base-iso", err.getvalue())

    def test_cli_root_required_for_apply_fails_when_non_root(self):
        args = self._make_args(profile="workstation", apply=True, dry_run=False)
        err = io.StringIO()
        with patch.object(os, "geteuid", return_value=1000):
            with patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    run_cli(args)
                self.assertEqual(cm.exception.code, 1)
        self.assertIn("Elevation Required", err.getvalue())
        self.assertIn("sudo", err.getvalue())

    def test_cli_root_required_for_trim_fails_when_non_root(self):
        args = self._make_args(trim=True, dry_run=False)
        err = io.StringIO()
        with patch.object(os, "geteuid", return_value=1000):
            with patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    run_cli(args)
                self.assertEqual(cm.exception.code, 1)
        self.assertIn("Elevation Required", err.getvalue())

    def test_cli_root_required_for_rollback_fails_when_non_root(self):
        args = self._make_args(rollback="snap_123", dry_run=False)
        err = io.StringIO()
        with patch.object(os, "geteuid", return_value=1000):
            with patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    run_cli(args)
                self.assertEqual(cm.exception.code, 1)
        self.assertIn("Elevation Required", err.getvalue())

    def test_cli_root_required_for_governor_fails_when_non_root(self):
        args = self._make_args(governor="performance", dry_run=False)
        err = io.StringIO()
        with patch.object(os, "geteuid", return_value=1000):
            with patch("sys.stderr", err):
                with self.assertRaises(SystemExit) as cm:
                    run_cli(args)
                self.assertEqual(cm.exception.code, 1)
        self.assertIn("Elevation Required", err.getvalue())

    def test_cli_root_allowed_when_root(self):
        args = self._make_args(tune_dnf=True, apply=True, dry_run=False)
        out = io.StringIO()
        with patch.object(os, "geteuid", return_value=0):
            with patch("sys.stdout", out):
                with patch("conftune.core.dnf_tuner.DNFTuner.apply_optimizations", return_value=(True, "DNF optimized successfully")):
                    run_cli(args)
        self.assertIn("Tuning DNF package manager", out.getvalue())


class TestMainEntryPoint(unittest.TestCase):
    def test_main_help_exit(self):
        with patch.object(sys, "argv", ["main.py", "--help"]):
            with self.assertRaises(SystemExit) as cm:
                main.main()
            self.assertEqual(cm.exception.code, 0)

    def test_main_status_headless(self):
        with patch.object(sys, "argv", ["main.py", "--status"]):
            out = io.StringIO()
            with patch("sys.stdout", out):
                main.main()
            self.assertIn("ConfTune FC - System Performance Status", out.getvalue())

    def test_main_fallback_when_no_display(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", ["main.py"]):
                out = io.StringIO()
                with patch("sys.stdout", out):
                    main.main()
                self.assertIn("No Wayland or X11 display detected", out.getvalue())


if __name__ == "__main__":
    unittest.main()
