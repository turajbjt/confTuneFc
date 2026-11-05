"""
Modern Fedora Adwaita stylesheet for ConfTune FC.
Provides clean dark/light themes inspired by GNOME 45+ Adwaita design language.
"""

ADWAITA_DARK_STYLE = """
/* ConfTune FC Modern Dark Theme (GNOME Adwaita) */

QWidget {
    background-color: #242424;
    color: #f6f8fa;
    font-family: Cantarell, "Segoe UI", Roboto, Ubuntu, sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #1e1e1e;
}

/* Sidebar / Navigation */
QListWidget#nav_sidebar {
    background-color: #1e1e1e;
    border: none;
    padding-top: 8px;
    font-size: 14px;
    outline: none;
}

QListWidget#nav_sidebar::item {
    padding: 12px 16px;
    border-radius: 8px;
    margin: 3px 8px;
    color: #c0c0c0;
}

QListWidget#nav_sidebar::item:hover {
    background-color: #2d2d2d;
    color: #ffffff;
}

QListWidget#nav_sidebar::item:selected {
    background-color: #3584e4;
    color: #ffffff;
    font-weight: bold;
}

/* Header & Cards */
QFrame.card {
    background-color: #2d2d2d;
    border-radius: 10px;
    border: 1px solid #383838;
    padding: 14px;
}

QFrame#header_bar {
    background-color: #2a2a2a;
    border-bottom: 1px solid #383838;
    padding: 10px 16px;
}

QLabel#app_title {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}

QLabel#pill_badge {
    background-color: #383838;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 12px;
    color: #99c1f1;
}

QLabel#pill_accent {
    background-color: #1c71d8;
    color: #ffffff;
    font-weight: bold;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 12px;
}

QLabel#pill_root {
    background-color: #e01b24;
    color: #ffffff;
    font-weight: bold;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 12px;
}

QLabel#pill_success {
    background-color: #26a269;
    color: #ffffff;
    font-weight: bold;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 12px;
}

/* Buttons */
QPushButton {
    background-color: #383838;
    color: #ffffff;
    border: 1px solid #484848;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #444444;
    border-color: #555555;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #666666;
    border-color: #333333;
}

QPushButton.primary, QPushButton[class="primary"] {
    background-color: #3584e4;
    border-color: #1c71d8;
    color: #ffffff;
    font-weight: bold;
}

QPushButton.primary:hover, QPushButton[class="primary"]:hover {
    background-color: #1c71d8;
}

QPushButton.success, QPushButton[class="success"] {
    background-color: #26a269;
    border-color: #1f8b57;
    color: #ffffff;
    font-weight: bold;
}

QPushButton.success:hover, QPushButton[class="success"]:hover {
    background-color: #1f8b57;
}

QPushButton.destructive, QPushButton[class="destructive"] {
    background-color: #e01b24;
    border-color: #c01c28;
    color: #ffffff;
    font-weight: bold;
}

QPushButton.destructive:hover, QPushButton[class="destructive"]:hover {
    background-color: #c01c28;
}

/* Tree & Tables */
QTreeWidget, QTableWidget {
    background-color: #242424;
    border: 1px solid #383838;
    border-radius: 8px;
    alternate-background-color: #282828;
    outline: none;
    gridline-color: #333333;
}

QTreeWidget::item, QTableWidget::item {
    padding: 6px;
}

QTableWidget QPushButton {
    background-color: #383838;
    color: #ffffff;
    border: 1px solid #484848;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    min-height: 28px;
    min-width: 150px;
}

QTableWidget QPushButton:hover {
    background-color: #444444;
    border-color: #555555;
}

QTableWidget QPushButton.destructive, QTableWidget QPushButton[class="destructive"] {
    background-color: #e01b24;
    border-color: #c01c28;
    color: #ffffff;
    font-weight: bold;
}

QTableWidget QPushButton.destructive:hover, QTableWidget QPushButton[class="destructive"]:hover {
    background-color: #c01c28;
}

QHeaderView::section {
    background-color: #2a2a2a;
    color: #dedede;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #383838;
    font-weight: bold;
}

/* Inputs & Form Controls */
QLineEdit, QSpinBox, QComboBox, QTextEdit {
    background-color: #2d2d2d;
    border: 1px solid #3e3e3e;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border-color: #3584e4;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #444444;
    border-radius: 4px;
    background-color: #2d2d2d;
}

QCheckBox::indicator:checked {
    background-color: #3584e4;
    border-color: #1c71d8;
}

/* ScrollBars */
QScrollBar:vertical {
    background: #1e1e1e;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #3e3e3e;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #555555;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* Tab Views */
QTabWidget::pane {
    border: 1px solid #383838;
    border-radius: 8px;
    background-color: #242424;
    padding: 8px;
}

QTabBar::tab {
    background: #2a2a2a;
    color: #b0b0b0;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #3584e4;
    color: #ffffff;
    font-weight: bold;
}
"""
