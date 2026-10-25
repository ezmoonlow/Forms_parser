# -*- coding: utf-8 -*-
"""Фоновые потоки, чтобы интерфейс не зависал во время скачивания/отправки."""

import smtplib

from PyQt5.QtCore import QThread, pyqtSignal

import file_manager


class AutoExportWorker(QThread):
    """Автоматический режим: скачивает все ссылки в строке, кроме ФИО и Направления."""

    progress = pyqtSignal(int, int)          # (текущая, всего)
    row_done = pyqtSignal(str, bool, str)    # (ФИО, успех, сообщение)
    finished_all = pyqtSignal(int, int)      # (успешно, всего)

    def __init__(self, rows, fio_col, dir_col, upload_root, token=None, parent=None):
        super().__init__(parent)
        self.rows = rows              # список (sheet_row, values)
        self.fio_col = fio_col
        self.dir_col = dir_col
        self.upload_root = upload_root
        self.token = token  # OAuth-токен Яндекса для скачивания файлов
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        total = len(self.rows)
        ok_count = 0
        base_dir = file_manager.ensure_upload_root(self.upload_root)

        for i, (sheet_row, values) in enumerate(self.rows, start=1):
            if self._stop:
                break
            fio = values[self.fio_col] if self.fio_col < len(values) else None
            fio_str = str(fio).strip() if fio else f"без_ФИО_{sheet_row}"
            direction = (
                values[self.dir_col] if self.dir_col < len(values) else None
            )
            direction_str = str(direction).strip() if direction else "без_направления"

            tmp_dir = None
            try:
                # если папка с таким путём уже есть (или встретилась раньше
                # в этой же выгрузке) - она будет перезаписана новыми файлами
                person_dir, tmp_dir = file_manager.start_person_dir(
                    base_dir, direction_str, fio_str
                )
                downloaded = 0
                for col_idx, value in enumerate(values):
                    if col_idx in (self.fio_col, self.dir_col):
                        continue
                    # в одной ячейке может быть несколько ссылок - качаем все
                    for link in file_manager.extract_links(value):
                        # --- вызов скачивания файла (см. core/file_manager.py) ---
                        file_manager.download_file(
                            link,
                            tmp_dir,
                            base_name=None,
                            token=self.token,
                        )
                        downloaded += 1
                file_manager.finish_person_dir(person_dir, tmp_dir)
                self.row_done.emit(fio_str, True, f"Успешно, файлов: {downloaded}")
                ok_count += 1
            except Exception as exc:  # noqa: BLE001
                if tmp_dir:
                    file_manager.cancel_person_dir(tmp_dir)
                self.row_done.emit(fio_str, False, str(exc))

            self.progress.emit(i, total)

        self.finished_all.emit(ok_count, total)


class ManualExportWorker(QThread):
    """Ручной режим: скачивает только указанные пользователем колонки,
    каждая под своим заданным именем."""

    progress = pyqtSignal(int, int)
    row_done = pyqtSignal(str, bool, str)
    finished_all = pyqtSignal(int, int)

    def __init__(self, rows, fio_col, dir_col, file_columns, upload_root,
                 token=None, parent=None):
        """
        file_columns: список кортежей (индекс_колонки, имя_для_сохранения)
        """
        super().__init__(parent)
        self.rows = rows
        self.fio_col = fio_col
        self.dir_col = dir_col
        self.file_columns = file_columns
        self.upload_root = upload_root
        self.token = token  # OAuth-токен Яндекса для скачивания файлов
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        total = len(self.rows)
        ok_count = 0
        base_dir = file_manager.ensure_upload_root(self.upload_root)

        for i, (sheet_row, values) in enumerate(self.rows, start=1):
            if self._stop:
                break
            fio = values[self.fio_col] if self.fio_col < len(values) else None
            fio_str = str(fio).strip() if fio else f"без_ФИО_{sheet_row}"
            direction = (
                values[self.dir_col] if self.dir_col < len(values) else None
            )
            direction_str = str(direction).strip() if direction else "без_направления"

            tmp_dir = None
            try:
                # если папка с таким путём уже есть (или встретилась раньше
                # в этой же выгрузке) - она будет перезаписана новыми файлами
                person_dir, tmp_dir = file_manager.start_person_dir(
                    base_dir, direction_str, fio_str
                )
                downloaded = 0
                for col_idx, save_name in self.file_columns:
                    value = values[col_idx] if col_idx < len(values) else None
                    # в одной ячейке может быть несколько ссылок - качаем все,
                    # нумеруя имена: Паспорт_1, Паспорт_2, ...
                    links = file_manager.extract_links(value)
                    for n, link in enumerate(links, start=1):
                        name = save_name if len(links) == 1 else f"{save_name}_{n}"
                        # --- вызов скачивания файла (см. core/file_manager.py) ---
                        # одинаковые имена (например, у двух колонок задано одно
                        # имя) не перезаписываются: download_file добавит _1, _2
                        file_manager.download_file(
                            link,
                            tmp_dir,
                            base_name=name,
                            token=self.token,
                        )
                        downloaded += 1
                file_manager.finish_person_dir(person_dir, tmp_dir)
                self.row_done.emit(fio_str, True, f"Успешно, файлов: {downloaded}")
                ok_count += 1
            except Exception as exc:  # noqa: BLE001
                if tmp_dir:
                    file_manager.cancel_person_dir(tmp_dir)
                self.row_done.emit(fio_str, False, str(exc))

            self.progress.emit(i, total)

        self.finished_all.emit(ok_count, total)


