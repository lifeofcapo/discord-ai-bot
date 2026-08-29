import re

CORE_SECTIONS = ["SITUATION", "STRATEGY", "REPLY", "OPTIONAL"]

SECTION_ORDER = CORE_SECTIONS

COPYABLE_SECTIONS = {"REPLY", "OPTIONAL"}

def _title_or_upper(word: str) -> str:
    return f"{word[0]}(?:{word[1:]}|{word[1:].lower()})"


SECTION_PATTERN = "|".join(_title_or_upper(w) for w in SECTION_ORDER)
_SECTION_HEADER_RE = re.compile(
    r"(?:^|(?<=[\.\!\?\s]))(?P<name>" + SECTION_PATTERN + r")\s*(?:[—\-:]\s*)?",
    re.MULTILINE,
)


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Возвращает список (SECTION_NAME, content) в порядке появления в тексте."""
    matches = list(_SECTION_HEADER_RE.finditer(text))
    if not matches:
        return []

    sections = []
    for i, match in enumerate(matches):
        name = match.group("name").upper()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        sections.append((name, content))
    return sections


def _strip_existing_code_fence(text: str) -> str:
    return re.sub(r"```[a-zA-Z]*\n?|```", "", text).strip()


def _split_copyable_and_trailing(content: str) -> tuple[str, str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    if not paragraphs:
        return content, ""

    def looks_like_reply(paragraph: str) -> bool:
        if len(paragraph) > 240:
            return False
        lowered = paragraph.lower()
        developer_markers = (
            "if you want", "i can also", "i can draft", "let me know if",
            "depending on", "would you like",
        )
        return not any(marker in lowered for marker in developer_markers)

    copyable_paragraphs = []
    trailing_paragraphs = []
    hit_trailing = False

    for paragraph in paragraphs:
        if not hit_trailing and looks_like_reply(paragraph):
            copyable_paragraphs.append(paragraph)
        else:
            hit_trailing = True
            trailing_paragraphs.append(paragraph)

    if not copyable_paragraphs:
        copyable_paragraphs = [paragraphs[0]]
        trailing_paragraphs = paragraphs[1:]

    return "\n\n".join(copyable_paragraphs), "\n\n".join(trailing_paragraphs)


def format_reply(raw_text: str) -> str:
    sections = _split_sections(raw_text)
    if not sections:
        return raw_text

    parts = []
    for name, content in sections:
        if not content:
            continue
        if name in COPYABLE_SECTIONS:
            content = _strip_existing_code_fence(content)
            copyable, trailing = _split_copyable_and_trailing(content)
            parts.append(f"**{name.title()}**\n```\n{copyable}\n```")
            if trailing:
                parts.append(trailing)
        else:
            parts.append(f"**{name.title()}** — {content}")

    return "\n\n".join(parts)