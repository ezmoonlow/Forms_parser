# -*- coding: utf-8 -*-
"""Диалог составления и отправки письма выбранным людям."""

import os

from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from settings_dialog import YandexSettingsDialog
from workers import MailSendWorker


class EmailComposeDialog(QDialog):
    def __init__(self, mail_sender, settings, columns_info, selected_rows, parent=None):
        """
        selected_rows: список (sheet_row, values, fio_str)
        """
        super().__init__(parent)
        self.mail_sender = mail_sender
        self.settings = settings
        self.columns_info = columns_info
        self.selected_rows = selected_rows
        self.attachments = []
        self.worker = None

        self.setWindowTitle("Рассылка писем")
        self.resize(520, 540)
        self.setMinimumSize(420, 420)
        self._build_ui()
        self._update_login_status()

    # ------------------------------------------------------------------ #
    def _build_ui(self):
        layout = QVBoxLayout(self)

        recipients_label = QLabel(
            f"Получателей выбрано: {len(self.selected_rows)}"
        )
        layout.addWidget(recipients_label)

        form = QFormLayout()
        self.email_col_combo = QComboBox()
        for info in self.columns_info:
            self.email_col_combo.addItem(info["label"], info["index"])
        form.addRow("Колонка с почтой:", self.email_col_combo)

        self.subject_edit = QLineEdit()
        self.subject_edit.setPlaceholderText("Тема письма")
        form.addRow("Тема:", self.subject_edit)
        layout.addLayout(form)

        layout.addWidget(QLabel("Текст письма:"))
        self.body_edit = QTextEdit()
        layout.addWidget(self.body_edit)

        attach_row = QHBoxLayout()
        attach_btn = QPushButton("Прикрепить файлы…")
        attach_btn.clicked.connect(self._add_attachments)
        remove_attach_btn = QPushButton("Убрать выбранное")
        remove_attach_btn.clicked.connect(self._remove_attachment)
        attach_row.addWidget(attach_btn)
        attach_row.addWidget(remove_attach_btn)
        layout.addLayout(attach_row)

        self.attach_list = QListWidget()
        self.attach_list.setMaximumHeight(100)
        layout.addWidget(self.attach_list)

        login_row = QHBoxLayout()
        self.login_status = QLabel("")
        self.login_btn = QPushButton("Токен и почта…")
        self.login_btn.clicked.connect(self._do_login)
        login_row.addWidget(self.login_status, stretch=1)
        login_row.addWidget(self.login_btn)
        layout.addLayout(login_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        layout.addWidget(self.log_view)

        buttons_row = QHBoxLayout()
        self.send_btn = QPushButton("Отправить")
        self.send_btn.setObjectName("primary")
        self.send_btn.clicked.connect(self._send)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        buttons_row.addWidget(self.send_btn)
        buttons_row.addWidget(close_btn)
        layout.addLayout(buttons_row)

    # ------------------------------------------------------------------ #
    def _update_login_status(self):
        if self.mail_sender.connected:
            self.login_status.setText(f"Вход по токену выполнен: {self.mail_sender.email}")
            self.login_status.setObjectName("status_ok")
        else:
            self.login_status.setText("Вход по токену не выполнен")
            self.login_status.setObjectName("status_err")
        self.login_status.setStyleSheet(self.login_status.styleSheet())

    def _do_login(self):
        dlg = YandexSettingsDialog(self.settings, self.mail_sender, self)
        dlg.exec_()
        self._update_login_status()

    def _add_attachments(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы для вложения")
        for f in files:
            if f not in self.attachments:
                self.attachments.append(f)
                self.attach_list.addItem(os.path.basename(f))

    def _remove_attachment(self):
        row = self.attach_list.currentRow()
        if row >= 0:
            self.attach_list.takeItem(row)
            del self.attachments[row]

    # ------------------------------------------------------------------ #
    def _send(self):
        if not self.mail_sender.connected:
            QMessageBox.warning(
                self,
                "Нужен вход",
                "Отправка невозможна: укажите токен и адрес почты в настройках "
                "аккаунта Яндекса и дождитесь успешной проверки.",
            )
            return

        subject = self.subject_edit.text().strip()
        body = self.body_edit.toPlainText()
        if not subject:
            QMessageBox.warning(self, "Внимание", "Укажите тему письма.")
            return

        email_col = self.email_col_combo.currentData()
        recipients = []
        for sheet_row, values, fio_str in self.selected_rows:
            email = values[email_col] if email_col < len(values) else None
            recipients.append((fio_str, email))

        self.send_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log_view.clear()

        self.worker = MailSendWorker(
            self.mail_sender, recipients, subject, body, list(self.attachments)
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.item_done.connect(self._on_item_done)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, current, total):
        pct = int(current / total * 100) if total else 0
        self.progress.setValue(pct)

    def _on_item_done(self, fio, ok, message):
        color = "#4fd18b" if ok else "#e05575"
        self.log_view.append(
            f'<span style="color:{color}">{"✔" if ok else "✘"} {fio}: {message}</span>'
        )

    def _on_finished(self, ok_count, total):
        self.send_btn.setEnabled(True)
        QMessageBox.information(
            self,
            "Готово",
            f"Отправка завершена.\nУспешно: {ok_count} из {total}.",
        )
