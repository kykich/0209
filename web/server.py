"""
Встроенный HTTP-сервер (стандартная библиотека: http.server и ssl не нужны).

Стартовая страница (index.html) и ассеты css/, js/ находятся в корне проекта.
Сервер реализует JSON-API:
    GET  /              — главная страница (index.html из корня);
    GET  /css/*,/js/*   — стили и скрипты;
    GET  /static/*      — то же, для совместимости;
    GET  /api/model     — информация о модели (для подвала);
    POST /api/ask       — принять вопрос, проверить тему, получить ответ.

Запрос к внешнему DeepSeek выполняется на сервере в момент POST /api/ask.
"""
import json
import mimetypes
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rtk_app import config, deepseek, html_report, session as session_io
from rtk_app.topic import is_related_to_rtk

# Подсказки для случаев, когда вопрос вне темы геодезии/RTK.
TIPS = [
    "Какие бывают виды RTK-поправок",
    "Что такое базовые и референц-станции в геодезии",
    "Чем отличается тахеометр от GNSS-приёмника",
    "Отличия поправок CMR, CMR+ и RTCM",
    "Как выполняется нивелирование / определение высот",
    "Что такое MSM-поправки в RTCM",
]

class _ServerState:
    """Общее состояние между обработчиками: ключ API и блокировка сессии."""
    api_key = ""
    lock = threading.Lock()


