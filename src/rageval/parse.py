"""Section-aware parsing of a 10-K: HTML -> text -> split by Item.

A 10-K is one large *structured* document. We deliberately parse it by its Item
structure (deterministic, faithful, cheap) instead of semantic vector search.
Vector RAG is reserved for cross-filing / query-driven tasks (a later slice).

Note: real 10-K HTML is messy (XBRL, tables, TOC duplication). This is an
MVP-grade heuristic parser, validated by tests; robustness improves in later slices.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.chunks.append(data)


def html_to_text(html: str) -> str:
    """Strip HTML to normalized plain text."""
    p = _TextExtractor()
    p.feed(html)
    return re.sub(r"\s+", " ", " ".join(p.chunks)).strip()


# Matches "Item 1.", "Item 1A.", "Item 7 —", etc.
_ITEM_RE = re.compile(r"\bItem\s+(\d+[A-Z]?)\.?\s*[—\-:]?\s*", re.IGNORECASE)

# Table-of-contents stubs are short; real sections are long. Filter below this.
_MIN_SECTION_CHARS = 200


@dataclass
class Section:
    item: str    # e.g. "1A"
    title: str   # best-effort short title
    text: str


def _item_sort_key(item: str) -> tuple[int, str]:
    m = re.match(r"(\d+)([A-Z]*)", item)
    return (int(m.group(1)), m.group(2)) if m else (999, item)


def split_sections(text: str, dedupe: bool = True) -> list[Section]:
    """Split filing text into sections keyed by Item number.

    Two passes of noise removal:
    1. Drop short bodies (table-of-contents stubs that just repeat the headers).
    2. Dedupe: a real 10-K cross-references Items throughout ("see Item 8 ..."),
       so the same Item matches many times. Keep the **longest** body per Item —
       the canonical section — and drop the cross-reference fragments.
    Set dedupe=False to inspect every raw match.
    """
    matches = list(_ITEM_RE.finditer(text))
    if not matches:
        return [Section(item="0", title="(whole document)", text=text)]

    raw: list[Section] = []
    for i, m in enumerate(matches):
        item = m.group(1).upper()
        if not 1 <= int(re.match(r"\d+", item).group()) <= 16:
            continue  # 10-K Items run 1..16; higher numbers are Reg S-K refs (e.g. "Item 601")
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) < _MIN_SECTION_CHARS:
            continue  # TOC stub, not a real section
        title = re.split(r"[.\n]", body[:80])[0].strip()
        raw.append(Section(item=item, title=title, text=body))

    if not dedupe:
        return raw

    best: dict[str, Section] = {}
    for s in raw:
        if s.item not in best or len(s.text) > len(best[s.item].text):
            best[s.item] = s
    return sorted(best.values(), key=lambda s: _item_sort_key(s.item))
