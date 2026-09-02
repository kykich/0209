"""
Оркестрация рабочего процесса приложения (service-слой).

Собирает вместе настройки, клиент DeepSeek, проверку темы, интерфейс и
сохранение результата. Здесь же — сохранение HTML в папку answer/.
"""
import json
import os
import sys
import urllib.error
from datetime import datetime

from . import config, deepseek, html_report, ui
from .key_store import read_api_key
from .topic import is_related_to_rtk

__all__ = ["run", "main"]


class TopicCheckerProxy:
    """Прокси, адаптирующий функцию is_related_to_rtk(api_key, q)
    к интерфейсу, ожидаемому UI (is_related_to_rtk(q))."""

    def __init__(self, api_key):
        self._api_key = api_key

    def is_related_to_rtk(self, question):
        return is_related_to_rtk(self._api_key, question)


def save_html(question, answer, answer_format="full", output_dir=None):
    """Сохраняет ответ в HTML и возвращает путь к сохранённому файлу."""
    ts = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    out_dir = output_dir or config.OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    filename = f"deepseek_{ts.replace(' ', '_')}.html"
    path = os.path.join(out_dir, filename)
    html_content = html_report.build_html(question, answer, ts, answer_format)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return path


def open_in_browser(path):
    """Открывает файл в браузере/system viewer (Windows)."""
    try:
        if os.name == "nt":
            os.startfile(os.path.abspath(path))
    except Exception:
        pass


def run():
    """Точка входа полноценной консольной сессии.

    Возвращает код завершения (0). На ошибках печатает сообщение и завершается.
    """
    # 1. Читаем ключ
    try:
        api_key = read_api_key()
        print(f"[OK] Ключ прочитан из {config.KEY_FILE}")
    except FileNotFoundError as e:
        print(f"[ОШИБКА] {e}")
        return 1

    proxy = TopicCheckerProxy(api_key)

    # 2. Собираем вопрос (с проверкой темы через UI)
    try:
        question = ui.collect_question(proxy)
    except Exception as e:
        print(f"[ОШИБКА] {e}")
        return 1
    if question is None:
        return 0

    # 3. Выбор формата ответа
    answer_format = ui.ask_format()
    if answer_format is None:
        return 0

    # 4. Запрос к DeepSeek
    print("\n[REQ] Отправка запроса к DeepSeek...")
    try:
        answer = deepseek.ask_deepseek(api_key, question, answer_format)
        print("[OK] Ответ получен.")
    except (urllib.error.URLError, urllib.error.HTTPError,
            json.JSONDecodeError, KeyError) as e:
        answer = f"Произошла ошибка при запросе к API: {e}"
        print(f"[ERR] {e}")

    # 5. Сохранение и открытие
    path = save_html(question, answer, answer_format)
    print(f"[SAVED] Ответ сохранён: {path}")
    print("\nГотово! Файл открыт в папке answer.")
    open_in_browser(path)
    return 0


def main():
    """Обёртка над run() для запуска из командной строки."""
    sys.exit(run())