class WebRequestHandler(BaseHTTPRequestHandler):
    server_version = "RTKWeb/1.0"

    # ------------------------------------------------------------------ #
    # Служебное
    # ------------------------------------------------------------------ #
    def _send_bytes(self, status, body, content_type):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, payload, "application/json; charset=utf-8")

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def log_message(self, fmt, *args):
        # Более краткое логирование (убираем многословный dump в консоль).
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    # ------------------------------------------------------------------ #
    # Маршрутизация
    # ------------------------------------------------------------------ #
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # Главная страница — index.html из корня проекта
        if path in ("/", "/index.html"):
            return self._serve_static_safe("index.html")

        # css/js (основные пути SPA): /css/style.css и /js/app.js
        if path.startswith(("/css/", "/js/")):
            return self._serve_static_safe(path.lstrip("/"))

        # совместимость со старым префиксом /static/*
        if path.startswith("/static/"):
            return self._serve_static_safe(os.path.normpath(path[len("/static/"):]))

        if path == "/api/model":
            return self._send_json(200, {"ok": True, "model": config.MODEL})

        # Состояние сессии: сколько реплик уже накоплено (для индикатора)
        if path == "/api/state":
            history = session_io.load()
            turns = sum(1 for m in history if m.get("role") in ("user", "assistant"))
            return self._send_json(200, {
                "ok": True,
                "exists": bool(history),
                "turns": turns,
            })
        self._send_json(404, {"ok": False, "error": "Not Found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/ask":
            return self._handle_ask()
        if parsed.path == "/api/reset":
            return self._handle_reset()
        self._send_json(404, {"ok": False, "error": "Not Found"})

    # ------------------------------------------------------------------ #
    # Сессия
    # ------------------------------------------------------------------ #
    def _handle_reset(self):
        """Сбрасывает текущую сессию (новый разговор)."""
        with _ServerState.lock:
            session_io.reset()
        return self._send_json(200, {"ok": True, "on_topic": True})

    # ------------------------------------------------------------------ #
    # Статика (отдаёт только index.html и ассеты из css/, js/)
    # ------------------------------------------------------------------ #
    ALLOWED_TOP = ("index.html", "css", "js")

    def _serve_static_safe(self, rel):
        """Отдаёт файл rel относительно WEB_ROOT с ограничением доступа.

        Разрешается только стартовая страница index.html и содержимое папок
        css/ и js/. Это защищает исходники проекта (rtk_app/, web/ и т.д.)
        от раздачи посторонним по URL.
        """
        root = config.WEB_ROOT
        root_real = os.path.realpath(root)

        # нормализуем путь и не даём выйти за пределы корня
        rel_norm = os.path.normpath(rel)
        full = os.path.realpath(os.path.join(root, rel_norm))
        if not (full.startswith(root_real + os.sep) or full == root_real):
            return self._send_bytes(403, "Forbidden", "text/plain")

        # разрешены только index.html и css/, js/
        top = rel_norm.split(os.sep, 1)[0]
        if rel_norm != "index.html" and top not in ("css", "js"):
            return self._send_bytes(403, "Forbidden", "text/plain")

        if not os.path.isfile(full):
            return self._send_bytes(404, "Not Found", "text/plain")

        ctype, _ = mimetypes.guess_type(full)
        ctype = ctype or "application/octet-stream"
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------------ #
    # Бизнес-логика: вопрос -> DeepSeek
    # ------------------------------------------------------------------ #
    def _handle_ask(self):
        data = self._read_json_body()
        if not data:
            return self._send_json(400, {"ok": False, "error": "Некорректный JSON."})

        question = str(data.get("question", "")).strip()
        if not question:
            return self._send_json(400, {"ok": False, "error": "Вопрос пустой."})

        answer_format = data.get("format", "full")
        if answer_format not in ("short", "full"):
            answer_format = "full"

        api_key = _ServerState.api_key

        # 1) Проверка темы
        on_topic = is_related_to_rtk(api_key, question)
        if not on_topic:
            return self._send_json(200, {
                "ok": True,
                "on_topic": False,
                "message": "Вопрос не по теме (не про геодезию и RTK-поправки).",
                "tips": TIPS,
            })

        # 2) Продолжаем диалог: грузим историю сессии из файла
        with _ServerState.lock:
            history = session_io.load()
            # Если сессии ещё нет — начинаем новый разговор с этим вопросом
            if not history or history[0].get("role") != "system":
                system = deepseek.build_system(question)
                history = [{"role": "system", "content": system}]
            user_content = deepseek.build_user_message(question, answer_format)
            history.append({"role": "user", "content": user_content})

        # 3) Запрос к DeepSeek с полной историей (продолжает разговор)
        try:
            answer = deepseek.chat(api_key, history)
        except Exception as exc:  # noqa: BLE001
            return self._send_json(200, {
                "ok": False,
                "error": f"Ошибка запроса к DeepSeek: {exc}",
            })

        # 4) Записываем ответ модели и сохраняем сессию на диск
        with _ServerState.lock:
            history.append({"role": "assistant", "content": answer})
            session_io.save(history)

        # 5) Сборка страницы ответа
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            # Показываем только содержимое ответа (без повторной обёртки в полный
            # документ) — используем подмножество функций html_report.
            answer_fragment = html_report.text_to_html_paragraphs(answer)
        except Exception:  # noqa: BLE001
            answer_fragment = "<p>Не удалось отформатировать ответ.</p>"

        meta = (f"Сгенерировано: {ts} · Модель: {config.MODEL} · "
                f"Формат: {'короткий' if answer_format == 'short' else 'полный'}")

        return self._send_json(200, {
            "ok": True,
            "on_topic": True,
            "html": answer_fragment,
            "meta": meta,
            "question": question,
            "answer_format": answer_format,
        })


def create_server(api_key, host=None, port=None):
    """Создаёт и возвращает настроенный ThreadingHTTPServer."""
    _ServerState.api_key = api_key
    addr = (host or config.WEB_HOST, port or config.WEB_PORT)
    httpd = ThreadingHTTPServer(addr, WebRequestHandler)
    return httpd


def _open_browser_later(url, delay=1.0):
    """Через задержку открывает url в браузере (в фоновом потоке)."""
    def _job():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            print(f"[WEB] Не удалось открыть браузер: {exc}")
    threading.Thread(target=_job, daemon=True).start()


def serve(api_key, host=None, port=None, open_page=True):
    """Запускает сервер в синхронном режиме (блокирующий вызов).

    Если open_page=True, автоматически открывает стартовую страницу,
    после чего продолжает обслуживать запросы к модели (/api/ask).
    """
    httpd = create_server(api_key, host, port)
    shown_host, shown_port = httpd.server_address[:2]
    url = f"http://{shown_host}:{shown_port}/"
    print(f"[WEB] Сервер запущен: {url}")
    if open_page:
        _open_browser_later(url)
    print("[WEB] Открыт стартовая страница. Нажмите Ctrl+C для остановки.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[WEB] Остановка сервера…")
    finally:
        httpd.server_close()


def main():
    """Точка запуска сервера из командной строки."""
    import sys

    from rtk_app.key_store import read_api_key

    try:
        api_key = read_api_key()
        print(f"[OK] Ключ прочитан из {config.KEY_FILE}")
    except FileNotFoundError as e:
        print(f"[ОШИБКА] {e}")
        sys.exit(1)

    # Опциональные аргументы: порт, хост
    args = sys.argv[1:]
    host, port = config.WEB_HOST, config.WEB_PORT
    if args and args[0].isdigit():
        port = int(args[0])
        if len(args) > 1:
            host = args[1]

    sys.exit(serve(api_key, host, port) or 0)
