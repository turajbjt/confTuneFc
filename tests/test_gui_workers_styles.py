"""
Unit Tests for ConfTune FC GUI Workers and Stylesheet.
"""

import sys
import time
import unittest
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from conftune.gui.styles import ADWAITA_DARK_STYLE
from conftune.gui.workers import (
    AsyncTaskWorker,
    WorkerTask,
    _ACTIVE_WORKERS,
    run_async_task,
)

# Ensure offscreen Qt platform
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestGUIStyles(unittest.TestCase):
    def test_adwaita_dark_style_contents(self):
        self.assertIsInstance(ADWAITA_DARK_STYLE, str)
        self.assertGreater(len(ADWAITA_DARK_STYLE), 500)
        self.assertIn("#header_bar", ADWAITA_DARK_STYLE)
        self.assertIn("#nav_sidebar", ADWAITA_DARK_STYLE)
        self.assertIn("QPushButton", ADWAITA_DARK_STYLE)
        self.assertIn("QTableWidget", ADWAITA_DARK_STYLE)
        self.assertIn("QTabWidget", ADWAITA_DARK_STYLE)
        self.assertIn("QLineEdit", ADWAITA_DARK_STYLE)


class TestGUIWorkers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_worker_task_success_tuple(self):
        def sample_task():
            return True, "Success result", {"data": 42}

        worker = AsyncTaskWorker(sample_task)
        received = []

        def on_finished(ok, msg, res):
            received.append((ok, msg, res))

        worker.task_finished.connect(on_finished)
        worker.run()

        self.assertEqual(len(received), 1)
        self.assertTrue(received[0][0])
        self.assertEqual(received[0][1], "Success result")
        self.assertEqual(received[0][2], (True, "Success result", {"data": 42}))

    def test_worker_task_success_raw_return(self):
        def sample_task():
            return "raw_string"

        worker = AsyncTaskWorker(sample_task)
        received = []

        def on_finished(ok, msg, res):
            received.append((ok, msg, res))

        worker.task_finished.connect(on_finished)
        worker.run()

        self.assertEqual(len(received), 1)
        self.assertTrue(received[0][0])
        self.assertEqual(received[0][2], "raw_string")

    def test_worker_task_exception(self):
        def bad_task():
            raise ValueError("Intentional crash in worker")

        worker = AsyncTaskWorker(bad_task)
        received = []

        def on_finished(ok, msg, res):
            received.append((ok, msg, res))

        worker.task_finished.connect(on_finished)
        worker.run()

        self.assertEqual(len(received), 1)
        self.assertFalse(received[0][0])
        self.assertIn("Intentional crash in worker", received[0][1])

    def test_backward_compatibility_alias(self):
        self.assertIs(WorkerTask, AsyncTaskWorker)

    def test_run_async_task_lifecycle(self):
        def background_job():
            return True, "Async job done", 123

        results = []

        def handle_done(ok, msg, res):
            results.append((ok, msg, res))

        worker = run_async_task(background_job, handle_done)
        self.assertIn(worker, _ACTIVE_WORKERS)

        # Wait for thread to finish
        worker.wait(2000)
        # Process queued events on main thread so queued slot runs
        for _ in range(10):
            QCoreApplication.processEvents()
            if results:
                break
            time.sleep(0.01)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][0])
        self.assertNotIn(worker, _ACTIVE_WORKERS)


if __name__ == "__main__":
    unittest.main()
