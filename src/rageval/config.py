"""Central configuration. Loads .env; defines paths, model, and EDGAR settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
FILINGS = DATA / "filings"      # cached raw filings (gitignored)
CHROMA = DATA / "chroma"        # vector store, only when vector RAG is justified
RESULTS = ROOT / "results"      # eval outputs + traces (gitignored)


@dataclass(frozen=True)
class Config:
    # --- model ---
    model: str = "claude-sonnet-4-6"        # extraction/agent model
    judge_model: str = "claude-sonnet-4-6"  # eval judge (swap to a 2nd model for independence)

    # --- EDGAR ---
    # SEC requires a descriptive User-Agent; set SEC_USER_AGENT in .env.
    sec_user_agent: str = os.environ.get("SEC_USER_AGENT", "filing-event-eval example@example.com")
    edgar_base: str = "https://www.sec.gov"
    edgar_data: str = "https://data.sec.gov"

    # --- pipeline budget ---
    max_sections: int = 40   # cap sections processed per filing (cost guard)

    # --- reliability / retries ---
    llm_max_retries: int = 6      # Anthropic SDK retries (exp backoff, respects Retry-After)
    request_timeout: int = 120    # per-call timeout (seconds)
    edgar_max_attempts: int = 4   # EDGAR GET attempts on 429/5xx (backoff); 4xx fails fast


CFG = Config()
