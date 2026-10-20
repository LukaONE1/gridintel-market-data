# GRIDINTEL phone-first deployment starter

This bundle is designed to be deployed from a phone using GitHub's website and Render's dashboard. It is a starter project, not already hosted.

## Files
- `index.html`: GRIDINTEL mobile-friendly beta.
- `main.py`: FastAPI service. Serves the frontend and provides `/api/kalshi/markets`.
- `requirements.txt`: Python dependencies.

## Deploy from Android (no terminal required)
1. Download and extract this ZIP on your phone.
2. Sign in to GitHub in your mobile browser and create a **new public repository** named `gridintel-market-data`. Do not add a README/license during repo creation.
3. Open the repository, use **Add file → Upload files**, and upload `index.html`, `main.py`, and `requirements.txt` from the extracted folder. Commit the changes.
4. Open Render in your browser and sign up/sign in.
5. Choose **New → Web Service**, connect GitHub, and select `gridintel-market-data`.
6. Set:
   - Language: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance type: Free, if offered and suitable
7. Create/deploy the service and wait for the build to finish.
8. Open the Render service URL ending in `.onrender.com`.
9. Add `/health` to the URL. It should return JSON with `"ok": true`.
10. Add `/api/kalshi/markets` to the URL. It should return JSON with `source`, `retrieved_at`, `count`, and `markets`.
11. Return to the base URL and open **Market Signals** in GRIDINTEL.

## Important
- Use a strong unique password and enable two-factor authentication where possible. Never put API keys or passwords in repository files.
- A public GitHub repository exposes the source code publicly. This starter contains no secrets.
- Free hosting can sleep when idle, so the first request may take a little time.
- NFL filtering is keyword-based and may miss valid markets or include false positives.
- Novig and FanDuel are not connected yet. This does not place bets or prove a betting edge.
- Before a commercial/public launch, add stronger validation, caching/rate limiting, monitoring, tests, and deployment security.

Official references:
- Render FastAPI deployment: https://render.com/docs/deploy-fastapi
- Kalshi public market-data quick start: https://docs.kalshi.com/getting_started/quick_start_market_data
