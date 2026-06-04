"""Tests for section-aware parsing (offline — no network)."""
from rageval.parse import html_to_text, split_sections

# A tiny synthetic 10-K: a table-of-contents (short stubs) then the real
# sections (long bodies), so we exercise the TOC-filtering heuristic.
_TOC = "<p>Item 1. Business</p><p>Item 1A. Risk Factors</p><p>Item 7. MD&A</p>"
_BODY = (
    "<p>Item 1. Business</p><p>We design and sell widgets across many markets. "
    + ("widget " * 60) + "</p>"
    "<p>Item 1A. Risk Factors</p><p>Our markets are volatile and uncertain. "
    + ("risk " * 60) + "</p>"
    "<p>Item 7. MD&A</p><p>Revenue grew year over year on strong demand. "
    + ("growth " * 60) + "</p>"
)
SAMPLE = f"<html><body>{_TOC}{_BODY}</body></html>"


def test_html_to_text_strips_tags():
    t = html_to_text(SAMPLE)
    assert "<p>" not in t
    assert "Item 1. Business" in t


def test_split_sections_finds_the_real_items():
    items = {s.item for s in split_sections(html_to_text(SAMPLE))}
    assert {"1", "1A", "7"} <= items


def test_toc_stubs_are_filtered_out():
    # Only the long bodies survive — not the short TOC entries — so each Item
    # appears once, not twice.
    secs = split_sections(html_to_text(SAMPLE))
    assert sum(s.item == "1" for s in secs) == 1


def test_section_text_is_captured():
    secs = {s.item: s for s in split_sections(html_to_text(SAMPLE))}
    assert "widget" in secs["1"].text
    assert "risk" in secs["1A"].text
