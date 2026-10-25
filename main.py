"""GRIDINTEL v0.6: targeted public Kalshi NFL series discovery; paper research only."""
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="GRIDINTEL Market Data Service", version="0.6.0")
ROOT = Path(__file__).resolve().parent
BASE = "https://external-api.kalshi.com/trade-api/v2"
# Known NFL game, spread and total series observed in previous working GRIDINTEL feed.
NFL_SERIES = ("KXNFLGAME", "KXNFLSPREAD", "KXNFLTOTAL")
ODDS_CACHE_TTL = 300
odds_cache = None
odds_cache_time = 0.0
@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")

@app.get("/health")
def health():
    return {"ok": True, "service": "GRIDINTEL", "version": "0.6.0", "checked_at": datetime.now(timezone.utc).isoformat()}

def numeric(m, key):
    try:
        value = m.get(key)
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None

def normalize(m, series):
    bid, ask, volume = numeric(m, "yes_bid_dollars"), numeric(m, "yes_ask_dollars"), numeric(m, "volume_fp")
    usable = bid is not None and ask is not None and 0 < bid <= ask < 1 and (volume or 0) > 0
    return {
        "ticker": m.get("ticker", ""), "title": m.get("title") or "NFL market",
        "subtitle": m.get("subtitle") or "", "event_title": m.get("event_title") or "",
        "series_ticker": series, "status": m.get("status"),
        "yes_bid_dollars": m.get("yes_bid_dollars"), "yes_ask_dollars": m.get("yes_ask_dollars"),
        "last_price_dollars": m.get("last_price_dollars"), "volume_fp": m.get("volume_fp"),
        "open_interest_fp": m.get("open_interest_fp"), "close_time": m.get("close_time"),
        "usable_quote": usable,
        "quote_status": "Two-sided quote with volume" if usable else "No verified usable two-sided quote",
    }

async def fetch_series(client, series):
    found = {}
    pages = 0
    scanned = 0
    cursor = None
    # Target the known NFL series instead of scanning unrelated markets.
    for _ in range(4):
        params = {"series_ticker": series, "status": "open", "limit": 1000, "mve_filter": "exclude"}
        if cursor:
            params["cursor"] = cursor
        response = await client.get(f"{BASE}/markets", params=params)
        response.raise_for_status()
        payload = response.json()
        pages += 1
        markets = payload.get("markets") or []
        scanned += len(markets)
        for m in markets:
            ticker = str(m.get("ticker") or "")
            if ticker and m.get("status") in ("open", "active") and not m.get("mve_collection_ticker"):
                found[ticker] = normalize(m, series)
        cursor = payload.get("cursor")
        if not cursor:
            break
    return found, pages, scanned

@app.get("/api/kalshi/markets")
async def kalshi_markets():
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            fetched = await asyncio.gather(*(fetch_series(client, s) for s in NFL_SERIES), return_exceptions=True)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Kalshi API request failed: {type(exc).__name__}") from exc
    found = {}
    pages = scanned = 0
    errors = []
    for series, result in zip(NFL_SERIES, fetched):
        if isinstance(result, BaseException):
            errors.append(f"{series}: {type(result).__name__}")
            continue
        entries, page_count, market_count = result
        found.update(entries)
        pages += page_count
        scanned += market_count
    if len(errors) == len(NFL_SERIES):
        raise HTTPException(status_code=502, detail="All targeted Kalshi series requests failed: " + "; ".join(errors))
    results = list(found.values())
    results.sort(key=lambda m: (int(m["usable_quote"]), numeric(m, "volume_fp") or 0), reverse=True)
    return {
        "source": "Kalshi public REST API", "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results), "markets": results[:100],
        "usable_quote_count": sum(bool(m["usable_quote"]) for m in results),
        "pages_scanned": pages, "events_scanned": 0, "individual_markets_scanned": scanned,
        "excluded_combinations": 0, "series_checked": list(NFL_SERIES), "series_errors": errors,
        "note": "Targeted partial scan of NFL game/spread/total series. Not exhaustive. Zero results do not prove no NFL markets exist. Quotes are not FanDuel odds or validated betting probabilities.",
    }
# GRIDINTEL v1.0 - NFL sportsbook odds
@app.get("/api/nfl/odds")
async def nfl_odds():
    import os
    global odds_cache, odds_cache_time

    if odds_cache is not None and time.monotonic() - odds_cache_time < ODDS_CACHE_TTL:
        return odds_cache
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Odds API is not configured"
        )

    url = (
        "https://api.the-odds-api.com/v4/"
        "sports/americanfootball_nfl/odds/"
    )
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            games = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Odds provider returned HTTP {exc.response.status_code}"
        ) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="NFL sportsbook odds temporarily unavailable"
        ) from exc

        result = {
        "source": "The Odds API",
        "sport": "NFL",
        "market": "moneyline",
        "odds_format": "american",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "game_count": len(games),
        "games": games,
        }
    odds_cache = result
    odds_cache_time = time.monotonic()
    return result
