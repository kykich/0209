"""
Пакет rtk_app — логика веб-утилиты RTK/RTCM + DeepSeek.

Содержит модули:
  config      — настройки и константы;
  key_store   — чтение API-ключа;
  deepseek    — клиент DeepSeek API;
  topic       — отсечка темы вопроса через модель;
  html_report — построение HTML-ответа;
  session     — сохранение диалога.
"""

__all__ = [
    "config",
    "key_store",
    "deepseek",
    "topic",
    "html_report",
    "session",
]

__version__ = "1.0.0"
