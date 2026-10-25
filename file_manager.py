import os
import random
import re
import shutil
import string
import mimetypes
from urllib.parse import urlparse, unquote

import requests

INVALID_CHARS = r'[<>:"/\\|?*\n\r\t]'


def sanitize_name(name):
    name = "" if name is None else str(name).strip()
    name = re.sub(INVALID_CHARS, "_", name)
    name = name.strip(" .")
    return name or "unnamed"


def random_name(length=8):
    length = max(1, min(8, length))
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choices(alphabet, k=length))


def is_link(value):
    if value is None:
        return False
    return str(value).strip().lower().startswith("http")


# ссылка тянется до пробела/переноса строки или до разделителя , ; | " ' < >
LINK_RE = re.compile(r'https?://[^\s,;|"\'<>]+', re.IGNORECASE)


def extract_links(value):
    """возвращает список всех ссылок из ячейки (в ячейке их может быть несколько:
    через перенос строки, пробел, запятую или точку с запятой)"""
    if value is None:
        return []
    links = []
    for link in LINK_RE.findall(str(value)):
        link = link.rstrip(".)]")  # хвостовая пунктуация из текста
        if link not in links:
            links.append(link)
    return links


def _extension_from_headers_or_url(url, response):
    cd = response.headers.get("Content-Disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
    if m:
        fname = unquote(m.group(1))
        ext = os.path.splitext(fname)[1]
        if ext and len(ext) <= 10:
            return ext

    #путь в самой ссылке
    path = urlparse(url).path
    ext = os.path.splitext(path)[1]
    if ext and len(ext) <= 10:
        return ext
    ctype = response.headers.get("Content-Type", "").split(";")[0].strip()
    if ctype:
        guessed = mimetypes.guess_extension(ctype)
        if guessed:
            return guessed

    return ""


# ------------скачивание файлов-----------------
def download_file(url, dest_dir, base_name=None, name_max_len=8, timeout=30,
                   token=None):
    """
    скачивает файл по ссылке url в папку dest_dir
    если base_name указан - файл сохраняется под этим именем
    иначе - генерируется случайное имя
    расширение файла определяется автоматически и сохраняется как в оригинале

    token - OAuth-токен Яндекса. Ссылки на прикреплённые файлы в выгрузках
    Яндекс форм закрыты для анонимного доступа: без заголовка Authorization
    сервер Яндекса отвечает ошибкой 401/403, и файл не скачивается. Поэтому
    если токен передан, он добавляется в заголовок запроса - именно это и
    обеспечивает доступ к файлу.

    возвращает полный путь к сохранённому файлу
    """
    os.makedirs(dest_dir, exist_ok=True)

    # --------аунтификация-----------
    headers = {}
    if token:
        headers["Authorization"] = f"OAuth {token}"

    resp = requests.get(
        url, headers=headers, timeout=timeout, allow_redirects=True, stream=True
    )
    if resp.status_code in (401, 403):
        raise PermissionError(
            "Яндекс отклонил доступ к файлу (401/403). Проверьте, что токен "
            "указан в настройках аккаунта Яндекса, не просрочен и выдан с "
            "правами на Яндекс формы."
        )
    resp.raise_for_status()

    ext = _extension_from_headers_or_url(url, resp)

    if base_name:
        name = sanitize_name(base_name)
    else:
        name = random_name(name_max_len)

    filename = f"{name}{ext}"
    dest_path = os.path.join(dest_dir, filename)

    counter = 1
    stem, e = os.path.splitext(dest_path)
    while os.path.exists(dest_path):
        dest_path = f"{stem}_{counter}{e}"
        counter += 1

    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return dest_path


def ensure_person_dir(base_dir, direction, fio):
    """создаёт (если нужно) структуру выгрузка/направление/ФИО и возвращает путь"""
    d = os.path.join(base_dir, sanitize_name(direction), sanitize_name(fio))
    os.makedirs(d, exist_ok=True)
    return d


# ------------перезапись папки человека-----------------
TMP_SUFFIX = ".__загрузка__"


def start_person_dir(base_dir, direction, fio):
    """
    готовит папку выгрузка/направление/ФИО к (пере)записи
    файлы скачиваются сначала во временную папку рядом, а уже после успешного
    скачивания всех файлов она заменяет старую (см. finish_person_dir) -
    так если папка с таким же путём попадается второй раз, её содержимое
    перезаписывается новыми файлами, а при ошибке скачивания старые файлы
    остаются на месте

    возвращает (итоговая_папка, временная_папка)
    """
    final_dir = os.path.join(base_dir, sanitize_name(direction), sanitize_name(fio))
    tmp_dir = final_dir + TMP_SUFFIX
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)  # остаток от прерванной выгрузки
    os.makedirs(tmp_dir)
    return final_dir, tmp_dir


def finish_person_dir(final_dir, tmp_dir):
    """заменяет старую папку человека новой (из временной)"""
    if os.path.isdir(final_dir):
        shutil.rmtree(final_dir)
    os.rename(tmp_dir, final_dir)
    return final_dir


def cancel_person_dir(tmp_dir):
    """удаляет временную папку, если скачивание не удалось"""
    shutil.rmtree(tmp_dir, ignore_errors=True)


def ensure_upload_root(root_dir):
    """создаёт (если нужно) корневую папку 'выгрузка' внутри указанного пути"""
    path = os.path.join(root_dir, "выгрузка")
    os.makedirs(path, exist_ok=True)
    return path
