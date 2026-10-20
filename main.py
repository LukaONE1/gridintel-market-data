"""GRIDINTEL Kalshi market feed v0.4.0 — NFL-only, no composite contracts."""
from datetime import datetime, timezone
from pathlib import Path
import re
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="GRIDINTEL Market Data Service", version="0.4.0")
ROOT = Path(__file__).resolve().parent
BASE = "https://api.elections.kalshi.com/trade-api/v2"

NFL_TEAMS = re.compile(
    r"\\b(nfl|super bowl|chiefs|eagles|cowboys|ravens|bills|49ers|niners|"
    r"packers|bears|lions|broncos|chargers|jets|giants|steelers|bengals|"
    r"browns|texans|colts|jaguars|titans|dolphins|patriots|raiders|"
    r"saints|falcons|panthers|buccaneers|bucs|seahawks|commanders|rams|"
    r"vikings)\\b", re.IGNORECASE
)
NFL_SERIES = ("KXNFL", "KXSB", "KXSUPERBOWL")
BAD_SERIES = ("CROSS", "MULTI", "COMBO", "PARLAY")
MAX_TITLE = 175


def dollars(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def clean_market(m, event):
    ticker = str(m.get("ticker") or "")
    series = str(event.get("series_ticker") or m.get("series_ticker") or "")
    event_title = str(event.get("title") or "")
    title = str(m.get("title") or event_title)
    subtitle = str(m.get("subtitle") or "")
    joined = f"{series} {event_title} {title} {subtitle}"
    # Require a clearly NFL-labelled series or a football-specific event title.
    if not (series.upper().startswith(NFL_SERIES) or NFL_TEAMS.search(event_title)):
        return None
    if any(bad in f"{ticker} {series}".upper() for bad in BAD_SERIES):
        return None
    if len(title) > MAX_TITLE or len(event_title) > MAX_TITLE:
        return None
    if title.count(",") > 3 or event_title.count(",") > 3:
        return None
    if m.get("status") not in ("active", "open"):
        return None
    bid = dollars(m.get("yes_bid_dollars"))
    ask = dollars(m.get("yes_ask_dollars"))
    last = dollars(m.get("last_price_dollars"))
    volume = dollars(m.get("volume_fp") or m.get("volume"))
    # A 0.00 or 1.00 quote alone is not actionable; flag instead of inventing a price.
    quoted = 0 < bid < 1 and 0 < ask < 1 and ask >= bid
    return {
        "ticker": ticker, "title": title, "subtitle": subtitle,
        "status": m.get("status"), "yes_bid_dollars": m.get("yes_bid_dollars"),
        "yes_ask_dollars": m.get("yes_ask_dollars"),
        "last_price_dollars": m.get("last_price_dollars"),
        "volume_fp": m.get("volume_fp"), "open_interest_fp": m.get("open_interest_fp"),
        "close_time": m.get("close_time"), "event_ticker": m.get("event_ticker"),
        "event_title": event_title, "series_ticker": series,
        "usable_quote": quoted, "has_volume": volume > 0,
        "signal_ready": quoted and volume > 0,
    }


@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "service": "GRIDINTEL", "version": "0.4.0",
            "checked_at": datetime.now(timezone.utc).isoformat()}


@app.get("/api/kalshi/markets")
async def kalshi_markets():
    found = {}
    pages_scanned = 0
    events_scanned = 0
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            # Target NFL series first. These series may be empty or not supported;
            # the general event scan below provides a fallback.
            for series in ("KXNFLGAME", "KXNFLSPREAD", "KXNFLTOTAL", "KXNFL"):
                response = await client.get(f"{BASE}/events", params={
                    "status": "open", "limit": 200, "with_nested_markets": "true",
                    "series_ticker": series,
                })
                if response.status_code in (400, 404, 422):
                    continue
                response.raise_for_status()
                payload = response.json()
                pages_scanned += 1
                for event in payload.get("events") or []:
                    events_scanned += 1
                    for m in event.get("markets") or []:
                        item = clean_market(m, event)
                        if item and item["ticker"]:
                            found[item["ticker"]] = item

            cursor = None
            for _ in range(8):
                params = {"status": "open", "limit": 200,
                          "with_nested_markets": "true"}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get(f"{BASE}/events", params=params)
                response.raise_for_status()
                payload = response.json()
                pages_scanned += 1
                for event in payload.get("events") or []:
                    events_scanned += 1
                    for m in event.get("markets") or []:
                        item = clean_market(m, event)
                        if item and item["ticker"]:
                            found[item["ticker"]] = item
                cursor = payload.get("cursor")
                if not cursor:
                    break
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Kalshi request failed: {type(exc).__name__}") from exc

    results = list(found.values())
    # Show tradeable quotes first; then other relevant NFL contracts.
    results.sort(key=lambda m: (
        not m["signal_ready"], not m["usable_quote"],
        -dollars(m["volume_fp"]), m["title"]
    ))
    ready = sum(m["signal_ready"] for m in results)
    return {
        "source": "Kalshi public REST API",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results), "signal_ready_count": ready,
        "markets": results[:100], "pages_scanned": pages_scanned,
        "events_scanned": events_scanned,
        "note": ("NFL-only filtering; composite contracts excluded. "
                 "A market with no valid bid/ask or no volume is not signal-ready. "
                 "This is a partial scan, not a comprehensive NFL feed. "
                 "No FanDuel or Novig integration; no validated betting edge.")
    }
