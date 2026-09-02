"""
Консольный пользовательский интерфейс.

Отвечает только за ввод-вывод в терминале: заголовок, выбор вопроса,
подсказки, выбор формата ответа. Не содержит бизнес-логики.
"""

# Подсказки для переформулирования вопроса (если вопрос вне темы геодезии/RTK)
TIPS = [
    "Какие бывают виды RTK-поправок",
    "Что такое базовые и референц-станции в геодезии",
    "Чем отличается тахеометр от GNSS-приёмника",
    "Отличия поправок CMR, CMR+ и RTCM",
    "Как выполняется нивелирование / определение высот",
    "Что такое MSM-поправки в RTCM",
]


def print_header():
    """Печатает шапку утилиты."""
    print("\n" + "=" * 64)
    print("   КОНСОЛЬНАЯ УТИЛИТА — запрос к DeepSeek")
    print("=" * 64)


def input_line(prompt):
    """Считывает строку из stdin, обрабатывая EOF/прерывание клавиатуры.

    Возвращает строку или None при выходе пользователем.
    """
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nВыход.")
        return None


def ask_format():
    """Спрашивает, короткий или полный ответ.

    Возвращает 'short', 'full' или None при выходе.
    """
    while True:
        print("\nВ каком виде выдать ответ?")
        print("   1 — короткий")
        print("   2 — полный")
        choice = input_line("Ваш выбор (1-2): ")
        if choice is None:
            return None
        choice = choice.strip()
        if choice == "1":
            return "short"
        if choice == "2":
            return "full"
        print("   ! Введите 1 или 2.\n")


def collect_question(topic_checker):
    """Предлагает пользователю ввести вопрос свободным текстом.

    topic_checker — функция/объект с методом is_related(question),
    возвращающая True, если вопрос по теме.

    Возвращает текст вопроса или None при выходе.
    """
    print_header()
    print("\nВведите свой вопрос свободным текстом.")
    print("(0 или пустая строка — выход)\n")

    # topic_checker должен быть объектом с методом is_related_to_rtk
    check = topic_checker

    while True:
        raw = input_line("Ваш вопрос: ")
        if raw is None:
            return None
        question = raw.strip()

        if question == "0":
            print("Выход.")
            return None
        if not question:
            print("   ! Введите текст вопроса.\n")
            continue

        # Свернуть многострочный вставленный текст в одну строку
        question = " ".join(question.split())

        # Проверка темы
        print("   [CHECK] Проверяю тему вопроса...")
        if not check.is_related_to_rtk(question):
            print("\n   ❌ Вопрос не по теме (не про геодезию и RTK-поправки).")
            print("\n   💡 Подсказки — вопросы по геодезии и видам RTK-поправок:")
            for tip in TIPS:
                print(f"      • {tip}")
            # Спрашиваем, повторить ли запрос
            if not _confirm_retry():
                return None
            continue

        return question


def _confirm_retry():
    """Спрашивает, повторить ли запрос. Возвращает True/False/None."""
    while True:
        ans = input_line("\n   Повторить запрос? (1-да / 2-нет): ")
        if ans is None:
            print("   Выход.")
            return False
        ans = ans.strip()
        if ans == "1":
            return True
        if ans == "2":
            print("   Выход.")
            return False
        print("   ! Введите 1 или 2.")
