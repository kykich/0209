"""
Управление состоянием сессии диалога.

Цель — переносить "состояние разговора" с моделью между машинами вместе
с кодом через git. Каждая машина хранит последнюю сессию в файле
sessions/current.json, а те, кто работает над проектом одновременно,
добавляют этот файл в коммит (это обычный JSON, без секретов).

Формат сообщений полностью совпадает с тем, что DeepSeek ожидает в
messages[]: список словарей {"role": "...", "content": "..."}. Первым
элементом лежит system-промпт сессии (он стабилен в течение разговора),
далее пары user/assistant.

Только сериализация. Никакой бизнес-логики и сетевых вызовов.
"""
import json
import os

from . import config

# "Роль" по которой модель идентифицирует себя в сессии.
DEFAULT_SYSTEM = (
    "Ты — профессиональный геодезист-эксперт по наземной, инженерной и "
    "спутниковой геодезии. Отвечай на русском языке. Если вопрос про "
    "RTK/RTCM-поправки — оформи ответ таблицей (дата появления, описание, "
    "размер). В остальных случаях отвечай связным текстом и списками."
)

__all__ = [
    "load", "save", "reset", "path", "ensure_system",
]


def _ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def path():
    """Возвращает путь к файлу текущей сессии."""
    return config.SESSION_FILE


def load(file_path=None):
    """Читает список сообщений сессии. Если файла нет/битый — пустой список.

    Возвращает корректный список сообщений (роль+содержимое).
    """
    file_path = file_path or config.SESSION_FILE
    if not os.path.isfile(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return [
            m for m in data
            if isinstance(m, dict) and m.get("role") and isinstance(m.get("content"), str)
        ]
    except (json.JSONDecodeError, OSError):
        return []


def save(messages, file_path=None):
    """Сохраняет список сообщений сессии (перезаписывает файл)."""
    if not isinstance(messages, list):
        messages = []
    messages = [
        m for m in messages
        if isinstance(m, dict) and m.get("role") and isinstance(m.get("content"), str)
    ]
    file_path = file_path or config.SESSION_FILE
    _ensure_dir(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def ensure_system(messages, system_content=None):
    """Гарантирует, что первый элемент списка — system-промпт сессии.

    Возвращает (messages, is_new). Если сессия пустая, кладём system первой
    записью и помечаем как новую (is_new=True). Новая сессия создаётся только
    при первом вопросе цикла.
    """
    system_content = system_content or DEFAULT_SYSTEM
    if messages and messages[0].get("role") == "system":
        return messages, False
    # создаём новую сессию с этим system-промптом
    new_list = [{"role": "system", "content": system_content}] + list(messages)
    return new_list, True


def reset(file_path=None):
    """Удаляет файл текущей сессии (начинает с чистого листа)."""
    file_path = file_path or config.SESSION_FILE
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
