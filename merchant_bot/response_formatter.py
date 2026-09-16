import re

# Порядок секций, которые бот обычно выдаёт (см. system_prompt.py, пункт 26).
SECTION_ORDER = ["SITUATION", "STRATEGY", "REPLY", "OPTIONAL"]

# Только эти секции оборачиваем в код-блок (```), чтобы Discord показал
# иконку "копировать" рядом с сообщением для покупателя.
COPYABLE_SECTIONS = {"REPLY", "OPTIONAL", "ALT REPLY"}

# Заголовок = короткая строка (или начало строки до ":"), где каждое слово
# начинается с заглавной буквы, без обычной пунктуации предложения.
# Это работает для "SITUATION", "REPLY", а также для любых заголовков,
# которые модель придумывает сама (NEXT MOVE, STATE AFTER THIS, DEAL STAGE и т.п.) —
# не нужно перечислять их все руками.
_INLINE_HEADER_RE = re.compile(
    r"^(?P<header>[A-ZА-Яa-zа-я][A-ZА-Яa-zа-я /]{1,40}?)\s*[:\u2014\u2013-]\s*(?P<rest>.*)$"
)
# Заголовок сам по себе, без ':'/'—' после него — модель иногда пишет просто "REPLY" отдельной строкой.
_BARE_HEADER_RE = re.compile(r"^(?P<header>[A-ZА-Яa-zа-я][A-ZА-Яa-zа-я /]{1,40})$")

# Фразы-подводки к альтернативному варианту ответа, который модель не всегда
# оформляет отдельным заголовком OPTIONAL, а просто дописывает после REPLY.
_ALT_LABEL_RE = re.compile(r"^(?P<label>.{1,60}?):\s*(?P<rest>.*)$")
_ALT_LABEL_KEYWORDS = (
    "if you want", "if he", "if she", "if they", "softer", "shorter",
    "alternative", "alt version", "another option", "instead", "different tone",
)


def _strip_markdown(text: str) -> str:
    """Убирает markdown-разметку (**жирный**, *курсив*, `код`), чтобы то,
    что клиент скопирует, не содержало лишних звёздочек/бэктиков."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    return text


def _strip_wrapping_quotes(text: str) -> str:
    """Модель иногда сама оборачивает готовую реплику в кавычки
    ("...", «...», '...') — для копирования это лишнее, убираем."""
    text = text.strip()
    pairs = [('"', '"'), ("«", "»"), ("'", "'"), ("\u201c", "\u201d")]
    for left, right in pairs:
        if text.startswith(left) and text.endswith(right) and len(text) >= 2:
            text = text[len(left):-len(right)].strip()
            break
    return text


def _strip_blockquote_markers(text: str) -> str:
    """Модель иногда оформляет реплику как markdown-цитату (каждая строка
    начинается с '>'). Для копипаста это лишний символ — убираем построчно,
    заодно подчищаем висящие пробелы в конце строк (markdown "разрыв строки")."""
    lines = [re.sub(r"^\s{0,3}>\s?", "", line).rstrip() for line in text.splitlines()]
    return "\n".join(lines)


def _strip_leading_label(text: str) -> str:
    """Убирает вступление-подводку вроде 'send this:', 'reply with:', 'say:',
    если модель добавила его первой строкой перед самим текстом реплики."""
    lines = text.splitlines()
    if len(lines) < 2:
        return text
    first = lines[0].strip()
    if first.endswith(":") and len(first) <= 40 and not any(ch in first for ch in "?!"):
        return "\n".join(lines[1:]).strip()
    return text


def _clean_copyable(text: str) -> str:
    text = _strip_markdown(text)
    text = _strip_blockquote_markers(text)
    text = _strip_leading_label(text).strip()
    text = _strip_wrapping_quotes(text)
    return text


def _is_valid_header_text(header: str) -> bool:
    words = header.split()
    if not words:
        return False
    if any(ch in header for ch in ",.!?"):
        return False
    return all(w[0].isupper() for w in words)


def _header_candidate(line: str) -> tuple[str, str] | None:
    stripped = _strip_markdown(line).strip(" *_>#-\t")

    match = _INLINE_HEADER_RE.match(stripped)
    if match:
        header = match.group("header").strip()
        rest = match.group("rest").strip()
        if _is_valid_header_text(header):
            return header.upper(), rest
        return None

    bare = _BARE_HEADER_RE.match(stripped)
    if bare:
        header = bare.group("header").strip()
        if _is_valid_header_text(header):
            return header.upper(), ""

    return None


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Возвращает список (SECTION_NAME, content) в порядке появления в тексте."""
    sections: list[tuple[str, list[str]]] = []

    for line in text.splitlines():
        candidate = _header_candidate(line)
        if candidate:
            name, rest = candidate
            sections.append((name, [rest] if rest else []))
        elif sections:
            sections[-1][1].append(line)
        # строки до первого распознанного заголовка отбрасываются намеренно —
        # такого в промпте быть не должно, но на всякий случай не ломаем формат

    return [(name, "\n".join(content).strip()) for name, content in sections]


