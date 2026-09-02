"""
Построение HTML-документа с текстом вопроса и ответа.
Включает: экранирование, парсинг Markdown-таблиц, сборку полной страницы.
"""
import re

from . import config

__all__ = ["escape_html", "build_html"]


def escape_html(text):
    """Экранирует спецсимволы для безопасного отображения в HTML."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def parse_markdown_table_block(lines, start_idx):
    """Собирает строки Markdown-таблицы, начиная с start_idx, в HTML-таблицу.

    Возвращает кортеж (html_таблица, индекс_последней_обработанной_строки).
    """
    header_cells = [c.strip().replace("**", "") for c in lines[start_idx].strip("|").split("|")]
    i = start_idx
    rows = []

    # Пропускаем разделительную строку (например, |---|---|---|)
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
    justify_css = "text-align: justify;" if answer_format == "full" else ""

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
    <div class="meta">Сгенерировано: {ts} &nbsp;•&nbsp; Модель: {config.MODEL}</div>

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
