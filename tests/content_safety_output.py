"""Inspect Markdown syntax as text; never render or fetch its contents."""

import re
from collections.abc import Callable, Iterable
from typing import Optional

URI = r"\bfile:/|(?:\b[a-z][a-z0-9+.-]*://|\b(?:https?|ftp|data|javascript|mailto):|www\.|//)\S"
EMAIL = r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b"
HTML = r"<!--|<![a-z]|<\??/?[a-z][\w:-]*(?:[\s/>])"
LINK = r"!\[|\]\s*(?:\(|\[|:\s*\S)"
ACTIVE = re.compile("|".join((URI, EMAIL, HTML, LINK)), re.IGNORECASE | re.MULTILINE)
FENCES = re.compile(r"(?m)^ {0,3}(`{3,}|~{3,})([^\n]*)\n")
TICKS = re.compile(r"(?<![\\`])`+(?!`)")


def fence_end(text: str, opening: re.Match[str]) -> Optional[re.Match[str]]:
    fence = opening.group(1)
    if fence[0] == "`" and "`" in opening.group(2):
        return None
    pattern = rf"(?m)^ {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*$"
    return re.compile(pattern).search(text, opening.end())


def span_end(text: str, opening: re.Match[str]) -> Optional[re.Match[str]]:
    pattern = rf"(?<!`)`{{{len(opening.group())}}}(?!`)"
    return re.compile(pattern).search(text, opening.end())


def mask_regions(text: str, openings: Iterable[re.Match[str]],
                 closing: Callable[[str, re.Match[str]], Optional[re.Match[str]]]) -> str:
    parts, position = [], 0
    for opening in openings:
        if opening.start() < position:
            continue
        end = closing(text, opening)
        if end is not None:
            parts.extend((text[position:opening.start()], " CODE "))
            position = end.end()
    return "".join(parts) + text[position:]


def outside_code(text: str) -> str:
    text = mask_regions(text, FENCES.finditer(text), fence_end)
    return "".join(mask_regions(line, TICKS.finditer(line), span_end) for line in text.splitlines(keepends=True))


def has_active_output(text: str) -> bool:
    return bool(ACTIVE.search(outside_code(text)))
