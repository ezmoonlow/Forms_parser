# -*- coding: utf-8 -*-
"""Диалог добавления пары «колонка со ссылкой -> имя сохраняемого файла» (ручной режим)."""

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class AddFileColumnDialog(QDialog):
    def __init__(self, columns_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить колонку с файлом")
        self.setMinimumWidth(380)
        self.columns_info = columns_info
        self.result_column_index = None
        self.result_name = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.column_combo = QComboBox()
        for info in self.columns_info:
            self.column_combo.addItem(info["label"], info["index"])
        form.addRow("Колонка со ссылкой:", self.column_combo)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: Диплом, Паспорт, Согласие")
        form.addRow("Название для файла:", self.name_edit)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("Добавить")
        ok_btn.setObjectName("primary")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Введите название!")
            return
        self.result_column_index = self.column_combo.currentData()
        self.result_name = name
        self.accept()
