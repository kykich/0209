"""
Пакет rtk_app — консольная утилита RTK/RTCM + DeepSeek.

Содержит модули:
  config      — настройки и константы;
  key_store   — чтение API-ключа;
  deepseek    — клиент DeepSeek API;
  topic       — проверка темы вопроса;
  html_report — построение HTML-ответа;
  ui          — консольный пользовательский интерфейс;
  service     — оркестрация всего рабочего процесса.
"""

__all__ = [
    "config",
    "key_store",
    "deepseek",
    "topic",
    "html_report",
    "ui",
    "service",
]

__version__ = "1.0.0"
