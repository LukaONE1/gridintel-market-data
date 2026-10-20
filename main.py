from datetime import datetime, timezone
from pathlib import Path
import re
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI(title="GRIDINTEL Market Data Service", version="0.2.0")
ROOT = Path(__file__).resolve().parent
KALSHI_BASE = "https://external-api.kalshi.com/trade-api/v2"
NFL_TERMS = re.compile(
    r"\\b(nfl|football|chiefs|eagles|cowboys|ravens|bills|49ers|packers|"
    r"bears|lions|broncos|chargers|jets|giants|steelers|bengals|browns|"
    r"texans|colts|jaguars|titans|dolphins|patriots|raiders|saints|falcons|"
    r"panthers|buccaneers|seahawks|commanders|rams|vikings)\\b",
    re.IGNORECASE,
)

@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")

@app.get("/health")
def health():
    return {"ok": True, "service": "GRIDINTEL", "checked_at": datetime.now(timezone.utc).isoformat()}

@app.get("/api/kalshi/markets")
async def kalshi_markets():
    params = {"status": "open", "limit": 1000}
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(f"{KALSHI_BASE}/markets", params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Could not retrieve Kalshi public markets: {type(exc).__name__}") from exc

    filtered = []
    for market in payload.get("markets", []):
        title = str(market.get("title") or "")
        ticker = str(market.get("ticker") or "")
        subtitle = str(market.get("subtitle") or "")
        if not NFL_TERMS.search(f"{title} {ticker} {subtitle}"):
            continue
        filtered.append({
            "ticker": ticker, "title": title, "subtitle": subtitle,
            "status": market.get("status"),
            "yes_bid_dollars": market.get("yes_bid_dollars"),
            "yes_ask_dollars": market.get("yes_ask_dollars"),
            "last_price_dollars": market.get("last_price_dollars"),
            "volume_fp": market.get("volume_fp"),
            "open_interest_fp": market.get("open_interest_fp"),
            "close_time": market.get("close_time"),
            "event_ticker": market.get("event_ticker"),
        })
    return {
        "source": "Kalshi public REST API",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "count": len(filtered), "markets": filtered[:100],
        "note": "Keyword-filtered public markets; verify contract equivalence before sportsbook comparisons.",
    }
