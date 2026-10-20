"""GRIDINTEL NFL market discovery — public Kalshi data, research/paper use only."""
from datetime import datetime, timezone
from pathlib import Path
import re
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="GRIDINTEL Market Data Service", version="0.5.0")
ROOT = Path(__file__).resolve().parent
BASE = "https://external-api.kalshi.com/trade-api/v2"

# Only retain markets from clearly NFL-related events, not mixed-sport combos.
NFL_TERMS = re.compile(
    r"\b(nfl|national football league|super bowl|chiefs|eagles|cowboys|ravens|bills|49ers|packers|"
    r"bears|lions|broncos|chargers|jets|giants|steelers|bengals|browns|texans|colts|"
    r"jaguars|titans|dolphins|patriots|raiders|saints|falcons|panthers|buccaneers|"
    r"seahawks|commanders|rams|vikings)\b", re.IGNORECASE
)
BLOCKED = re.compile(r"crosscategory|cross.category|multi.?sport|parlay|combo|bundle", re.IGNORECASE)
OTHER_SPORTS = re.compile(r"\b(nba|wnba|nhl|mlb|soccer|tennis|hockey|baseball|basketball|golf|cricket)\b", re.IGNORECASE)

@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")

@app.get("/health")
def health():
    return {"ok": True, "service": "GRIDINTEL", "version": "0.5.0", "checked_at": datetime.now(timezone.utc).isoformat()}


def quote_number(market, field):
    """Keep API dollar quote as number where available, without fabricating one."""
    value = market.get(field)
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def normalize(market, event_title="", series_ticker=""):
    bid = quote_number(market, "yes_bid_dollars")
    ask = quote_number(market, "yes_ask_dollars")
    volume = market.get("volume_fp")
    try:
        volume_n = float(volume or 0)
    except (TypeError, ValueError):
        volume_n = 0
    # Zero prices and crossed/invalid quotes must never be treated as fair probabilities.
    usable = bool(bid is not None and ask is not None and 0 < bid <= ask < 1 and volume_n > 0)
    return {
        "ticker": market.get("ticker", ""),
        "title": market.get("title") or event_title or "Untitled NFL market",
        "subtitle": market.get("subtitle") or "",
        "event_title": event_title,
        "series_ticker": series_ticker,
        "status": market.get("status"),
        "yes_bid_dollars": market.get("yes_bid_dollars"),
        "yes_ask_dollars": market.get("yes_ask_dollars"),
        "last_price_dollars": market.get("last_price_dollars"),
        "volume_fp": market.get("volume_fp"),
        "open_interest_fp": market.get("open_interest_fp"),
        "close_time": market.get("close_time"),
        "usable_quote": usable,
        "quote_status": "Two-sided quote with volume" if usable else "No verified usable two-sided quote",
    }

@app.get("/api/kalshi/markets")
async def kalshi_markets():
    found = {}
    pages_scanned = 0
    events_scanned = 0
    markets_scanned = 0
    excluded_combinations = 0
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            # Events carry sport/game context; inspect multiple pages rather than one random market page.
            cursor = None
            for _ in range(12):
                params = {"status": "open", "limit": 200, "with_nested_markets": "true"}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get(f"{BASE}/events", params=params)
                response.raise_for_status()
                payload = response.json()
                pages_scanned += 1
                events = payload.get("events") or []
                events_scanned += len(events)
                for event in events:
                    event_title = str(event.get("title") or "")
                    event_subtitle = str(event.get("sub_title") or "")
                    series = str(event.get("series_ticker") or "")
                    event_ticker = str(event.get("event_ticker") or "")
                    context = " ".join((event_title, event_subtitle, series, event_ticker))
                    if BLOCKED.search(context) or OTHER_SPORTS.search(context):
                        excluded_combinations += 1
                        continue
                    if not NFL_TERMS.search(context):
                        continue
                    for market in event.get("markets") or []:
                        markets_scanned += 1
                        ticker = str(market.get("ticker") or "")
                        title = str(market.get("title") or "")
                        if not ticker or BLOCKED.search(f"{ticker} {title}"):
                            excluded_combinations += 1
                            continue
                        if market.get("status") not in ("open", "active"):
                            continue
                        found[ticker] = normalize(market, event_title, series)
                cursor = payload.get("cursor")
                if not cursor:
                    break

            # Additional market pages catch NFL titles even if event pagination missed their events.
            cursor = None
            for _ in range(8):
                params = {"status": "open", "limit": 1000}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get(f"{BASE}/markets", params=params)
                response.raise_for_status()
                payload = response.json()
                pages_scanned += 1
                markets = payload.get("markets") or []
                markets_scanned += len(markets)
                for market in markets:
                    title = str(market.get("title") or "")
                    ticker = str(market.get("ticker") or "")
                    subtitle = str(market.get("subtitle") or "")
                    context = " ".join((title, ticker, subtitle, str(market.get("event_ticker") or "")))
                    if BLOCKED.search(context) or OTHER_SPORTS.search(context):
                        excluded_combinations += 1
                        continue
                    if not NFL_TERMS.search(context) or not ticker:
                        continue
                    found.setdefault(ticker, normalize(market))
                cursor = payload.get("cursor")
                if not cursor:
                    break
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Kalshi public API request failed: {type(exc).__name__}") from exc

    results = list(found.values())
    def rank(m):
        try:
            volume = float(m.get("volume_fp") or 0)
        except (ValueError, TypeError):
            volume = 0
        return (int(m["usable_quote"]), volume)
    results.sort(key=rank, reverse=True)
    return {
        "source": "Kalshi public REST API",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "markets": results[:100],
        "usable_quote_count": sum(1 for m in results if m["usable_quote"]),
        "pages_scanned": pages_scanned,
        "events_scanned": events_scanned,
        "individual_markets_scanned": markets_scanned,
        "excluded_combinations": excluded_combinations,
        "note": "Partial paginated public-market discovery, not exhaustive. Zero results do not prove no NFL markets exist. Quotes are not FanDuel odds or validated betting probabilities.",
    }
