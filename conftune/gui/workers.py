"""
Asynchronous Worker Threads for ConfTune FC GUI.
Ensures UI responsiveness during tuning operations, system scans, and disk trimming.
"""

from typing import Any, Callable, Dict
from PyQt6.QtCore import QObject, QThread, pyqtSignal


class WorkerTask(QObject):
    """Executes a callable workload inside a worker thread."""

    finished = pyqtSignal(bool, str, object)
    progress = pyqtSignal(str)

    def __init__(self, func: Callable[..., Any], *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            res = self.func(*self.args, **self.kwargs)
            if isinstance(res, tuple) and len(res) >= 2 and isinstance(res[0], bool):
                self.finished.emit(res[0], str(res[1]), res)
            else:
                self.finished.emit(True, "Task finished successfully.", res)
        except Exception as e:
            self.finished.emit(False, str(e), None)


def run_async_task(func: Callable[..., Any], on_finished: Callable[[bool, str, Any], None], *args, **kwargs) -> QThread:
    """Helper to launch a function on a background QThread."""
    thread = QThread()
    worker = WorkerTask(func, *args, **kwargs)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(on_finished)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread
