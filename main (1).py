"""GRIDINTEL public Kalshi NFL market feed. No authentication or betting actions."""
from datetime import datetime, timezone
from pathlib import Path
import re
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="GRIDINTEL Market Data Service", version="0.3.0")
ROOT = Path(__file__).resolve().parent
BASE = "https://api.elections.kalshi.com/trade-api/v2"
# Match team names and common NFL contract series/tickers, but not generic college football.
NFL_TERMS = re.compile(
    r"\b(?:nfl|super\s*bowl|chiefs|eagles|cowboys|ravens|bills|49ers|niners|"
    r"packers|bears|lions|broncos|chargers|jets|giants|steelers|bengals|browns|"
    r"texans|colts|jaguars|titans|dolphins|patriots|raiders|saints|falcons|"
    r"panthers|buccaneers|bucs|seahawks|commanders|rams|vikings|"
    r"kxnfl[a-z0-9-]*|kxsb[a-z0-9-]*)\b",
    re.IGNORECASE,
)

@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")

@app.get("/health")
def health():
    return {"ok": True, "service": "GRIDINTEL", "checked_at": datetime.now(timezone.utc).isoformat()}


def normalize(market, event_title="", series_ticker=""):
    return {
        "ticker": market.get("ticker"),
        "title": market.get("title") or event_title,
        "subtitle": market.get("subtitle") or "",
        "status": market.get("status"),
        "yes_bid_dollars": market.get("yes_bid_dollars"),
        "yes_ask_dollars": market.get("yes_ask_dollars"),
        "last_price_dollars": market.get("last_price_dollars"),
        "volume_fp": market.get("volume_fp"),
        "open_interest_fp": market.get("open_interest_fp"),
        "close_time": market.get("close_time"),
        "event_ticker": market.get("event_ticker"),
        "event_title": event_title,
        "series_ticker": series_ticker,
    }

@app.get("/api/kalshi/markets")
async def kalshi_markets():
    found = {}
    pages_scanned = 0
    scanned = 0
    event_count = 0
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            # Events provide important context: a market title alone may be just a team name.
            cursor = None
            for _ in range(8):
                params = {"status": "open", "limit": 200, "with_nested_markets": "true"}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get(f"{BASE}/events", params=params)
                response.raise_for_status()
                payload = response.json()
                pages_scanned += 1
                events = payload.get("events") or []
                event_count += len(events)
                for event in events:
                    title = str(event.get("title") or "")
                    subtitle = str(event.get("sub_title") or "")
                    series = str(event.get("series_ticker") or "")
                    ticker = str(event.get("event_ticker") or "")
                    if not NFL_TERMS.search(f"{title} {subtitle} {series} {ticker}"):
                        continue
                    for market in event.get("markets") or []:
                        if market.get("status") != "open":
                            continue
                        key = market.get("ticker")
                        if key:
                            found[key] = normalize(market, title, series)
                cursor = payload.get("cursor")
                if not cursor:
                    break

            # Supplement event matches with individual markets from the first few pages.
            cursor = None
            for _ in range(5):
                params = {"status": "open", "limit": 1000}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get(f"{BASE}/markets", params=params)
                response.raise_for_status()
                payload = response.json()
                pages_scanned += 1
                markets = payload.get("markets") or []
                scanned += len(markets)
                for market in markets:
                    searchable = " ".join(str(market.get(k) or "") for k in
                                          ("title", "subtitle", "ticker", "event_ticker"))
                    if NFL_TERMS.search(searchable) and market.get("ticker"):
                        found.setdefault(market["ticker"], normalize(market))
                cursor = payload.get("cursor")
                if not cursor:
                    break
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Kalshi public API request failed: {type(exc).__name__}") from exc

    result = list(found.values())
    result.sort(key=lambda m: float(m.get("volume_fp") or 0), reverse=True)
    return {
        "source": "Kalshi public REST API",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "count": len(result),
        "markets": result[:100],
        "pages_scanned": pages_scanned,
        "events_scanned": event_count,
        "individual_markets_scanned": scanned,
        "note": "Public data; partial paginated scan, not an exhaustive NFL feed. Verify contract terms, liquidity, and timestamps.",
    }
