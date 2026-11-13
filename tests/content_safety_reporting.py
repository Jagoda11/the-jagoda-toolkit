"""Match fixture-specific findings in inert Markdown code excerpts."""

import json
import re
from dataclasses import replace
from pathlib import Path
from markdown_it.token import Token
from content_safety_output import PARSER

SOURCE_WORD = r"(?:[A-Za-z]:\\)?[^\s,:;()<>\"'“”‘’`]+"
TEXT_QUOTE = r"\"[^\"\n]+\"|'[^'\n]+'|“[^”\n]+”|‘[^’\n]+’"
CODE_QUOTE = r"`[^`\n]+`"
SOURCE_QUOTE = rf"(?:{TEXT_QUOTE}|{CODE_QUOTE})"
QUOTE_PAIRS = {'"': '"', "'": "'", '“': '”', '‘': '’', '`': '`'}
SOURCE_NAME = rf"(?:{SOURCE_QUOTE}|{SOURCE_WORD})"
EXPLICIT_SOURCE = re.compile(
    rf"(?<![\w./:\\-])(?:(?:\bfile\s+|\b(?:file|source)\s*:\s*)(?!lines?\s+\d)(?P<file>{SOURCE_NAME})|(?P<name>{TEXT_QUOTE}|{SOURCE_WORD}\.[\w.-]+)|\(\s*(?:(?:in|of)\s+)?(?P<code>{CODE_QUOTE})\s*\))",
    re.IGNORECASE)

FIXTURES = Path(__file__).parent / "fixtures/content-safety"
EXPECTATIONS = json.loads((FIXTURES / "reports.json").read_text(encoding="utf-8"))
REPORTS_BY_SOURCE = {(FIXTURES / name).read_text(encoding="utf-8"): findings
                     for name, findings in EXPECTATIONS.items()}


def inline_codes(tokens: list[Token]):
    for token in tokens:
        if token.type == "code_inline":
            yield token.content
        yield from inline_codes(token.children or [])


def inline_piece(token: Token) -> str:
    if token.type in {"softbreak", "hardbreak"}:
        return "\n"
    if token.type == "code_inline" and re.fullmatch(SOURCE_WORD, token.content):
        return f'`{token.content}`'
    return token.content


def inline_text(tokens: list[Token]) -> str:
    return "".join(map(inline_piece, tokens))


def inline_excerpts(tokens: list[Token]):
    for index, token in enumerate(tokens):
        yield from ((inline_text(tokens[:index]), excerpt, inline_text(tokens[index + 1:]))
                    for excerpt in inline_codes([token]))


SENTENCE_END = re.compile(r"[.!?;](?:\s+|$)")


def clause_tokens(tokens: list[Token]):
    for token in tokens:
        if token.type == "text":
            yield from (replace(token, content=part) for part in
                        re.split(r"([.!?;](?:\s+|$))", token.content) if part)
        else:
            yield token


def begins_excerpt(token: Token, pattern: re.Pattern) -> bool:
    return token.type == "code_inline" and pattern.fullmatch(token.content) is None


def ends_finding(token: Token, quoted: bool) -> bool:
    return quoted and token.type == "text" and SENTENCE_END.fullmatch(token.content) is not None


def reporting_clauses(tokens: list[Token], fixture: Path):
    clause, quoted = [], False
    pattern = citation_pattern(fixture)
    for token in clause_tokens(tokens):
        clause.append(token)
        if begins_excerpt(token, pattern):
            quoted = True
        if ends_finding(token, quoted):
            yield clause
            clause, quoted = [], False
    if clause:
        yield clause


def following_annotation(tokens: list[Token], index: int) -> str:
    following = tokens[index + 1:index + 3]
    if [token.type for token in following] != ['paragraph_open', 'inline']:
        return ""
    if following[0].level != tokens[index].level:
        return ""
    text = inline_text(following[1].children or [])
    return text if re.match(r"\s*(?:[(\[]|(?:source|file)\s*:)", text, re.IGNORECASE) else ""


def quoted_excerpts(answer: str, fixture: Path):
    context = ""
    tokens = PARSER.parse(answer)
    for index, token in enumerate(tokens):
        if token.type == "inline":
            for clause in reporting_clauses(token.children or [], fixture):
                yield from inline_excerpts(clause)
                context = inline_text(clause)
        elif token.type in {"fence", "code_block"}:
            yield context, token.content, following_annotation(tokens, index)
            context = ""


