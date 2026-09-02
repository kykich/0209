"""
Точка входа консольной утилиты RTK/RTCM + DeepSeek.

Запускает пакет rtk_app (основная логика — в модуле service).

Запуск:
    python rtk_console.py
"""
from rtk_app import service


if __name__ == "__main__":
    service.main()