class AutoLoginWorker(QThread):
    """Тихая проверка входа в почту по токену при запуске программы,
    используя сохранённые в настройках адрес почты и токен."""

    finished_login = pyqtSignal(bool, str)

    def __init__(self, mail_sender, email, token, parent=None):
        super().__init__(parent)
        self.mail_sender = mail_sender
        self.email = email
        self.token = token

    def run(self):
        # --- ВХОД В ПОЧТУ ПО ТОКЕНУ (см. core/mail_sender.py) ---
        ok, err = self.mail_sender.login(self.email, self.token)
        self.finished_login.emit(ok, err)


class MailSendWorker(QThread):
    """Рассылка писем выбранным людям."""

    progress = pyqtSignal(int, int)
    item_done = pyqtSignal(str, bool, str)   # (адрес/ФИО, успех, сообщение)
    finished_all = pyqtSignal(int, int)

    def __init__(self, sender, recipients, subject, body, attachments, parent=None):
        """
        recipients: список кортежей (ФИО, email)
        """
        super().__init__(parent)
        self.sender = sender
        self.recipients = recipients
        self.subject = subject
        self.body = body
        self.attachments = attachments
        self._stop = False
        self._server = None

    def stop(self):
        self._stop = True

    def _drop_connection(self):
        self.sender.close_session(self._server)
        self._server = None

    def _send_one(self, address):
        """Отправляет одно письмо через общее соединение рассылки.
        Если сервер разорвал соединение — один раз переподключается."""
        if self._server is None:
            self._server = self.sender.open_session()
        try:
            self.sender.send(
                address, self.subject, self.body, self.attachments,
                server=self._server,
            )
        except smtplib.SMTPServerDisconnected:
            self._drop_connection()
            self._server = self.sender.open_session()
            self.sender.send(
                address, self.subject, self.body, self.attachments,
                server=self._server,
            )

    def run(self):
        total = len(self.recipients)
        ok_count = 0
        self._server = None  # одно SMTP-соединение на всю рассылку
        try:
            for i, (fio, email) in enumerate(self.recipients, start=1):
                if self._stop:
                    break
                try:
                    if not email or not str(email).strip():
                        raise ValueError("не указан адрес почты")
                    self._send_one(str(email).strip())
                    self.item_done.emit(fio, True, "Отправлено")
                    ok_count += 1
                except Exception as exc:  # noqa: BLE001
                    self.item_done.emit(fio, False, str(exc))
                    # Неверный адрес получателя соединение не портит; после
                    # любой другой ошибки для следующего письма откроем новое.
                    if not isinstance(exc, (ValueError, smtplib.SMTPRecipientsRefused)):
                        self._drop_connection()
                self.progress.emit(i, total)
        finally:
            self._drop_connection()

        self.finished_all.emit(ok_count, total)
