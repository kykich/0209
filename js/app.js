/* Клиентская логика SPA: отправка вопроса, статус, вывод ответа. */
(function () {
    "use strict";

    var qEl = document.getElementById("question");
    var submit = document.getElementById("submit");
    var statusEl = document.getElementById("status");
    var resultEl = document.getElementById("result");
    var tipsEl = document.getElementById("tips");
    var tipsList = document.getElementById("tips-list");
    var modelEl = document.getElementById("model");

    function setStatus(message, kind) {
        statusEl.hidden = !message;
        statusEl.textContent = message || "";
        statusEl.className = "status" + (kind ? " " + kind : "");
    }

    function showResult(html, extraMeta) {
        resultEl.innerHTML =
            '<h2>Ответ</h2>' + (extraMeta ? '<div class="meta-line">' + extraMeta + "</div>" : "") +
            '<div class="answer-block">' + html + "</div>";
        resultEl.hidden = false;
    }

    function showTips(tips) {
        tipsList.innerHTML = "";
        tips.forEach(function (tip) {
            var li = document.createElement("li");
            li.textContent = "• " + tip;
            tipsList.appendChild(li);
        });
        tipsEl.hidden = false;
    }

    function resetOutput() {
        resultEl.hidden = true;
        resultEl.innerHTML = "";
        tipsEl.hidden = true;
    }

    async function ask() {
        var question = qEl.value.trim();
        if (!question) {
            setStatus("Введите текст вопроса.", "error");
            return;
        }

        var formatEl = document.querySelector("input[name='format']:checked");
        var format = formatEl ? formatEl.value : "full";

        submit.disabled = true;
        resetOutput();
        setStatus("Проверяю тему вопроса…", "");

        try {
            var resp = await fetch("/api/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: question, format: format })
            });

            // Перед чтением JSON — если ответ не JSON, показываем тех. ошибку
            var data;
            try {
                data = await resp.json();
            } catch (e) {
                setStatus("Сервер вернул некорректный ответ (возможно, истёк таймаут запроса к DeepSeek).", "error");
                return;
            }

            if (!data.ok) {
                setStatus(data.error || "Произошла ошибка.", "error");
                return;
            }

            if (data.on_topic === false) {
                setStatus(data.message || "Вопрос не по теме (не про RTK-поправки).", "error");
                if (data.tips && data.tips.length) showTips(data.tips);
                else tipsEl.hidden = true;
                return;
            }

            setStatus("Отправляю запрос к DeepSeek…", "");
            // Достаём результат (запрос уже выполнен на сервере)
            setStatus("", "");
            showResult(data.html || "", data.meta || "");
        } catch (err) {
            setStatus("Ошибка связи с сервером: " + err.message, "error");
        } finally {
            submit.disabled = false;
            refreshSessionNote();
        }
    }

    submit.addEventListener("click", ask);
    qEl.addEventListener("keydown", function (ev) {
        if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") ask();
    });

    // Кнопка «Закончить» — закрыть вкладку.
    // Браузеры позволяют window.close() только для вкладок, открытых самим
    // скриптом. Поэтому пробуем разные способы и, если ничего не вышло,
    // сообщаем пользователю закрыть вкладку вручную.
    var finish = document.getElementById("finish");
    if (finish) {
        finish.addEventListener("click", function () {
            finish.disabled = true;
            tryCloseWindow();
        });
    }

    function tryCloseWindow() {
        try {
            // Способ 1: прямой вызов (работает для вкладок, открытых этим скриптом)
            window.close();
        } catch (e) { /* игнорируем */ }

        // Проверяем через короткий интервал, закрылось ли окно
        setTimeout(function () {
            try {
                if (!window.closed) {
                    // Способ 2: открыть пустую страницу в этой вкладке и закрыть её
                    // (работает в некоторых случаях).
                    window.open("", "_self");
                    window.close();
                }
            } catch (e) { /* игнорируем */ }

            setTimeout(function () {
                if (!window.closed) {
                    setStatus(
                        "Браузер не дал закрыть вкладку программно. " +
                        "Закройте её вручную (крестик вкладки).",
                        "error"
                    );
                    if (finish) finish.disabled = false;
                }
            }, 150);
        }, 150);
    }

    // Индикатор состояния сессии + кнопка «Новый разговор»
    var newchat = document.getElementById("newchat");
    var noteEl = document.getElementById("session-note");

    function setSessionNote(text) {
        if (noteEl) noteEl.textContent = text || "";
    }

    function refreshSessionNote() {
        if (!noteEl) return;
        fetch("/api/state")
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                if (!d) { setSessionNote(""); return; }
                var t = d.turns || 0;
                if (t <= 0) setSessionNote("Новый разговор пока не начат.");
                else setSessionNote("Разговор продолжается: сохранено реплик: " + t + ".");
            })
            .catch(function () { setSessionNote(""); });
    }

    if (newchat) {
        newchat.addEventListener("click", function () {
            fetch("/api/reset", { method: "POST" })
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function () {
                    resetOutput();
                    setStatus("Начат новый разговор. История сессии очищена.", "ok");
                    refreshSessionNote();
                })
                .catch(function () {
                    setStatus("Не удалось сбросить сессию.", "error");
                });
        });
    }

    refreshSessionNote();

    // Показать модель в подвале (она отдаётся на главной странице одним запросом)
    fetch("/api/model")
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (d && d.model) modelEl.textContent = d.model; })
        .catch(function () { modelEl.textContent = ""; });
})();

