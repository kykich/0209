"""
Консольная утилита: ввод вопроса свободным текстом.
Спрашивает DeepSeek и сохраняет ответ в HTML (папка answer).
"""
import os
import re
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime

# --- Настройки ---
API_URL = "https://api.deepseek.com/chat/completions"

# Папка, где лежит сам .py-файл. ОТ всех путей будем отталкиваться от неё.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

KEY_FILE = os.path.join(BASE_DIR, "apidpsk.txt")   # файл ключа — рядом со скриптом
OUTPUT_DIR = os.path.join(BASE_DIR, "answer")       # папка для HTML — рядом со скриптом
MODEL = "deepseek-chat"

def read_api_key(filename):
    """Читает API-ключ из текстового файла."""
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Файл {filename} не найден. Создайте его и вставьте туда ваш API-ключ."
        )
    with open(filename, "r", encoding="utf-8") as f:
        return f.read().strip()


def ask_deepseek_raw(api_key, system_content, user_content):
    """Отправляет запрос к DeepSeek и возвращает текст ответа."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "stream": False
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data_bytes, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as response:
        resp_data = response.read().decode("utf-8")
    data = json.loads(resp_data)
    return data["choices"][0]["message"]["content"]


# Ключевые слова для быстрой проверки темы (англ., рус., транслит)
TOPIC_KEYWORDS = [
    # английские
    "rtk", "rtcm", "gnss", "cmr", "msm",
    # русские / транслит
    "поправк", "поправка", "коррекц", "цмр", "ртцм", "ртк", "гнсс",
    "спутник", "сателлит", "базовые станции", "базовая станция",
    "референц", "эфемерид", "координат", "фазовые наблюдения",
    "псевдодальност", "дифференциальн"
]


def contains_topic_keyword(question):
    """Быстрая проверка по ключевым словам (учитывает заглавные, рус., транслит)."""
    q = question.lower()
    return any(kw in q for kw in TOPIC_KEYWORDS)


def is_related_to_rtk(api_key, question):
    """Определяет, относится ли вопрос к RTK-поправкам.
    Сначала — быстрая проверка по словам, затем — проверка через DeepSeek."""
    # 1) Быстрая проверка по ключевым словам (включая русские/транслит)
    if contains_topic_keyword(question):
        return True

    # 2) Если слов не нашлось — спрашиваем DeepSeek (учитывает синонимы/смысл)
    system_content = (
        "Ты — модератор тем. Определи, относится ли вопрос пользователя к RTK-поправкам "
        "(RTK, RTCM, GNSS, CMR, поправки от базовой станции, эфемериды, координаты "
        "референц-станции и т.п.). Учитывай русские и транслит-варианты названий "
        "(например, ЦМР = CMR, РТЦМ = RTCM, РТК = RTK). "
        "Ответь ровно одним словом: ДА (если относится) или НЕТ (если не относится)."
    )
    try:
        answer = ask_deepseek_raw(api_key, system_content, question).strip()
        return answer.upper().startswith("ДА")
    except (urllib.error.URLError, urllib.error.HTTPError,
            json.JSONDecodeError, KeyError, Exception):
        # При ошибке — считаем вопрос подходящим, чтобы заблокировать запуск
        return True


def select_type(api_key):
    """Возвращает вопрос, введённый пользователем вручную, или None при выходе."""
    print("\n" + "=" * 64)
    print("   КОНСОЛЬНАЯ УТИЛИТА — запрос к DeepSeek")
    print("=" * 64)
    print("\nВведите свой вопрос свободным текстом.")
    print("(0 или пустая строка — выход)\n")
    while True:
        try:
            question = input("Ваш вопрос: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            return None

        if question == "0":
            print("Выход.")
            return None

        if not question:
            print("   ! Введите текст вопроса.\n")
            continue

        # Свернуть многострочный вставленный текст в одну строку
        question = " ".join(question.split())

        # Проверка — по теме ли вопрос (слова → DeepSeek)
        print("   [CHECK] Проверяю тему вопроса...")
        if not is_related_to_rtk(api_key, question):
            print("\n   ❌ Вопрос не по теме (не про RTK-поправки).")
            # Подсказки для переформулирования вопроса (про виды RTK-поправок)
            print("\n   💡 Подсказки — вопросы про виды RTK-поправок:")
            for tip in [
                "Какие бывают виды RTK-поправок",
                "Отличия поправок CMR, CMR+ и RTCM",
                "Виды поправок: координаты станции, эфемериды, наблюдения",
                "Что такое MSM-поправки в RTCM",
                "Источники RTK-поправок (базовая станция, сети, спутники)",
            ]:
                print(f"      • {tip}")
            # Спрашиваем, повторить ли запрос
            while True:
                try:
                    again = input("\n   Повторить запрос? (1-да / 2-нет): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n   Выход.")
                    return None
                if again == "1":
                    print()
                    break  # возвращаемся к вводу нового вопроса
                elif again == "2":
                    print("   Выход.")
                    return None
                else:
                    print("   ! Введите 1 или 2.")
            continue

        return question


def escape_html(text):
    """Экранирует спецсимволы для безопасного отображения в HTML."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def parse_markdown_table_block(lines, start_idx):
    """Собирает строки Markdown-таблицы, начиная с start_idx, и возвращает HTML-таблицу."""
    header_cells = [c.strip().replace("**", "") for c in lines[start_idx].strip("|").split("|")]
    i = start_idx
    rows = []

    # Пропускаем разделительную строку (например, |---|-----|)
    j = start_idx + 1
    if j < len(lines) and re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", lines[j]):
        j += 1

    for k in range(j, len(lines)):
        line = lines[k].strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)

    table_html = ["<table>", "<thead><tr>"]
    for idx, h in enumerate(header_cells):
        if idx == 1:
            table_html.append(f"<th class='desc-col'>{h}</th>")
        else:
            table_html.append(f"<th>{h}</th>")
    table_html.append("</tr></thead><tbody>")
    for row in rows:
        table_html.append("<tr>")
        for idx, cell in enumerate(row):
            if idx == 0:
                table_html.append(f"<td class='date-col'>{cell}</td>")
            elif idx == 1:
                table_html.append(f"<td class='desc-col'>{cell}</td>")
            elif idx == 2:
                table_html.append(f"<td class='size-col'>{cell}</td>")
            else:
                table_html.append(f"<td>{cell}</td>")
        table_html.append("</tr>")
    table_html.append("</tbody></table>")

    return "\n".join(table_html), j - 1