def _primary_and_trailing(content: str) -> tuple[str, str]:
    """Первый абзац — это готовое сообщение для копирования и отправки клиенту.
    Всё, что дальше (альтернативные формулировки, пояснения мерчанту),
    в код-блок не идёт — это не для копирования 1-в-1."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    if not paragraphs:
        return "", ""
    return paragraphs[0], "\n\n".join(paragraphs[1:])


def _looks_like_alt_label(label: str) -> bool:
    lower = label.lower()
    return any(kw in lower for kw in _ALT_LABEL_KEYWORDS)


def _promote_alt_reply_to_optional(
    sections: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    """Модель не всегда ставит отдельный заголовок для альтернативной
    формулировки реплики — часто просто дописывает абзац вида
    'If you want it more direct: ...' сразу после REPLY.

    Вытаскиваем такой абзац в отдельную копируемую секцию:
    - если в ответе НЕТ настоящего OPTIONAL (follow-up/операционная заметка) —
      называем вытащенный абзац OPTIONAL, как обычно;
    - если OPTIONAL уже есть и означает что-то своё (например, что писать,
      если покупатель не ответит) — называем вытащенный абзац ALT REPLY,
      чтобы два разных сообщения не склеились в один код-блок для копирования."""
    has_explicit_optional = any(name == "OPTIONAL" for name, _ in sections)

    result: list[tuple[str, str]] = []
    for name, content in sections:
        if name != "REPLY":
            result.append((name, content))
            continue

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
        if len(paragraphs) < 2:
            result.append((name, content))
            continue

        primary = paragraphs[0]
        rest_paragraphs = []
        extracted = None

        for p in paragraphs[1:]:
            lines = p.splitlines()
            first_line = _strip_markdown(lines[0]).strip()
            match = _ALT_LABEL_RE.match(first_line)
            if extracted is None and match and _looks_like_alt_label(match.group("label")):
                inline_rest = match.group("rest").strip()
                body = "\n".join([inline_rest] + lines[1:]).strip()
                if body:
                    extracted = body
                    continue
            rest_paragraphs.append(p)

        result.append(("REPLY", "\n\n".join([primary] + rest_paragraphs)))
        if extracted:
            label = "ALT REPLY" if has_explicit_optional else "OPTIONAL"
            result.append((label, extracted))

    return result


def format_reply(raw_text: str) -> str:
    sections = _split_sections(raw_text)
    if not sections:
        return _strip_markdown(raw_text).strip()

    sections = _promote_alt_reply_to_optional(sections)

    parts = []
    for name, content in sections:
        if not content:
            continue

        if name in COPYABLE_SECTIONS:
            primary, trailing = _primary_and_trailing(content)
            primary = _clean_copyable(primary)
            if primary:
                parts.append(f"**{name.title()}**\n```\n{primary}\n```")
            if trailing:
                parts.append(_strip_markdown(trailing).strip())
        else:
            clean = _strip_markdown(content).strip()
            parts.append(f"**{name.title()}** — {clean}")

    return "\n\n".join(parts)