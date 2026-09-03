"""
Настройки проекта: пути, API-эндпоинт и модель DeepSeek.
"""
import os

# Корень проекта — родитель папки, где лежит пакет rtk_app.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Папка с API-ключом DeepSeek (лежит в корне, секретно).
KEY_FILE = os.path.join(BASE_DIR, "apidpsk.txt")

# Папка состояний сессии (переносится между машинами через git).
# Это НЕ gitignore-папка: файлы сессий ездят вместе с кодом.
SESSION_DIR = os.path.join(BASE_DIR, "sessions")
SESSION_FILE = os.path.join(SESSION_DIR, "current.json")

# Endpoint и модель DeepSeek.
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# Таймаут запроса к API (в секундах).
REQUEST_TIMEOUT = 60

# --- Параметры встроенного веб-сервера ---
WEB_HOST = "127.0.0.1"
WEB_PORT = 8000

# Папка с веб-статьёй. Стартовая страница (index.html) и папки css/, js/
# находятся в корне проекта (совпадает с BASE_DIR).
WEB_ROOT = BASE_DIR

