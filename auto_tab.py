# -*- coding: utf-8 -*-
"""Вкладка «Автоматическая выгрузка»."""

from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from workers import AutoExportWorker


class AutoExportTab(QWidget):
    def __init__(self, excel_handler, settings, parent=None):
        super().__init__(parent)
        self.excel = excel_handler
        self.settings = settings
        self.upload_root = None
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Автоматический режим: ФИО берётся из первого столбца таблицы (A).\n"
            "Укажите столбец с направлением работы и папку, куда сохранить выгрузку.\n"
            "Все ссылки из остальных ячеек строки (в ячейке их может быть несколько)\n"
            "будут скачаны как файлы со случайным именем (до 8 символов) и исходным\n"
            "расширением. Если папка человека уже есть, она перезаписывается."
        )
        info.setObjectName("hint")
        info.setWordWrap(True)
        layout.addWidget(info)

        settings_box = QGroupBox("Настройки")
        form = QFormLayout(settings_box)

        self.dir_col_combo = QComboBox()
        form.addRow("Столбец «Направление работы»:", self.dir_col_combo)

        path_row = QHBoxLayout()
        self.path_label = QLabel("Папка не выбрана")
        self.path_label.setObjectName("hint")
        choose_path_btn = QPushButton("Выбрать папку выгрузки…")
        choose_path_btn.clicked.connect(self._choose_folder)
        path_row.addWidget(self.path_label, stretch=1)
        path_row.addWidget(choose_path_btn)
        form.addRow("Куда сохранять:", path_row)

        layout.addWidget(settings_box)

        self.start_btn = QPushButton("Начать выгрузку")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start)
        layout.addWidget(self.start_btn)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    # ------------------------------------------------------------------ #
    def refresh_columns(self):
        self.dir_col_combo.clear()
        if not self.excel.is_loaded():
            return
        for info in self.excel.get_columns_info():
            self.dir_col_combo.addItem(info["label"], info["index"])

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
        if self.dir_col_combo.count() == 0:
            QMessageBox.warning(self, "Внимание", "Не выбран столбец направления.")
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

        dir_col = self.dir_col_combo.currentData()
        fio_col = 0  # первый столбец, как указано в задании
        rows = self.excel.get_data_rows()
        if not rows:
            QMessageBox.information(self, "Внимание", "В таблице нет строк с данными.")
            return

        self.start_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log_view.clear()
        self.status_label.setText("")

        self.worker = AutoExportWorker(
            rows, fio_col, dir_col, self.upload_root,
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
        self.status_label.setText(f"Успешно! Обработано {ok_count} из {total}.")
        self.status_label.setObjectName("status_ok")
        self.status_label.setStyleSheet(self.status_label.styleSheet())
        QMessageBox.information(
            self, "Готово", f"Выгрузка завершена успешно.\nОбработано: {ok_count} из {total}."
        )
