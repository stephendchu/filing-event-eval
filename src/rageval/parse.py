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


def split_sections(text: str) -> list[Section]:
    """Split filing text into sections keyed by Item number.

    Filters out the short table-of-contents entries (which repeat the Item
    headers) by requiring a minimum body length, keeping the real sections.
    """
    matches = list(_ITEM_RE.finditer(text))
    if not matches:
        return [Section(item="0", title="(whole document)", text=text)]

    sections: list[Section] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if len(body) < _MIN_SECTION_CHARS:
            continue  # TOC stub, not a real section
        title = re.split(r"[.\n]", body[:80])[0].strip()
        sections.append(Section(item=m.group(1).upper(), title=title, text=body))
    return sections
