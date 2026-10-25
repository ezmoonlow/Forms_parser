import os
import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from main_window import MainWindow
from styles import DARK_QSS


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    app.setApplicationName("Работа с анкетами")

    window = MainWindow()
    window.show()

    # проверка собранного .exe на сервере сборки: окно открылось - выходим
    if os.environ.get("EXCEL_MANAGER_SMOKE_TEST"):
        QTimer.singleShot(3000, app.quit)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
