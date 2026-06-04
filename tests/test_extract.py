"""Tests for event parsing (offline — no API call)."""
from rageval.extract import parse_events


def test_parses_json_array():
    raw = '[{"event":"X closes Q3","type":"forward_looking","citation":"X by Q3 2026"}]'
    evs = parse_events(raw, "7")
    assert len(evs) == 1
    assert evs[0].item == "7"
    assert evs[0].type == "forward_looking"
    assert evs[0].citation == "X by Q3 2026"


def test_tolerates_surrounding_text_and_code_fences():
    raw = 'Sure:\n```json\n[{"event":"a risk","type":"risk","citation":"a risk arises"}]\n```'
    assert len(parse_events(raw, "1A")) == 1


def test_bad_json_returns_empty():
    assert parse_events("not json at all", "1") == []


def test_objects_without_event_are_dropped():
    raw = '[{"type":"risk","citation":"x"}, {"event":"real","type":"material","citation":"y"}]'
    evs = parse_events(raw, "8")
    assert [e.event for e in evs] == ["real"]
