# -*- coding: utf-8 -*-
"""Главное окно приложения."""

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from excel_handler import ExcelHandler
from mail_sender import YandexMailSender
from settings import AppSettings
from auto_tab import AutoExportTab
from manual_tab import ManualExportTab
from list_tab import ListBroadcastTab
from settings_dialog import YandexSettingsDialog
from workers import AutoLoginWorker


class StretchTabBar(QTabBar):
    """Панель вкладок, у которой текст вкладок всегда виден полностью,
    а сами вкладки делят между собой всю ширину окна."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setElideMode(Qt.ElideNone)   # не обрезать текст «…»
        self.setUsesScrollButtons(False)
        self.setExpanding(True)

    def _text_width(self, index):
        # ширина, нужная, чтобы надпись вкладки поместилась целиком
        return QTabBar.tabSizeHint(self, index).width()

    def tabSizeHint(self, index):
        hint = super().tabSizeHint(index)
        owner = self.parentWidget()
        if owner is not None and self.count():
            share = owner.width() // self.count()
            hint.setWidth(max(self._text_width(index), share))
        return hint

    def minimumSizeHint(self):
        # окно нельзя сузить так, чтобы надписи вкладок перестали помещаться
        hint = super().minimumSizeHint()
        width = sum(self._text_width(i) for i in range(self.count()))
        return QSize(width, hint.height())


class StretchTabWidget(QTabWidget):
    """QTabWidget, который пересчитывает ширину вкладок при изменении окна."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(StretchTabBar(self))

    def resizeEvent(self, event):
        # помечаем раскладку вкладок устаревшей, чтобы они пересчитались
        # под новую ширину окна (setIconSize делает это без побочных эффектов)
        bar = self.tabBar()
        bar.setIconSize(bar.iconSize())
        super().resizeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.excel = ExcelHandler()
        self.mail_sender = YandexMailSender()

        # Настройки (адрес почты + OAuth-токен Яндекса), сохранённые ранее
        # на диск (см. core/config_manager.py), подгружаются автоматически.
        self.settings = AppSettings()
        self.settings.load()

        self.auto_login_worker = None

        self.setWindowTitle("Работа с анкетами — выгрузка файлов и рассылка")
        self.resize(920, 720)

        self._build_ui()
        self._try_silent_auto_login()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        top_bar = QHBoxLayout()
        open_btn = QPushButton("Открыть таблицу Excel…")
        open_btn.setObjectName("primary")
        open_btn.clicked.connect(self._open_table)
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setObjectName("hint")
        top_bar.addWidget(open_btn)
        top_bar.addWidget(self.file_label, stretch=1)

        # --- Кнопка в углу: OAuth-токен Яндекса + адрес почты ---
        self.account_status_label = QLabel("")
        self.account_status_label.setObjectName("hint")
        top_bar.addWidget(self.account_status_label)

        account_btn = QPushButton("⚙ Аккаунт Яндекса")
        account_btn.clicked.connect(self._open_account_settings)
        top_bar.addWidget(account_btn)

        layout.addLayout(top_bar)

        self.tabs = StretchTabWidget()
        layout.addWidget(self.tabs)

        self.auto_tab = AutoExportTab(self.excel, self.settings)
        self.manual_tab = ManualExportTab(self.excel, self.settings)
        self.list_tab = ListBroadcastTab(self.excel, self.mail_sender, self.settings)

        self.tabs.addTab(self.auto_tab, "Автоматическая выгрузка")
        self.tabs.addTab(self.manual_tab, "Ручной выбор")
        self.tabs.addTab(self.list_tab, "Список / Рассылка")

        self._update_account_status()

    # ------------------------------------------------------------------ #
    def _open_table(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть таблицу Excel", "", "Excel файлы (*.xlsx)"
        )
        if not path:
            return
        try:
            self.excel.load(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{exc}")
            return

        self.file_label.setText(path)
        self.auto_tab.refresh_columns()
        self.manual_tab.refresh_columns()
        self.list_tab.refresh_columns()

    # ------------------------------------------------------------------ #
    def _open_account_settings(self):
        dlg = YandexSettingsDialog(self.settings, self.mail_sender, self)
        dlg.exec_()
        self._update_account_status()

    def _try_silent_auto_login(self):
        """При запуске программы, если адрес почты и токен уже сохранены,
        проверяем вход в почту по токену в фоне, не блокируя интерфейс."""
        if not self.settings.has_mail_credentials():
            self._update_account_status()
            return

        self.account_status_label.setText("Почта: выполняется вход…")
        self.auto_login_worker = AutoLoginWorker(
            self.mail_sender, self.settings.yandex_email, self.settings.token
        )
        self.auto_login_worker.finished_login.connect(self._on_auto_login_finished)
        self.auto_login_worker.start()

    def _on_auto_login_finished(self, ok, err):
        self._update_account_status()
        if not ok:
            # Не мешаем пользователю модальным окном при старте — только статус.
            self.account_status_label.setText("Почта: вход не выполнен")

    def _update_account_status(self):
        parts = []
        if self.mail_sender.connected:
            parts.append(f"Почта: {self.mail_sender.email}")
        else:
            parts.append("Почта: вход не выполнен")

        parts.append(
            "Токен: указан" if self.settings.has_token() else "Токен: не указан"
        )
        self.account_status_label.setText(" · ".join(parts))
