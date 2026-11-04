"""
Asynchronous Worker Threads for ConfTune FC GUI.
Ensures UI responsiveness during tuning operations, system scans, and disk trimming.
Provides thread lifetime management and safe main-thread callback marshaling.
"""

from typing import Any, Callable, Dict, Optional, Set
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal

# Persistent set to retain running workers and prevent Python garbage collection
_ACTIVE_WORKERS: Set[QThread] = set()


class AsyncTaskWorker(QThread):
    """Executes a callable workload safely inside a dedicated QThread."""

    task_finished = pyqtSignal(bool, str, object)
    task_progress = pyqtSignal(str)

    def __init__(self, func: Callable[..., Any], *args, parent: Optional[QObject] = None, **kwargs):
        super().__init__(parent)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            res = self.func(*self.args, **self.kwargs)
            if isinstance(res, tuple) and len(res) >= 2 and isinstance(res[0], bool):
                self.task_finished.emit(res[0], str(res[1]), res)
            else:
                self.task_finished.emit(True, "Task finished successfully.", res)
        except Exception as e:
            self.task_finished.emit(False, str(e), None)


# Backward-compatibility alias
WorkerTask = AsyncTaskWorker


def run_async_task(
    func: Callable[..., Any],
    on_finished: Optional[Callable[[bool, str, Any], None]] = None,
    *args,
    on_progress: Optional[Callable[[str], None]] = None,
    parent: Optional[QObject] = None,
    **kwargs,
) -> AsyncTaskWorker:
    """
    Launch a function on a background QThread with lifetime protection.
    Guarantees that the QThread is never garbage-collected while executing,
    and dispatches on_finished safely on the Qt main GUI thread.
    """
    worker = AsyncTaskWorker(func, *args, parent=parent, **kwargs)
    _ACTIVE_WORKERS.add(worker)

    def _cleanup(ok: bool, msg: str, payload: Any) -> None:
        _ACTIVE_WORKERS.discard(worker)
        worker.deleteLater()
        if on_finished:
            on_finished(ok, msg, payload)

    # QueuedConnection guarantees that the slot is invoked on the thread of the receiver (GUI thread)
    worker.task_finished.connect(_cleanup, Qt.ConnectionType.QueuedConnection)
    if on_progress:
        worker.task_progress.connect(on_progress, Qt.ConnectionType.QueuedConnection)

    worker.start()
    return worker
