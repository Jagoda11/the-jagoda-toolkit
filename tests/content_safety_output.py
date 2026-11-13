"""Inspect Markdown syntax as text; never render or fetch its contents."""

import re
from typing import ClassVar
from markdown_it import MarkdownIt
from markdown_it.token import Token

URI = r"<[a-z][a-z0-9+.-]{1,31}:[^\x00-\x20\x7f<>]*>|\bfile:/|(?:\b[a-z][a-z0-9+.-]*://|\b(?:https?|ftp|data|javascript|vbscript|file|mailto):|www\.|//)\S"
EMAIL = r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b"
ACTIVE_TEXT = re.compile("|".join((URI, EMAIL)), re.IGNORECASE)
ACTIVE_TYPES = {"html_inline", "html_block", "link_open", "image"}


class TokenOnlyRenderer:
    __output__: ClassVar[str] = "tokens"

    def __init__(self, _parser: MarkdownIt) -> None:
        pass

    def render(self, *_args: object, **_kwargs: object) -> str:
        raise RuntimeError("Rendering is disabled for content inspection")

    renderInline = render


PARSER = MarkdownIt("commonmark", renderer_cls=TokenOnlyRenderer).enable("table")
# Classify every destination; active_token rejects all link and image tokens.
PARSER.validateLink = lambda _destination: True


def active_token(token: Token) -> bool:
    # Boundary tokens can precede content omitted by the parser's nesting cap.
    if token.level >= PARSER.options["maxNesting"] - 1:
        return True
    if token.type in ACTIVE_TYPES:
        return True
    if token.type == "text":
        return bool(ACTIVE_TEXT.search(token.content))
    return any(map(active_token, token.children or ()))


def has_active_output(text: str) -> bool:
    return any(map(active_token, PARSER.parse(text)))
