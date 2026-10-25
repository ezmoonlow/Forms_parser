# -*- coding: utf-8 -*-
"""
Окно настроек аккаунта Яндекса.

Здесь пользователь один раз вводит:
  - OAuth-токен Яндекса — он используется и для скачивания файлов из
    Яндекс.Форм, и для отправки писем по SMTP;
  - адрес почты — нужен для входа по токену и как адрес отправителя.

Пароль от почты не нужен и нигде не запрашивается.

После нажатия «Сохранить и проверить» данные записываются на диск
(core/config_manager.py) и при следующем запуске программы подставляются
автоматически — вводить их заново не нужно.

Окно небольшое, но свободно растягивается (не имеет фиксированного размера).
"""

from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class YandexSettingsDialog(QDialog):
    def __init__(self, settings, mail_sender, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.mail_sender = mail_sender

        self.setWindowTitle("Аккаунт Яндекса")
        self.resize(460, 320)
        self.setMinimumSize(380, 280)

        self._build_ui()
        self._load_from_settings()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        token_hint = QLabel(
            "Один OAuth-токен Яндекса используется для всего: скачивания файлов\n"
            "из Яндекс.Форм и отправки писем. Токен должен быть выдан с правами\n"
            "на Яндекс.Формы и «Отправка писем по протоколу SMTP» (mail:smtp).\n"
            "Пароль от почты не нужен."
        )
        token_hint.setObjectName("hint")
        token_hint.setWordWrap(True)
        layout.addWidget(token_hint)

        form = QFormLayout()
        self.token_edit = QLineEdit()
        self.token_edit.setPlaceholderText("OAuth-токен Яндекса")
        self.token_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Токен:", self.token_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("login@yandex.ru")
        form.addRow("Почта:", self.email_edit)
        layout.addLayout(form)

        email_hint = QLabel(
            "Почта — адрес того аккаунта, для которого выдан токен (это адрес\n"
            "отправителя). Нужна только для рассылки; для скачивания файлов\n"
            "достаточно одного токена."
        )
        email_hint.setObjectName("hint")
        email_hint.setWordWrap(True)
        layout.addWidget(email_hint)

        show_row = QHBoxLayout()
        self.show_secrets_chk = QCheckBox("Показать токен")
        self.show_secrets_chk.stateChanged.connect(self._toggle_secrets_visibility)
        show_row.addWidget(self.show_secrets_chk)
        show_row.addStretch(1)
        layout.addLayout(show_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons_row = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить и проверить")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        buttons_row.addWidget(self.save_btn)
        buttons_row.addWidget(close_btn)
        layout.addLayout(buttons_row)

    def _toggle_secrets_visibility(self, state):
        mode = QLineEdit.Normal if state else QLineEdit.Password
        self.token_edit.setEchoMode(mode)

    def _load_from_settings(self):
        self.email_edit.setText(self.settings.yandex_email)
        self.token_edit.setText(self.settings.token)

    def _set_status(self, text, kind=""):
        self.status_label.setText(text)
        self.status_label.setObjectName(kind)
        self.status_label.setStyleSheet(self.status_label.styleSheet())

    def _save(self):
        email = self.email_edit.text().strip()
        token = self.token_edit.text().strip()

        self.settings.yandex_email = email
        self.settings.token = token
        self.settings.save()  # <-- сохранение на диск, подставится при следующем запуске

        if not token:
            self.mail_sender.logout()
            self._set_status("Токен не указан — скачивание файлов и рассылка недоступны.", "hint")
            return

        if not email:
            self.mail_sender.logout()
            self._set_status(
                "Токен сохранён — скачивание файлов доступно. Для рассылки "
                "укажите ещё адрес почты.",
                "hint",
            )
            return

        self.save_btn.setEnabled(False)
        self._set_status("Проверка входа в почту по токену…")
        QApplication.processEvents()

        # --- ВХОД В ПОЧТУ ПО ТОКЕНУ (см. core/mail_sender.py) ---
        ok, err = self.mail_sender.login(email, token)
        self.save_btn.setEnabled(True)

        if ok:
            self._set_status(f"Сохранено. Вход в почту по токену выполнен: {email}", "status_ok")
        else:
            self._set_status(
                f"Настройки сохранены, но вход в почту не удался: {err}", "status_err"
            )
            QMessageBox.warning(self, "Ошибка входа в почту", str(err))