def text_to_html_paragraphs(text):
    """Разбивает текст на абзацы, списки и Markdown-таблицы."""
    text = escape_html(text)
    lines = text.split("\n")
    html = []
    in_list = False
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # Если строка — начало Markdown-таблицы (содержит "|")
        if line.strip().startswith("|") and "|" in line[1:]:
            if in_list:
                html.append("</ul>")
                in_list = False
            table_html, i = parse_markdown_table_block(lines, i)
            html.append(table_html)
            i += 1
            continue

        if not line:
            if in_list:
                html.append("</ul>")
                in_list = False
            i += 1
            continue

        if line.startswith("### "):
            if in_list:
                html.append("</ul>")
                in_list = False
            html.append(f"<h4>{line[4:]}</h4>")
        elif line.startswith("## "):
            if in_list:
                html.append("</ul>")
                in_list = False
            html.append(f"<h3>{line[3:]}</h3>")
        elif line.startswith("# "):
            if in_list:
                html.append("</ul>")
                in_list = False
            html.append(f"<h2>{line[2:]}</h2>")
        elif line.strip().startswith("- "):
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{line.strip()[2:]}</li>")
        elif re.match(r"^\d+\.\s", line.strip()):
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{re.sub(r'^\d+\.\s', '', line.strip())}</li>")
        else:
            if in_list:
                html.append("</ul>")
                in_list = False
            html.append(f"<p>{line}</p>")

        i += 1

    if in_list:
        html.append("</ul>")

    return "\n".join(html)


