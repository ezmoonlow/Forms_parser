import config_manager


class AppSettings:
    def __init__(self):
        self.yandex_email = ""  # почта
        self.token = ""         # OAuth-токен яндекса

    def load(self):
        data = config_manager.load_config()
        self.yandex_email = data["yandex_email"]
        self.token = data["token"]

    def save(self):
        config_manager.save_config(self.yandex_email, self.token)

    def has_token(self):
        return bool(self.token)

    def has_mail_credentials(self):
        # для отправки писем нужны и адрес почты, и токен
        return bool(self.yandex_email and self.token)
