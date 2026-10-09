from __future__ import annotations

import difflib
import json
import logging
import re
import time
from pathlib import Path

import httpx

from app.config import BASE_DIR, get_settings
from app.industry.universe import find_universe_company, find_universe_mentions
from app.schemas import CompanyEntity

logger = logging.getLogger("financial_research_agent.retrieval.company_resolver")

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SAMPLE_DIRECTORY_PATH = BASE_DIR / "sample_data" / "company_directory_sample.json"

_CACHE_TTL_SECONDS = 3600


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[.,]", "", text)
    for suffix in (" inc", " corporation", " corp", " limited", " ltd", " plc", " co", " company"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text.strip()


class CompanyResolver:
    _directory: list[dict] | None = None
    _directory_loaded_at: float = 0.0

    def __init__(self):
        self.settings = get_settings()

    def _load_directory(self) -> list[dict]:
        now = time.time()
        if CompanyResolver._directory is not None and (now - CompanyResolver._directory_loaded_at) < _CACHE_TTL_SECONDS:
            return CompanyResolver._directory

        if not self.settings.effective_demo_mode:
            live = self._try_fetch_live()
            if live is not None:
                CompanyResolver._directory = live
                CompanyResolver._directory_loaded_at = now
                return live

        directory = self._load_sample_directory()
        CompanyResolver._directory = directory
        CompanyResolver._directory_loaded_at = now
        return directory

    def _try_fetch_live(self) -> list[dict] | None:
        try:
            resp = httpx.get(
                SEC_TICKERS_URL,
                headers={"User-Agent": self.settings.sec_edgar_user_agent},
                timeout=5.0,
            )
            resp.raise_for_status()
            raw = resp.json()
            directory = [
                {
                    "name": row["title"],
                    "ticker": row["ticker"],
                    "cik": str(row["cik_str"]).zfill(10),
                    "exchange": None,
                }
                for row in raw.values()
            ]
            logger.info("Loaded %d companies from live SEC EDGAR ticker directory", len(directory))
            return directory
        except Exception as exc:  # noqa: BLE001
            logger.warning("Live SEC ticker directory fetch failed (%s); falling back to bundled sample", exc)
            return None

    def _load_sample_directory(self) -> list[dict]:
        with open(SAMPLE_DIRECTORY_PATH, encoding="utf-8") as f:
            return json.load(f)

    def resolve(self, raw_name: str) -> CompanyEntity:
        raw_name = raw_name.strip()
        if not raw_name:
            return CompanyEntity(name=raw_name, resolved=False, resolution_notes="Empty company name")

        universe_hit = find_universe_company(raw_name)
        if universe_hit is not None:
            return CompanyEntity(
                name=universe_hit.name,
                ticker=universe_hit.symbol,
                exchange="NSE",
                resolved=True,
                resolution_notes=f"Matched industry universe company {universe_hit.nse}",
            )

        directory = self._load_directory()
        upper = raw_name.upper()
        normalized_query = _normalize(raw_name)

        for row in directory:
            if row.get("ticker") and row["ticker"].upper() == upper:
                return self._to_entity(row)

        for row in directory:
            if _normalize(row["name"]) == normalized_query:
                return self._to_entity(row)

        candidates = [
            row for row in directory
            if normalized_query in _normalize(row["name"]) or _normalize(row["name"]) in normalized_query
        ]
        if len(candidates) == 1:
            return self._to_entity(candidates[0])
        if len(candidates) > 1:
            best = min(candidates, key=lambda r: len(r["name"]))
            return self._to_entity(best)

        names = [_normalize(row["name"]) for row in directory]
        close = difflib.get_close_matches(normalized_query, names, n=1, cutoff=0.72)
        if close:
            idx = names.index(close[0])
            return self._to_entity(directory[idx])

        return CompanyEntity(
            name=raw_name,
            resolved=False,
            resolution_notes=f"No match found for '{raw_name}' in company directory",
        )

    def find_mentions(self, text: str) -> list[str]:
        universe = find_universe_mentions(text)
        found: list[str] = [company.name for company in universe]
        claimed = {key.upper() for company in universe for key in (company.nse, *company.aliases)}
        directory = self._load_directory()
        for row in directory:
            name = row["name"]
            ticker = row.get("ticker")
            short_name = _normalize(name)
            name_match = bool(short_name) and len(short_name) >= 3 and re.search(
                rf"\b{re.escape(short_name)}\b", text, re.IGNORECASE
            )
            ticker_match = bool(ticker) and re.search(rf"\b{re.escape(ticker)}\b", text)
            if universe and find_universe_company(short_name) is not None:
                continue
            if (name_match or ticker_match) and name not in found:
                found.append(name)
        return found

    @staticmethod
    def _to_entity(row: dict) -> CompanyEntity:
        return CompanyEntity(
            name=row["name"],
            ticker=row.get("ticker"),
            cik=row.get("cik"),
            exchange=row.get("exchange"),
            resolved=True,
        )