def build_html(question, answer, ts, answer_format="full"):
    """Формирует полный HTML-документ."""
    q_html = text_to_html_paragraphs(question)
    a_html = text_to_html_paragraphs(answer)

    # При полном ответе — выравнивание 2-го столбца по ширине
    justify_css = ""
    if answer_format == "full":
        justify_css = "text-align: justify;"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ответ DeepSeek — {ts}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
            line-height: 1.6;
            color: #2c3e50;
            background: #f9f9fb;
        }}
        h1 {{
            color: #1a1a2e;
            border-bottom: 3px solid #4d6bfe;
            padding-bottom: 10px;
        }}
        .meta {{
            color: #888;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
        .block {{
            background: #fff;
            border-radius: 10px;
            padding: 25px 30px;
            margin-bottom: 25px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            border-left: 5px solid #2ecc71;
        }}
        .block.question {{
            border-left-color: #4d6bfe;
        }}
        .block h2 {{
            margin-top: 0;
            color: #34495e;
            font-size: 1.3em;
        }}
        h3 {{ color: #4d6bfe; }}
        h4 {{ color: #663399; }}
        ul {{ padding-left: 25px; }}
        li {{ margin-bottom: 6px; }}
        code {{
            background: #f0f0f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.92em;
        }}
        pre {{
            background: #282c34;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        .error {{
            background: #fee;
            border-left-color: #e74c3c;
            color: #c0392b;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 0.95em;
            background: #fff;
        }}
        th {{
            background: #4d6bfe;
            color: #fff;
            text-align: center;
            padding: 10px 12px;
            border: 1px solid #4d6bfe;
        }}
        td {{
            padding: 9px 12px;
            border: 1px solid #e0e0e8;
            vertical-align: top;
        }}
        tr:nth-child(even) td {{
            background: #f7f8fc;
        }}
        .date-col {{
            white-space: nowrap;
            font-weight: 600;
            color: #1a1a2e;
        }}
        .desc-col {{
            width: 80%;
            {justify_css}
        }}
        .size-col {{
            text-align: center;
            white-space: nowrap;
            font-weight: 600;
            color: #663399;
        }}
    </style>
</head>
<body>
    <h1>Ответ DeepSeek API</h1>
    <div class="meta">Сгенерировано: {ts} &nbsp;•&nbsp; Модель: {MODEL}</div>

    <div class="block question">
        <h2>Вопрос</h2>
        {q_html}
    </div>

    <div class="block">
        <h2>Ответ</h2>
        {a_html}
    </div>
</body>
</html>"""


def ask_format():
    """Спрашивает, в каком виде выдать ответ: короткий или полный.
    Возвращает 'short' или 'full'. Возвращает None при выходе."""
    while True:
        print("\nВ каком виде выдать ответ?")
        print("   1 — короткий")
        print("   2 — полный")
        try:
            choice = input("Ваш выбор (1-2): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            return None
        if choice == "1":
            return "short"
        elif choice == "2":
            return "full"
        else:
            print("   ! Введите 1 или 2.\n")


def ask_deepseek(api_key, question, answer_format="full"):
    """Отправляет запрос к DeepSeek и возвращает строку ответа."""
    # Дополнительная инструкция по формату ответа
    if answer_format == "short":
        format_note = (
            "Давай КРАТКИЙ ответ: описание каждой поправки — не более 10 слов."
        )
    else:
        format_note = (
            "Давай ПОЛНЫЙ ответ: подробное описание каждой поправки. "
            "Текст во 2-м столбце выравнивай по ширине (justify)."
        )

    system_content = (
        "Ты — эксперт по GNSS, RTK и RTCM. Отвечай подробно на русском. "
        "Всегда сортируй RTK-поправки по времени их появления (от самой ранней к самой поздней), "
        "а при одинаковом времени — по размеру поправки (по возрастанию). "
        f"{format_note} "
        "Оформляй ответ в виде Markdown-таблицы из трёх столбцов: "
        "1-й столбец — дата появления RTK-поправки, 2-й столбец — называется "
        "\"Описание версии\" (текст об этой поправке), "
        "3-й столбец — размер поправки в байтах."
    )
    return ask_deepseek_raw(api_key, system_content, question)


def save_html(question, answer, answer_format="full"):
    """Сохраняет ответ в HTML и возвращает путь к файлу."""
    ts = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"deepseek_{ts.replace(' ', '_')}.html"
    path = os.path.join(OUTPUT_DIR, filename)
    html_content = build_html(question, answer, ts, answer_format)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return path


def main():
    # 1. Читаем ключ
    try:
        api_key = read_api_key(KEY_FILE)
        print(f"[OK] Ключ прочитан из {KEY_FILE}")
    except FileNotFoundError as e:
        print(f"[ОШИБКА] {e}")
        sys.exit(1)

    # 2. Выбор и запрос
    question = select_type(api_key)
    if question is None:
        return

    # 3. Выбор формата ответа
    answer_format = ask_format()
    if answer_format is None:
        return

    print("\n[REQ] Отправка запроса к DeepSeek...")
    try:
        answer = ask_deepseek(api_key, question, answer_format)
        print("[OK] Ответ получен.")
    except (urllib.error.URLError, urllib.error.HTTPError,
            json.JSONDecodeError, KeyError) as e:
        answer = f"Произошла ошибка при запросе к API: {e}"
        print(f"[ERR] {e}")

    path = save_html(question, answer, answer_format)
    print(f"[SAVED] Ответ сохранён: {path}")
    print("\nГотово! Файл открыт в папке answer.")
    try:
        os.startfile(os.path.abspath(path)) if os.name == "nt" else None
    except Exception:
        pass


if __name__ == "__main__":
    main()
