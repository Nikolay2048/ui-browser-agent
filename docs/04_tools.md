# Инструменты браузера (Browser Tools)

**Файл:** `src/testing_agent/tools/browser_tools.py`

Все инструменты — это LangChain `@tool` функции, которые executor получает через `llm.bind_tools(BROWSER_TOOLS)`. LLM видит имя и описание (docstring) каждого инструмента и сам решает, какой вызвать.

## Принцип работы

Каждый инструмент:
1. Получает `Page` из `BrowserManager.get_instance().page`
2. Выполняет действие через Playwright
3. Возвращает строку с результатом (успех) или строку `ERROR: ...` / `NOT_FOUND: ...` (неудача)

Executor видит результат в тексте `ToolMessage` и решает, что делать дальше.

## Приоритет локаторов

### Для кликов:
```
click_by_role(role, name)   ← Лучший: использует ARIA-семантику
click_by_text(text)         ← Хороший: по видимому тексту
click_by_css(selector)      ← Запасной: по CSS-селектору
```

### Для заполнения полей:
```
fill_by_label(label, value)       ← Лучший: по тексту label
fill_by_placeholder(ph, value)    ← Хороший: по placeholder
fill_by_css(selector, value)      ← Запасной: по CSS
```

Этот приоритет прописан в промпте executor и в промпте planner — оба агента знают его.

---

## Полный список инструментов

### navigate_to_url(url)
Переходит на URL и ждёт `domcontentloaded`. Возвращает заголовок и текущий URL.

```python
navigate_to_url("https://www.saucedemo.com/")
# → "Navigated to https://www.saucedemo.com/. Title: 'Swag Labs', URL: ..."
```

---

### get_page_context()
**Ключевой инструмент.** Возвращает JSON со структурой текущей страницы:
- `url` и `title`
- `headings` — видимые заголовки h1/h2/h3
- `alerts_messages` — сообщения об ошибках/успехе
- `interactive_elements` — до 40 элементов: кнопки, поля, ссылки

Executor вызывает этот инструмент первым делом, чтобы понять что сейчас на странице.

```json
{
  "url": "https://www.saucedemo.com/",
  "title": "Swag Labs",
  "headings": [],
  "alerts_messages": [],
  "interactive_elements": [
    "input[text]: placeholder/label='Username'",
    "input[password]: placeholder/label='Password'",
    "button: 'Login'"
  ]
}
```

---

### take_screenshot(name)
Делает скриншот viewport (не full-page). Сохраняет в `screenshots/{name}_{uuid}.png`.
Возвращает путь к файлу. Allure-репортер позже копирует его в `allure-results/`.

---

### click_by_role(role, name)
Клик по элементу с ARIA-ролью и доступным именем. Использует Playwright `get_by_role`.

```python
click_by_role("button", "Login")
click_by_role("link", "Products")
click_by_role("checkbox", "Remember me")
```

---

### click_by_text(text, exact=False)
Клик по элементу с заданным видимым текстом. `exact=False` — подстрока.

---

### click_by_css(selector)
Клик по CSS-селектору. Используется как последний резерв.

---

### fill_by_label(label, value)
Заполняет поле, найденное по тексту `<label>`. Playwright `get_by_label`.

```python
fill_by_label("Username", "standard_user")
fill_by_label("Password", "secret_sauce")
```

---

### fill_by_placeholder(placeholder, value)
Заполняет поле по атрибуту `placeholder`.

---

### fill_by_css(selector, value)
Заполняет поле по CSS-селектору.

---

### press_key(key)
Нажимает клавишу клавиатуры: `Enter`, `Tab`, `Escape`, `ArrowDown`, `Space`, `Backspace`.

---

### wait_for_text(text, timeout_ms=8000)
Ждёт появления текста на странице. Полезен после асинхронных действий.

```python
wait_for_text("Products", timeout_ms=5000)
# → "Text 'Products' appeared on page"
# или → "TIMEOUT: 'Products' did not appear within 5000ms"
```

---

### verify_text_visible(text)
Проверяет, виден ли текст прямо сейчас (без ожидания).

```python
verify_text_visible("Thank you for your order!")
# → "VISIBLE: 'Thank you for your order!' is visible"
# или → "NOT_VISIBLE: '...' is NOT visible on page"
```

---

### verify_element_visible(selector)
Проверяет видимость элемента по CSS-селектору.

---

### get_element_text(selector)
Возвращает текст элемента по CSS-селектору. Полезен для проверки содержимого конкретного элемента.

---

### select_option(selector, value)
Выбирает опцию в `<select>` по тексту или значению атрибута value.

```python
select_option(".sort-container select", "Price (low to high)")
```

---

### scroll_page(direction)
Прокрутка страницы. Варианты: `up`, `down`, `top`, `bottom`.

---

### mark_step_complete(status, actual_result, screenshot_name="")

**Специальный инструмент-сигнал.** Обязан быть последним в каждом шаге.

```python
mark_step_complete(
    status="passed",
    actual_result="Пользователь перенаправлен на /inventory.html, заголовок 'Products' виден",
    screenshot_name="step1_products_page"
)
```

**Как работает:**
1. Делает финальный скриншот (если указан `screenshot_name`)
2. Сохраняет результат в `BrowserManager._last_step_result`
3. Возвращает `STEP_COMPLETE::passed::actual_result`
4. Executor обнаруживает это и завершает ReAct-цикл

**Статусы:**
- `passed` — шаг выполнен, ожидаемый результат достигнут
- `failed` — шаг выполнен, но результат не совпал с ожидаемым
- `broken` — невозможно выполнить (ошибка инструмента, элемент не найден)
