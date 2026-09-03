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


# Ролевые установки (персона) в зависимости от выбранного формата ответа.
# Прикладываются к КАЖДОМУ запросу, чтобы персона следовала формату даже при
# переключении посреди сессии. Все три уверенно дают корректный ответ по
# геодезии, отличаясь широтой знаний, глубиной разбора и профессиональной
# терминологией.
_ROLE_PRESETS = {
    "short": (
        "Отвечай как самообучающийся новичок в геодезии: хорошо знаешь "
        "классическую геодезию (теодолит, нивелир, тахеометр, ходы, "
        "топосъёмку) и мало разбираешься в GPS/GNSS. Отвечай коротко, "
        "просто и доступно, без сложной спутниковой терминологии."
    ),
    "medium": (
        "Отвечай как техник-геодезист: уверенно владеешь классической "
        "геодезией и знаешь GPS/GNSS в общих чертах, но не разбираешься "
        "во внутренней работе RTK-поправок. Отвечай умеренно подробно, "
        "с ясными практическими пояснениями."
    ),
    "full": (
        "Отвечай как опытный специалист-геодезист: хорошо знаешь "
        "классическую геодезию, уверенно владеешь GPS/GNSS с применением "
        "RTK и имеешь опыт сочетания классических и спутниковых методов. "
        "Отвечай развёрнуто и профессионально, допустима специальная "
        "терминология и примеры из практики."
    ),
}

# Общий потолок объёма для любого формата (~100 коротких строк по ~30 знаков).
_MAX_LEN_HINT = (
    "Укладывай ответ в объём не более примерно 100 коротких строк "
    "(около 3000 знаков). Можно короче — главное, не превышай этот предел."
)


def build_role_system(answer_format="full"):
    """Системный промпт — персона, заданная выбранным форматом.

    Роль выбирается из трёх возможных персон (новичок/техник/специалист)
    по переданному answer_format. Перед каждым запросом системный промпт
    переустанавливается на актуальную роль (в т.ч. при смене формата в
    середине диалога), а в содержании роли задан общий потолок объёма.
    """
    role = _ROLE_PRESETS.get(answer_format, _ROLE_PRESETS["full"])
    return f"{role} {_MAX_LEN_HINT}"


def build_system(answer_format="full"):
    """Системный промпт по роли/формату (обратная совместимость)."""
    return build_role_system(answer_format)


def build_user_message(question, answer_format="full"):
    """Пользовательское сообщение — просто сам вопрос.

    Персона и ограничение объёма идут из системного промпта (роли),
    поэтому в реплику пользователя дополнительных подсказок не добавляем.
    Возвращается строка, готовая к отправке роли 'user'.
    """
    _ = answer_format  # роль задаётся системным промптом по answer_format
    return question


def ask_deepseek(api_key, question, answer_format="full"):
    """Отправляет вопрос к DeepSeek с подходящими ролями-системой.

    answer_format: 'short' — новичок; 'medium' — техник; 'full' — специалист.

    Системный промпт формируется ролью, соответствующей выбранному формату,
    чтобы стиль и глубина ответа соответствовали выбранной персоне.
    """
    system_content = build_role_system(answer_format)
    user_content = build_user_message(question, answer_format)
    return ask_deepseek_raw(api_key, system_content, user_content)
