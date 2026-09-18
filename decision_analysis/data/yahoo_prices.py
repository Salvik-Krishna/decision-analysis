"""
Dependency-free daily price history from the Yahoo Finance v8 chart API.

This is a stdlib-only drop-in replacement for ``MarketScraper.fetch_prices``
(which depends on ``yfinance``/``pandas``).  It is used by ``scrape_dataset.py``
so the full market dataset can be built in environments where the scientific
Python stack cannot be installed.

Only the standard library is used (``urllib`` + ``json``).  TLS verification is
preserved: pass an ``ssl.SSLContext`` built from a CA bundle, or rely on the
``SSL_CERT_FILE`` environment variable that the default context honours.
"""

from __future__ import annotations

import json
import ssl
import time
from datetime import datetime, timezone
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .database import Database

_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) decision-analysis-research"


def _to_epoch(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _from_epoch(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


class YahooPriceFetcher:
    """
    Fetch OHLCV daily history from Yahoo's public chart endpoint.

    Parameters
    ----------
    db           : Database to write rows into
    ssl_context  : Optional SSLContext (recommended; built from a CA bundle).
                   If None, the module-default verified context is used, which
                   respects the SSL_CERT_FILE env var.
    throttle     : Seconds to pause between requests.
    """

    def __init__(
        self,
        db: Database,
        ssl_context: Optional[ssl.SSLContext] = None,
        throttle: float = 0.5,
    ) -> None:
        self.db = db
        self.ctx = ssl_context
        self.throttle = throttle

    def fetch_prices(
        self,
        ticker: str,
        start: str = "2018-01-01",
        end: Optional[str] = None,
    ) -> int:
        """Download daily OHLCV for ``ticker`` and insert new rows. Returns rows inserted."""
        if end is None:
            end = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        # Yahoo symbols use '-' the same way the registry does (e.g. BRK-B).
        symbol = ticker.upper()
        url = _CHART_URL.format(symbol=symbol)
        params = (
            f"?period1={_to_epoch(start)}&period2={_to_epoch(end)}"
            f"&interval=1d&events=div%2Csplit&includeAdjustedClose=true"
        )

        try:
            payload = self._get_json(url + params)
        except (HTTPError, URLError, TimeoutError) as exc:
            print(f"  [error] {ticker} prices: {exc}")
            return 0
        except Exception as exc:  # noqa: BLE001 - report and continue the batch
            print(f"  [error] {ticker} prices (unexpected): {exc}")
            return 0

        rows = self._parse_chart(ticker, payload)
        if not rows:
            return 0
        # db.insert_prices returns SQLite changes() which under-reports after
        # executemany; count the table delta instead for an accurate total.
        before = self._row_count(ticker)
        self.db.insert_prices(rows)
        return self._row_count(ticker) - before

    def _row_count(self, ticker: str) -> int:
        return len(self.db.get_prices(ticker))

    @staticmethod
    def _parse_chart(ticker: str, payload: dict) -> List[dict]:
        chart = (payload or {}).get("chart", {})
        if chart.get("error"):
            print(f"  [warn] {ticker}: {chart['error']}")
            return []
        results = chart.get("result") or []
        if not results:
            return []
        res = results[0]

        timestamps = res.get("timestamp") or []
        quote = (res.get("indicators", {}).get("quote") or [{}])[0]
        adj = (res.get("indicators", {}).get("adjclose") or [{}])
        adj_close = adj[0].get("adjclose") if adj else None

        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        rows: List[dict] = []
        for i, ts in enumerate(timestamps):
            close = _at(closes, i)
            if close is None:
                continue  # skip holidays / null rows
            rows.append({
                "ticker": ticker.upper(),
                "date": _from_epoch(ts),
                "open": _at(opens, i),
                "high": _at(highs, i),
                "low": _at(lows, i),
                "close": close,
                "adj_close": _at(adj_close, i) if adj_close is not None else close,
                "volume": _int_at(volumes, i),
            })
        return rows

    def _get_json(self, url: str) -> dict:
        time.sleep(self.throttle)
        req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
        with urlopen(req, timeout=25, context=self.ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))


def _at(seq, i):
    try:
        v = seq[i]
    except (IndexError, TypeError):
        return None
    return None if v is None else round(float(v), 6)


def _int_at(seq, i):
    v = _at(seq, i)
    return int(v) if v is not None else None
