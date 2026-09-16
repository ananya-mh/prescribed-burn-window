# Prescribed Burn Window Finder

Checks whether weather and air quality conditions are safe for a prescribed burn at a
California location, with a 5-day outlook. Click a point on the map, get a
GO / MARGINAL / NO-GO verdict per day plus the specific reason.

- **Live app:** https://prescribed-burn-window.vercel.app
- **API:** https://burn-window-api.onrender.com/api/burn-areas

Phase 1: live API calls and threshold comparison. No database, no model.

> The API is on Render's free tier, which sleeps after 15 minutes idle. The first request after
> a quiet spell takes about a minute to wake, and that first call also rebuilds the cache by
> re-scanning all 30 zones. The UI says so while it waits.

## How it decides

For each day it looks at the NWS hourly forecast between **09:00 and 17:00 local** — prescribed
burns are a daylight operation — and finds the **longest run of consecutive hours** in which
every parameter is inside its threshold. A burn needs 3–6 hours of active burning plus setup and
mop-up, so a run shorter than 4 hours is a NO-GO even if the weather is otherwise perfect.

This matters more than it sounds. Collapsing the whole day into one min/max range instead lets a
single calm or humid morning hour veto a day with a workable afternoon: against live forecast
data that rule rejected genuine 5-, 6- and 7-hour windows.

Thresholds live in `backend/core/thresholds.py`:

| Parameter | Burn window | Why |
|---|---|---|
| Wind | 3–15 mph | Below 3, smoke won't disperse. Above 15, fire spread is uncontrollable. |
| Humidity | 25–55% | Below 25, fuel is too dry and fire escapes. Above 55, fuel won't ignite. |
| Temperature | below 90°F | Above 90 compounds with low humidity. |
| Precipitation | below 30% chance | Rain likely wastes burn prep. |
| AQI | below 100 | Above 100 the air district won't permit burning. |

**GO** = a window of 4+ hours with every parameter inside its threshold. **NO-GO** = no such
window, either because a parameter is out of range or because the good hours don't last long
enough. **MARGINAL** = a workable window, but at least one parameter sits within 10% of a
boundary (or air quality is unknown).

Air quality comes from two sources. **AirNow** is the air district's own forecast and is what a
burn permit is judged against, so it always wins — but its reporting areas track population
centres, so across California's wildland fire zones it covers only about 5% of day-values.
**Open-Meteo** fills the rest with a keyless modelled AQI, labelled `modeled` in the response and
`(modeled, not agency-issued)` in the detail text. If neither has data the day reads **unknown**,
which never blocks a day but does cap it at MARGINAL.

## Running it

**Backend** (Python 3.9+):
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # optional: add a free AirNow key
.venv/bin/uvicorn main:app --reload --port 8000
```
Without an `AIRNOW_API_KEY` the app still runs; air quality just reports as unknown.
Get a free key at https://docs.airnowapi.org/account/request/

**Frontend** (Node 20+):
```bash
cd frontend
npm install
npm run dev
```

**Tests** — the threshold engine is the core logic and is the module under test:
```bash
cd backend && .venv/bin/python -m pytest tests -v
```

## Deploying

Backend on **Render**, frontend on **Vercel**. No Docker: both platforms build from source, and
Render does not auto-detect a Dockerfile anyway.

Deploy the backend first — the two reference each other's URLs.

1. **Render** — New → Blueprint, point it at this repo. `render.yaml` supplies the root
   directory, commands, Python version and health check. It will prompt for `AIRNOW_API_KEY`
   (leave `CORS_ORIGINS` blank for now). Note the service URL.
2. **Vercel** — import the repo, set **Root Directory** to `frontend`. The Vite preset handles
   the rest. Set `VITE_API_BASE_URL` to the Render URL.
   `VITE_*` vars are baked in at build time, so changing this later needs a redeploy, not a restart.
3. **Back on Render** — set `CORS_ORIGINS` to the Vercel URL and redeploy.

Two settings account for essentially every "the backend isn't loading" failure here, and neither
shows up in the logs:

- **`CORS_ORIGINS` is matched as an exact string.** `https://app.vercel.app/` (trailing slash),
  `app.vercel.app` (no scheme) and a different capitalisation all fail silently. Copy the origin
  from the browser console error or `window.location.origin`.
- **`VITE_API_BASE_URL` is compiled into the bundle at build time.** Saving it in Vercel does
  nothing to an existing deployment — you must redeploy. To check which backend the live site is
  actually calling:
  ```bash
  curl -s https://prescribed-burn-window.vercel.app/ | grep -o '/assets/[^"]*\.js'
  # then fetch that asset and grep it for onrender.com vs 127.0.0.1
  ```

**First load is slow.** Render's free tier spins a service down after 15 minutes idle and takes
about a minute to wake. A cold start also means empty caches, so the first `/api/burn-areas`
re-runs the full zone scan. The UI says so rather than looking broken. The 1-hour cache TTLs
therefore rarely reach expiry on a low-traffic site — worst case that is roughly 120 AirNow
requests an hour, comfortably under the 500/hour cap.

## Endpoints

Base URL: `https://burn-window-api.onrender.com`

- [`GET /api/burn-window?lat=&lon=`](https://burn-window-api.onrender.com/api/burn-window?lat=38.706&lon=-120.3297) — 5-day assessment for a California point
- [`GET /api/burn-areas`](https://burn-window-api.onrender.com/api/burn-areas) — ~30 California wildland **NWS fire weather zones** ranked most
  promising first. Cached server-side for an hour, since one scan costs ~60 NWS requests.
  `backend/core/areas.py` is generated by `scripts/generate_areas.py`, which derives each
  coordinate from the zone's official polygon and verifies it lands inside that zone.
- [`GET /api/health`](https://burn-window-api.onrender.com/api/health)

## Data sources

- **NWS** (`api.weather.gov`) — no key, requires a User-Agent. Two-step lookup:
  `/points/{lat},{lon}` returns the `forecastHourly` URL.
- **AirNow** (`www.airnowapi.org`) — free key. Uses `/aq/forecast/current/`; the older
  `/aq/forecast/latLong/` was retired 2026-09-30. Responses are cached for an hour because
  AirNow allows only 500 requests/hour/key.
- **Open-Meteo** (`air-quality-api.open-meteo.com`) — no key. Modelled US AQI, used only where
  AirNow has no reporting area, which is most wildland. Always labelled as modelled.
