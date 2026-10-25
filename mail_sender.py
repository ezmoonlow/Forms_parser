# -*- coding: utf-8 -*-
"""
Отправка писем через почту Яндекса (SMTP) по OAuth-токену.

Логин и пароль не используются. Вход выполняется командой
AUTH XOAUTH2, в которую передаются адрес почты и OAuth-токен:

    user=<адрес>\\x01auth=Bearer <токен>\\x01\\x01   (затем base64)

Что нужно от токена и ящика:
  * токен выдан с правом «Отправка писем через Яндекс почту по протоколу
    SMTP» (mail:smtp) - его отмечают при создании приложения на
    https://oauth.yandex.ru
  * адрес почты - того самого аккаунта, которому выдан токен

Рассылка идёт через одно SMTP-соединение на все письма (см. open_session /
close_session), а не с новым входом на каждое письмо
"""

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

SMTP_HOST = "smtp.yandex.com"
SMTP_PORT = 465


def build_xoauth2_string(email, token):
    """строка авторизации XOAUTH2"""
    return f"user={email}\x01auth=Bearer {token}\x01\x01"


def _explain_error(exc):
    """понятное пользователю описание ошибки входа/подключения"""
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return (
            "Яндекс не принял токен (ошибка 535). Проверьте: токен актуален "
            "и выдан с правом «Отправка писем по SMTP» (mail:smtp); адрес "
            "почты принадлежит тому же аккаунту, для которого выдан токен; "
            "в настройках Яндекс почты не запрещён доступ по протоколу SMTP."
        )
    if isinstance(exc, smtplib.SMTPConnectError):
        return f"Не удалось подключиться к серверу Яндекса: {exc}"
    if isinstance(exc, smtplib.SMTPException):
        return str(exc)
    if isinstance(exc, OSError):
        return f"Не удалось подключиться к серверу Яндекса: {exc}"
    return str(exc)


class YandexMailSender:
    def __init__(self):
        self.email = None
        self.token = None
        self.connected = False

    #---------- аунтификация по токену -------------
    @staticmethod
    def _open_connection(email, token, timeout=30):
        """открывает SMTP-соединение и входит по токену. возвращает сервер"""
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=timeout)
        try:
            server.ehlo()
            auth_string = build_xoauth2_string(email, token)

            def authobject(challenge=None):
                # Первый вызов - начальный ответ с токеном
                # Если сервер всё же прислал challenge (это JSON с описанием ошибки), отвечаем
                # пустой строкой - так по протоколу XOAUTH2 сервер завершает
                # обмен кодом 535, и smtplib выбросит SMTPAuthenticationError
                return auth_string if challenge is None else ""

            server.auth("XOAUTH2", authobject)
        except Exception:
            try:
                server.close()
            except Exception:
                pass
            raise
        return server

    def login(self, email, token):
        """
        Проверяет вход в почту по токену. Возвращает (успех: bool, сообщение_об_ошибке: str)
        При успехе запоминает адрес и токен для последующей отправки
        """
        email = (email or "").strip()
        token = (token or "").strip()
        if not token:
            self.logout()
            return False, "Токен не указан."
        if "@" not in email:
            self.logout()
            return False, (
                "Укажите адрес почты на Яндексе — он нужен для входа по токену "
                "и как адрес отправителя."
            )

        try:
            server = self._open_connection(email, token, timeout=15)
        except Exception as exc:  # noqa: BLE001
            self.connected = False
            return False, _explain_error(exc)

        self.close_session(server)
        self.email = email
        self.token = token
        self.connected = True
        return True, ""

    def logout(self):
        self.email = None
        self.token = None
        self.connected = False

    # ---------отправка------------
    def open_session(self):
        """Открывает авторизованное соединение для отправки серии писем."""
        if not self.connected:
            raise RuntimeError(
                "Отправка невозможна: не выполнен вход в почту по токену."
            )
        return self._open_connection(self.email, self.token, timeout=30)

    @staticmethod
    def close_session(server):
        if server is None:
            return
        try:
            server.quit()
        except Exception:  # noqa: BLE001
            try:
                server.close()
            except Exception:  # noqa: BLE001
                pass

    def _build_message(self, to_addr, subject, body, attachments):
        msg = EmailMessage()
        msg["From"] = self.email
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=self.email.split("@")[-1])
        msg.set_content(body or "", charset="utf-8")

        for path in attachments or []:
            if not path or not os.path.isfile(path):
                continue
            ctype, encoding = mimetypes.guess_type(path)
            # text/* без указания кодировки клиент получателя может показать
            # «кракозябрами» — вложения отдаём как бинарные, байт-в-байт.
            if ctype is None or encoding is not None or ctype.startswith("text/"):
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with open(path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=os.path.basename(path),
                )
        return msg

    def send(self, to_addr, subject, body, attachments=None, server=None):
        # отправляет одно письмо
        if not self.connected:
            raise RuntimeError(
                "Отправка невозможна: не выполнен вход в почту по токену."
            )

        msg = self._build_message(to_addr, subject, body, attachments)

        if server is not None:
            server.send_message(msg)
            return

        server = self.open_session()
        try:
            server.send_message(msg)
        finally:
            self.close_session(server)