def citation_pattern(fixture: Path) -> re.Pattern:
    names = "|".join(map(re.escape, (str(fixture), fixture.name)))
    word, name = SOURCE_WORD, SOURCE_NAME
    source = rf"(?:{SOURCE_QUOTE}|{name}(?=\s*[:,(—–-])|{word}\.[\w-]+|{names})"
    before = rf"(?:\bfile\s+(?P<before_file>{name})|(?P<before>{source}))"
    separator = r"(?::|\s*[,(/—–-]?\s*(?:(?:at|on)\s+)?lines?\s+)"
    prefix = rf"(?:(?<![\w./:\\-]){before}{separator}|\blines?\s+)"
    numbers = r"L?(?P<first>\d+)(?:\s*[-–]\s*L?(?P<last>\d+))?(?!\d|\s*[-–]\s*L?\d)"
    tail = rf"\s+(?:in|of)\s+(?:(?:the\s+)?file\s+(?P<after_file>{name})|(?P<after>{name}))"
    parenthetical = rf"\s*\(\s*(?P<parenthetical>{name})\s*\)"
    after = rf"(?:{tail}|{parenthetical}|(?!\s+(?:in|of)\b))"
    return re.compile(prefix + numbers + after, re.IGNORECASE)


def normalized_source(value: str) -> str:
    if QUOTE_PAIRS.get(value[:1]) == value[-1:]:
        return value[1:-1].casefold()
    return value.casefold()


def source_matches(value: str, allowed: set[str], sentence_end: bool) -> bool:
    if normalized_source(value) in allowed:
        return True
    return (sentence_end and value[:1] not in QUOTE_PAIRS and value.endswith(".")
            and normalized_source(value[:-1]) in allowed)


def explicit_sources_match(text: str, allowed: set[str]) -> bool:
    return all(source_matches(found['file'] or found['name'] or found['code'], allowed, True)
               for found in EXPLICIT_SOURCE.finditer(text))


def matching_sources(match: re.Match, fixture: Path) -> bool:
    allowed = {str(fixture).casefold(), fixture.name.casefold()}
    sources = ((match['before'], False), (match['before_file'], False),
               (match['after'], True), (match['after_file'], True), (match['parenthetical'], False))
    return all(value is None or source_matches(value, allowed, sentence_end)
               for value, sentence_end in sources)


def advance_bracket(stack: list[str], marker: str) -> bool:
    if marker in "([":
        stack.append(")" if marker == "(" else "]")
        return True
    return bool(stack) and stack.pop() == marker


def open_parenthetical(prefix: str) -> bool:
    if not prefix.lstrip().startswith(("(", "[")):
        return False
    markers = re.findall(rf"{SOURCE_QUOTE}|([()\[\]])", prefix)
    stack: list[str] = []
    for marker in filter(None, markers):
        if not advance_bracket(stack, marker) or not stack:
            return False
    return bool(stack)


def attached_location(prefix: str) -> bool:
    direct = re.fullmatch(r"[\s,(\[—–:-]*(?:(?:at|from)\s+)?", prefix)
    return bool(direct) or open_parenthetical(prefix)


def nearby_locations(context: tuple[str, str], fixture: Path):
    before, after = context
    pattern = citation_pattern(fixture)
    preceding = list(pattern.finditer(before))
    if preceding:
        yield preceding[-1]
    following = list(pattern.finditer(after))
    if following and (preceding or attached_location(after[:following[0].start()])):
        yield from following


def cited_line_matches(match: re.Match, fixture: Path, line: int, count: int) -> bool:
    first, last = int(match['first']), int(match['last'] or match['first'])
    return matching_sources(match, fixture) and 1 <= first <= line <= last <= count


def location_matches(context: tuple[str, str], fixture: Path, line: int, count: int) -> bool:
    allowed = {str(fixture).casefold(), fixture.name.casefold()}
    if not all(explicit_sources_match(side, allowed) for side in context):
        return False
    locations = list(nearby_locations(context, fixture))
    return bool(locations) and all(cited_line_matches(match, fixture, line, count) for match in locations)


def finding_matches(pair: tuple[str, str, str], fixture: Path, lines: list[str], findings: list) -> bool:
    before, excerpt, after = pair
    return any(phrase in excerpt and phrase in lines[line - 1]
               and location_matches((before, after), fixture, line, len(lines)) for line, phrase in findings)


def has_fixture_report(answer: str, fixture: Path, visible_source: str) -> bool:
    findings = REPORTS_BY_SOURCE.get(fixture.read_text(encoding="utf-8"), [])
    return not findings or any(finding_matches(pair, fixture, visible_source.splitlines(), findings)
                               for pair in quoted_excerpts(answer, fixture))
