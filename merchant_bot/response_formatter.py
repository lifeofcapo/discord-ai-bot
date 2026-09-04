import re

SECTION_ORDER = ["SITUATION", "STRATEGY", "REPLY", "OPTIONAL"]

COPYABLE_SECTIONS = {"REPLY", "OPTIONAL"}

_INLINE_HEADER_RE = re.compile(
    r"^(?P<header>[A-ZА-Яa-zа-я][A-ZА-Яa-zа-я /]{1,40}?):\s*(?P<rest>.*)$"
)


def _strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    return text


def _header_candidate(line: str) -> tuple[str, str] | None:
    stripped = _strip_markdown(line).strip(" *_>#-\t")
    match = _INLINE_HEADER_RE.match(stripped)
    if not match:
        return None
    header = match.group("header").strip()
    rest = match.group("rest").strip()
    words = header.split()
    if not words:
        return None
    if any(ch in header for ch in ",.!?"):
        return None
    if not all(w[0].isupper() for w in words):
        return None
    return header.upper(), rest


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

    return [(name, "\n".join(content).strip()) for name, content in sections]


def _primary_and_trailing(content: str) -> tuple[str, str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    if not paragraphs:
        return "", ""
    return paragraphs[0], "\n\n".join(paragraphs[1:])


def format_reply(raw_text: str) -> str:
    sections = _split_sections(raw_text)
    if not sections:
        return _strip_markdown(raw_text).strip()

    parts = []
    for name, content in sections:
        if not content:
            continue

        if name in COPYABLE_SECTIONS:
            primary, trailing = _primary_and_trailing(content)
            primary = _strip_markdown(primary).strip()
            if primary:
                parts.append(f"**{name.title()}**\n```\n{primary}\n```")
            if trailing:
                parts.append(_strip_markdown(trailing).strip())
        else:
            clean = _strip_markdown(content).strip()
            parts.append(f"**{name.title()}** — {clean}")

    return "\n\n".join(parts)