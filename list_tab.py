# -*- coding: utf-8 -*-
"""Вкладка «Список / Рассылка»: просмотр строк таблицы, выбор нескольких
записей (как выбор сообщений в мессенджере для пересылки), удаление
выбранных строк и рассылка писем выбранным людям."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from email_dialog import EmailComposeDialog


class ListBroadcastTab(QWidget):
    def __init__(self, excel_handler, mail_sender, settings, parent=None):
        super().__init__(parent)
        self.excel = excel_handler
        self.mail_sender = mail_sender
        self.settings = settings
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top_box = QGroupBox("Отображение")
        form = QFormLayout(top_box)
        self.dir_col_combo = QComboBox()
        self.dir_col_combo.currentIndexChanged.connect(self.refresh_rows)
        form.addRow("Столбец «Направление» для показа:", self.dir_col_combo)
        layout.addWidget(top_box)

        select_row = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать всё")
        select_all_btn.clicked.connect(self._select_all)
        select_none_btn = QPushButton("Снять выделение")
        select_none_btn.clicked.connect(self._select_none)
        select_row.addWidget(select_all_btn)
        select_row.addWidget(select_none_btn)
        select_row.addStretch(1)
        layout.addLayout(select_row)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Выбор", "ФИО", "Направление"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.table)

        actions_row = QHBoxLayout()
        self.selected_label = QLabel("Выбрано: 0")
        actions_row.addWidget(self.selected_label)
        actions_row.addStretch(1)

        delete_btn = QPushButton("Удалить выбранные")
        delete_btn.setObjectName("danger")
        delete_btn.clicked.connect(self._delete_selected)
        actions_row.addWidget(delete_btn)

        mail_btn = QPushButton("Написать письмо выбранным")
        mail_btn.setObjectName("primary")
        mail_btn.clicked.connect(self._compose_mail)
        actions_row.addWidget(mail_btn)

        layout.addLayout(actions_row)

    # ------------------------------------------------------------------ #
    def refresh_columns(self):
        self.dir_col_combo.blockSignals(True)
        self.dir_col_combo.clear()
        if self.excel.is_loaded():
            for info in self.excel.get_columns_info():
                self.dir_col_combo.addItem(info["label"], info["index"])
        self.dir_col_combo.blockSignals(False)
        self.refresh_rows()

    def refresh_rows(self):
        self.table.setRowCount(0)
        if not self.excel.is_loaded():
            self._update_selected_count()
            return

        dir_col = self.dir_col_combo.currentData()
        rows = self.excel.get_data_rows()
        self.table.setRowCount(len(rows))

        for r, (sheet_row, values) in enumerate(rows):
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Unchecked)
            checkbox_item.setData(Qt.UserRole, sheet_row)
            self.table.setItem(r, 0, checkbox_item)

            fio_val = values[0] if len(values) > 0 else ""
            fio_item = QTableWidgetItem(str(fio_val) if fio_val is not None else "")
            fio_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(r, 1, fio_item)

            direction_val = ""
            if dir_col is not None and dir_col < len(values):
                direction_val = values[dir_col]
            dir_item = QTableWidgetItem(str(direction_val) if direction_val is not None else "")
            dir_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(r, 2, dir_item)

        self._update_selected_count()

    # ------------------------------------------------------------------ #
    def _on_item_clicked(self, item):
        row = item.row()
        checkbox_item = self.table.item(row, 0)
        if item.column() != 0:
            # клик по любой ячейке строки тоже переключает выбор — как в мессенджере
            new_state = (
                Qt.Unchecked if checkbox_item.checkState() == Qt.Checked else Qt.Checked
            )
            checkbox_item.setCheckState(new_state)
        self._update_selected_count()

    def _select_all(self):
        for r in range(self.table.rowCount()):
            self.table.item(r, 0).setCheckState(Qt.Checked)
        self._update_selected_count()

    def _select_none(self):
        for r in range(self.table.rowCount()):
            self.table.item(r, 0).setCheckState(Qt.Unchecked)
        self._update_selected_count()

    def _update_selected_count(self):
        count = sum(
            1
            for r in range(self.table.rowCount())
            if self.table.item(r, 0) and self.table.item(r, 0).checkState() == Qt.Checked
        )
        self.selected_label.setText(f"Выбрано: {count}")

    def _get_selected(self):
        """Возвращает список (sheet_row, values, fio_str) для отмеченных строк."""
        selected = []
        rows = dict(self.excel.get_data_rows())
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item and item.checkState() == Qt.Checked:
                sheet_row = item.data(Qt.UserRole)
                values = rows.get(sheet_row, [])
                fio_str = self.table.item(r, 1).text() or f"строка_{sheet_row}"
                selected.append((sheet_row, values, fio_str))
        return selected

    # ------------------------------------------------------------------ #
    def _delete_selected(self):
        selected = self._get_selected()
        if not selected:
            QMessageBox.information(self, "Внимание", "Ничего не выбрано.")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить {len(selected)} выбранных строк из таблицы?\n"
            f"Изменения будут сохранены в файл.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        sheet_rows = [s[0] for s in selected]
        self.excel.delete_rows_by_sheet_index(sheet_rows)
        self.refresh_rows()
        QMessageBox.information(self, "Готово", "Выбранные строки удалены.")

    def _compose_mail(self):
        if not self.excel.is_loaded():
            QMessageBox.warning(self, "Внимание", "Сначала откройте таблицу Excel.")
            return
        selected = self._get_selected()
        if not selected:
            QMessageBox.information(self, "Внимание", "Ничего не выбрано.")
            return

        dlg = EmailComposeDialog(
            self.mail_sender, self.settings, self.excel.get_columns_info(), selected, self
        )
        dlg.exec_()
