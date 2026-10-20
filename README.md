# GRIDINTEL v0.5 — Android update

## Recommended easiest upgrade
1. In GitHub repository `gridintel-market-data`, open `index.html`, tap pencil/Edit.
2. Replace its contents with the supplied `index.html` file content using a mobile text editor, then Commit changes. Alternatively upload a replacement file through GitHub if your browser permits overwriting.
3. Update `main.py` from this package if you want the v0.5 health version label; existing v0.4 backend is compatible with the new index.html.
4. On Render, redeploy the latest GitHub commit if auto deploy does not start.
5. Reload your Render app, press Check Kalshi markets, and choose Top 10 or All.

Only `index.html` is required for the dashboard upgrade if the deployed v0.4 backend is already returning `usable_quote`, bid, ask, volume and close time. Keep `requirements.txt` unchanged.

Notes: Bid/ask quotes are not verified win probabilities. The displayed American odds are mathematical equivalents of Kalshi YES ask prices, not sportsbook prices. The backend scans a subset of the public API and does not guarantee exhaustive NFL coverage. Existing paper records remain in browser localStorage if you use the same browser and origin.
