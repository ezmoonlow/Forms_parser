# -*- coding: utf-8 -*-
"""Вкладка «Ручной выбор»."""

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from add_file_column_dialog import AddFileColumnDialog
from workers import ManualExportWorker


class ManualExportTab(QWidget):
    def __init__(self, excel_handler, settings, parent=None):
        super().__init__(parent)
        self.excel = excel_handler
        self.settings = settings
        self.upload_root = None
        self.file_columns = []  # список (col_index, save_name)
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Ручной режим: укажите столбец ФИО и столбец направления, затем\n"
            "добавьте любое количество пар «колонка со ссылкой -> имя файла».\n"
            "Если в ячейке несколько ссылок, скачаются все: Имя_1, Имя_2, …\n"
            "Если папка человека уже есть, она перезаписывается новыми файлами."
        )
        info.setObjectName("hint")
        info.setWordWrap(True)
        layout.addWidget(info)

        settings_box = QGroupBox("Основные столбцы")
        form = QFormLayout(settings_box)
        self.fio_col_combo = QComboBox()
        self.dir_col_combo = QComboBox()
        form.addRow("Столбец «ФИО»:", self.fio_col_combo)
        form.addRow("Столбец «Направление работы»:", self.dir_col_combo)
        layout.addWidget(settings_box)

        files_box = QGroupBox("Файлы для скачивания")
        files_layout = QVBoxLayout(files_box)
        self.files_list = QListWidget()
        files_layout.addWidget(self.files_list)

        files_buttons = QHBoxLayout()
        add_btn = QPushButton("Добавить колонку файла…")
        add_btn.clicked.connect(self._add_file_column)
        remove_btn = QPushButton("Удалить выбранную")
        remove_btn.clicked.connect(self._remove_file_column)
        files_buttons.addWidget(add_btn)
        files_buttons.addWidget(remove_btn)
        files_layout.addLayout(files_buttons)
        layout.addWidget(files_box)

        path_row = QHBoxLayout()
        self.path_label = QLabel("Папка не выбрана")
        self.path_label.setObjectName("hint")
        choose_path_btn = QPushButton("Выбрать папку выгрузки…")
        choose_path_btn.clicked.connect(self._choose_folder)
        path_row.addWidget(self.path_label, stretch=1)
        path_row.addWidget(choose_path_btn)
        layout.addLayout(path_row)

        self.start_btn = QPushButton("Начать выгрузку")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start)
        layout.addWidget(self.start_btn)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

    # ------------------------------------------------------------------ #
    def refresh_columns(self):
        self.fio_col_combo.clear()
        self.dir_col_combo.clear()
        self.files_list.clear()
        self.file_columns = []
        if not self.excel.is_loaded():
            return
        for info in self.excel.get_columns_info():
            self.fio_col_combo.addItem(info["label"], info["index"])
            self.dir_col_combo.addItem(info["label"], info["index"])
        self._columns_info = self.excel.get_columns_info()

    def _add_file_column(self):
        if not self.excel.is_loaded():
            QMessageBox.warning(self, "Внимание", "Сначала откройте таблицу Excel.")
            return
        dlg = AddFileColumnDialog(self.excel.get_columns_info(), self)
        if dlg.exec_() == QDialog.Accepted:
            self.file_columns.append((dlg.result_column_index, dlg.result_name))
            letter = self.excel.get_columns_info()[dlg.result_column_index]["letter"]
            self.files_list.addItem(f"{letter} -> {dlg.result_name}")

    def _remove_file_column(self):
        row = self.files_list.currentRow()
        if row >= 0:
            self.files_list.takeItem(row)
            del self.file_columns[row]

    def _choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Выбрать папку для выгрузки")
        if path:
            self.upload_root = path
            self.path_label.setText(path)

    def _start(self):
        if not self.excel.is_loaded():
            QMessageBox.warning(self, "Внимание", "Сначала откройте таблицу Excel.")
            return
        if not self.upload_root:
            QMessageBox.warning(self, "Внимание", "Выберите папку для выгрузки.")
            return
        if not self.file_columns:
            QMessageBox.warning(self, "Внимание", "Добавьте хотя бы одну колонку с файлом.")
            return

        if not self.settings.has_token():
            reply = QMessageBox.question(
                self,
                "Токен Яндекса не указан",
                "В настройках аккаунта Яндекса не указан токен.\n"
                "Без него ссылки на файлы, скорее всего, не скачаются.\n"
                "Всё равно продолжить?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        fio_col = self.fio_col_combo.currentData()
        dir_col = self.dir_col_combo.currentData()
        rows = self.excel.get_data_rows()
        if not rows:
            QMessageBox.information(self, "Внимание", "В таблице нет строк с данными.")
            return

        self.start_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log_view.clear()

        self.worker = ManualExportWorker(
            rows, fio_col, dir_col, list(self.file_columns), self.upload_root,
            token=self.settings.token,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.row_done.connect(self._on_row_done)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, current, total):
        pct = int(current / total * 100) if total else 0
        self.progress.setValue(pct)

    def _on_row_done(self, fio, ok, message):
        color = "#4fd18b" if ok else "#e05575"
        mark = "✔" if ok else "✘"
        self.log_view.append(f'<span style="color:{color}">{mark} {fio}: {message}</span>')

    def _on_finished(self, ok_count, total):
        self.start_btn.setEnabled(True)
        QMessageBox.information(
            self, "Готово", f"Выгрузка завершена успешно.\nОбработано: {ok_count} из {total}."
        )
