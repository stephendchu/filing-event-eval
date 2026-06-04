"""Observability: OpenTelemetry tracing + (optional) Arize Phoenix UI.

Every pipeline stage and every Claude call becomes a **span** you can inspect.
A span = one timed unit of work, with attributes (inputs/outputs/metadata).

Two ways to see them:
- **Console exporter (always on):** spans print to your terminal as raw JSON —
  the best way to *learn* what's actually captured (latency, tokens, prompts).
- **Phoenix UI (set PHOENIX=1):** a local trace dashboard at http://localhost:6006.

This module is intentionally small and commented — read it top to bottom.
"""
from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

_TRACER = None


def init_tracing(project: str = "filing-event-eval"):
    """Set up tracing once and return a tracer. Idempotent."""
    global _TRACER
    if _TRACER is not None:
        return _TRACER

    use_phoenix = os.environ.get("PHOENIX") == "1"

    if use_phoenix:
        # Phoenix builds + installs the provider AND auto-instruments Anthropic.
        from phoenix.otel import register
        provider = register(project_name=project, auto_instrument=True)
        print("[obs] Phoenix UI -> http://localhost:6006")
    else:
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
        # Instrument the Anthropic SDK so every Claude call becomes a span.
        try:
            from openinference.instrumentation.anthropic import AnthropicInstrumentor
            AnthropicInstrumentor().instrument(tracer_provider=provider)
        except Exception as e:  # noqa: BLE001 — tracing must never break the run
            print(f"[obs] anthropic auto-instrumentation unavailable ({e})")

    # Always also print spans to the console — this is the learnable raw view.
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    _TRACER = trace.get_tracer(project)
    return _TRACER
