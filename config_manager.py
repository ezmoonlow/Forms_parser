import base64
import json
import os

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".excel_manager")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

_LEGACY_KEYS = ("yandex_password", "forms_token")


def _obfuscate(value):
    if not value:
        return ""
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _deobfuscate(value):
    if not value:
        return ""
    try:
        return base64.b64decode(value.encode("ascii")).decode("utf-8")
    except Exception:  # noqa: BLE001
        return ""


def load_config():
    """читает сохранённые настройки. если файла нет — возвращает пустые значения"""
    empty = {"yandex_email": "", "token": ""}
    if not os.path.isfile(CONFIG_PATH):
        return empty

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return empty

    email = raw.get("yandex_email", "")
    token = _deobfuscate(raw.get("token", "")) or _deobfuscate(
        raw.get("forms_token", "")
    )

    if any(key in raw for key in _LEGACY_KEYS):
        try:
            save_config(email, token)
        except OSError:
            pass

    return {"yandex_email": email, "token": token}


def save_config(yandex_email, token):
    """Сохраняет настройки на диск"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    data = {
        "yandex_email": yandex_email or "",
        "token": _obfuscate(token or ""),
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONFIG_PATH, 0o600)  # только владелец (на Windows игнорируется)
    except OSError:
        pass
