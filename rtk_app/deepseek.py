"""
Клиент для работы с DeepSeek API (chat completions).
"""
import json
import urllib.error
import urllib.request

from . import config

# Импортируется для удобства обработки ошибок в вызывающем коде.
__all__ = [
    "ask_deepseek_raw", "ask_deepseek",
    "chat", "build_system", "build_user_message",
]


def chat(api_key, messages):
    """Отправляет произвольный список сообщений и возвращает текст ответа.

    messages — список словарей {"role": "...", "content": "..."}.
    Может выбросить urllib.error.URLError / HTTPError / json.JSONDecodeError.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.MODEL,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        config.API_URL, data=data_bytes, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=config.REQUEST_TIMEOUT) as response:
        resp_data = response.read().decode("utf-8")
    data = json.loads(resp_data)
    return data["choices"][0]["message"]["content"]


def ask_deepseek_raw(api_key, system_content, user_content):
    """Удобная обёртка: один вопрос в новой сессии.

    Может выбросить urllib.error.URLError / HTTPError / json.JSONDecodeError.
    """
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    return chat(api_key, messages)


# Ключевые слова, явно указывающие на запрос именно про RTK/RTCM/CMR-поправки.
_RTK_FOCUS_KEYWORDS = [
    "rtk", "rtcm", "цмр", "ртцм", "ртк", "поправк", "поправка", "cmr", "msm",
    "дифференциальн", "референц", "базовая станция", "базовые станции",
]


def _is_rtk_focused(question):
    """True, если вопрос сфокусирован на RTK/RTCM-поправках,
    а не на наземной геодезии в целом."""
    q = question.lower()
    return any(kw in q for kw in _RTK_FOCUS_KEYWORDS)


def _build_rtk_system_prompt(answer_format):
    """Системный промпт для узкой темы «версии RTK-поправок»."""
    if answer_format == "short":
        format_note = (
            "Давай КРАТКИЙ ответ: описание каждой поправки — не более 10 слов."
        )
    else:
        format_note = (
            "Давай ПОЛНЫЙ ответ: подробное описание каждой поправки. "
            "Текст во 2-м столбце выравнивай по ширине (justify)."
        )

    return (
        "Ты — эксперт по GNSS/RTK и геодезии. Отвечай подробно на русском. "
        "Всегда сортируй RTK-поправки по времени их появления (от самой ранней к самой поздней), "
        "а при одинаковом времени — по размеру поправки (по возрастанию). "
        f"{format_note} "
        "Оформляй ответ в виде Markdown-таблицы из трёх столбцов: "
        "1-й столбец — дата появления RTK-поправки, 2-й столбец — называется "
        "\"Описание версии\" (текст об этой поправке), "
        "3-й столбец — размер поправки в байтах."
    )


def _build_general_system_prompt(answer_format):
    """Системный промпт для общей геодезии (наземной, инженерной, спутниковой).

    Здесь нет навязанной таблицы «версий поправок», чтобы модель могла
    свободно и глубоко ответить, например, про теодолит.
    """
    if answer_format == "short":
        style = "Отвечай КРАТКО, сжато и по делу."
    else:
        style = "Отвечай ПОЛНО и подробно, с объяснениями и примерами."

    return (
        "Ты — профессиональный геодезист-эксперт с большим опытом в наземной, "
        "инженерной, спутниковой и прикладной геодезии. Отвечай на русском языке. "
        "Ты прекрасно знаешь классические геодезические приборы (теодолит, нивелир, "
        "тахеометр, дальномер, буссоль, штатив, веха, рейка) и современные "
        "GNSS-приёмники, а также методы измерений: углов, расстояний, превышений, "
        "координат, разбивочные работы, топосъёмку, нивелирование, полярный и "
        "линейно-угловой ход, полигонометрию, триангуляцию. "
        f"{style} "
        "Если вопрос касается RTK/RTCM-поправок или сравнения их версий — оформи "
        "ответ таблицей (дата появления, описание, размер). В остальных случаях "
        "отвечай связным текстом, используя при необходимости списки. "
        "Излагай грамотно, понятно и по существу."
    )


def build_system(question):
    """Системный промпт для сессии по характеру первого вопроса.

    Не зависит от ответа/формата — используется один раз для сессии.
    """
    if _is_rtk_focused(question):
        return _build_rtk_system_prompt("full")
    return _build_general_system_prompt("full")


def build_user_message(question, answer_format="full"):
    """Пользовательское сообщение с подсказкой желаемой длины ответа.

    answer_format: 'short' — кратко, иначе 'full' — подробно.
    Возвращается строка, готовая к отправке роли 'user'.
    """
    reminder = (
        (", ПОЖАЛУЙСТА, ОТВЕТЬ КРАТКО (не растягивай описание)" if answer_format == "short"
         else ", ПОЖАЛУЙСТА, ОТВЕТЬ ПОДРОБНО")
    )
    return question + reminder


def ask_deepseek(api_key, question, answer_format="full"):
    """Отправляет вопрос к DeepSeek с подходящим системным промптом.

    answer_format: 'short' — короткий ответ, иначе 'full' — полный.

    Для узких вопросов про RTK/RTCM-поправки используется специализированный
    промпт с таблицей версий; для остальной геодезии — общий геодезический
    системный промпт без навязанного формата.
    """
    system_content = build_system(question)
    user_content = build_user_message(question, answer_format)
    return ask_deepseek_raw(api_key, system_content, user_content)
