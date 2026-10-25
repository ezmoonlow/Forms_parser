# -*- coding: utf-8 -*-
"""Тёмная минималистичная тема оформления приложения."""

DARK_QSS = """
QWidget {
    background-color: #1b1d23;
    color: #e6e6ea;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #1b1d23;
}

QTabWidget::pane {
    border: 1px solid #2c2f38;
    border-radius: 8px;
    top: -1px;
    background-color: #20232b;
}

QTabBar::tab {
    background: #1b1d23;
    color: #9a9ea9;
    padding: 9px 18px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background: #20232b;
    color: #8b7bff;
    border-bottom: 2px solid #8b7bff;
}

QTabBar::tab:hover {
    color: #ffffff;
}

QGroupBox {
    border: 1px solid #2c2f38;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    color: #b7bac3;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #8b7bff;
}

QPushButton {
    background-color: #2b2e38;
    color: #e6e6ea;
    border: 1px solid #383c48;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #363a46;
    border: 1px solid #8b7bff;
}

QPushButton:pressed {
    background-color: #262933;
}

QPushButton:disabled {
    color: #63666f;
    background-color: #23252c;
    border: 1px solid #2c2f38;
}

QPushButton#primary {
    background-color: #6c5ce7;
    border: 1px solid #6c5ce7;
    color: #ffffff;
}

QPushButton#primary:hover {
    background-color: #7d6ef2;
}

QPushButton#danger {
    background-color: #3a2130;
    border: 1px solid #e05575;
    color: #f2a9bb;
}

QPushButton#danger:hover {
    background-color: #4a2739;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #23252c;
    border: 1px solid #383c48;
    border-radius: 6px;
    padding: 6px 8px;
    color: #e6e6ea;
    selection-background-color: #6c5ce7;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #8b7bff;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox QAbstractItemView {
    background-color: #23252c;
    border: 1px solid #383c48;
    selection-background-color: #6c5ce7;
    color: #e6e6ea;
    outline: none;
}

QTableWidget, QListWidget {
    background-color: #20232b;
    border: 1px solid #2c2f38;
    border-radius: 8px;
    gridline-color: #2c2f38;
    color: #e6e6ea;
    alternate-background-color: #23252c;
}

QHeaderView::section {
    background-color: #262933;
    color: #9a9ea9;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #2c2f38;
    font-weight: 600;
}

QTableWidget::item:selected, QListWidget::item:selected {
    background-color: #3a3350;
    color: #ffffff;
}

QScrollBar:vertical {
    background: #1b1d23;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #383c48;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #4a4f5c;
}
QScrollBar:horizontal {
    background: #1b1d23;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #383c48;
    border-radius: 5px;
    min-width: 24px;
}

QProgressBar {
    background-color: #23252c;
    border: 1px solid #2c2f38;
    border-radius: 6px;
    text-align: center;
    color: #e6e6ea;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #6c5ce7;
    border-radius: 6px;
}

QLabel#status_ok {
    color: #4fd18b;
    font-weight: 600;
}

QLabel#status_err {
    color: #e05575;
    font-weight: 600;
}

QLabel#hint {
    color: #7d8190;
    font-style: italic;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #4a4f5c;
    background: #23252c;
}

QCheckBox::indicator:checked {
    background: #6c5ce7;
    border: 1px solid #6c5ce7;
}

QSplitter::handle {
    background-color: #2c2f38;
}

QToolTip {
    background-color: #23252c;
    color: #e6e6ea;
    border: 1px solid #383c48;
    padding: 4px;
}
"""
