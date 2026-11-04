"""
Audit Logs Tab for ConfTune FC.
Real-time log streamer and audit trail view.
"""

import logging
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from conftune.core.logger import add_log_listener, remove_log_listener


class LogsTab(QWidget):
    """Real-time audit log interface."""

    def __init__(self):
        super().__init__()
        self._init_ui()
        add_log_listener(self._on_log_message)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Card
        header = QFrame()
        header.setProperty("class", "card")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 12, 16, 12)

        v_box = QVBoxLayout()
        lbl_title = QLabel("System Audit Logs & Execution Stream")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_sub = QLabel("Live audit trail of system modifications, backups, and tuning tasks.")
        lbl_sub.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        v_box.addWidget(lbl_title)
        v_box.addWidget(lbl_sub)
        h_lay.addLayout(v_box)
        h_lay.addStretch()

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filter logs...")
        self.txt_filter.setFixedWidth(200)
        h_lay.addWidget(self.txt_filter)

        btn_clear = QPushButton("🧹 Clear")
        btn_clear.clicked.connect(self._clear_logs)
        h_lay.addWidget(btn_clear)

        layout.addWidget(header)

        # Log Text Box
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "background-color: #1e1e1e; color: #dedede; font-family: monospace; font-size: 12px; border: 1px solid #333333; border-radius: 6px; padding: 10px;"
        )
        layout.addWidget(self.log_text)

    def _on_log_message(self, message: str, level: int):
        color = "#dedede"
        if level >= logging.ERROR:
            color = "#f66151"
        elif level >= logging.WARNING:
            color = "#f6d32d"
        elif "success" in message.lower() or "restored" in message.lower():
            color = "#57e389"

        html_msg = f'<span style="color: {color};">{message}</span>'
        self.log_text.append(html_msg)
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def _clear_logs(self):
        self.log_text.clear()

    def closeEvent(self, event):
        remove_log_listener(self._on_log_message)
        super().closeEvent(event)
