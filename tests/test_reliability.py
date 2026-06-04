"""Retry-policy tests (offline). Transient faults retry; config errors fail fast."""
from rageval.edgar import _should_retry


def test_retries_on_transient_faults():
    assert _should_retry(429)            # rate limited
    assert _should_retry(500)
    assert _should_retry(503)


def test_fails_fast_on_config_and_success():
    assert not _should_retry(403)        # bad User-Agent -> don't hammer SEC, fix the UA
    assert not _should_retry(404)        # not found -> retrying won't help
    assert not _should_retry(200)
