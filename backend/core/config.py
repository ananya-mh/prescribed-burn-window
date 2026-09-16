"""Configuration constants, read from the environment where needed."""

import os

from dotenv import load_dotenv

load_dotenv()

# NWS requires a User-Agent identifying the app and a contact address.
# Requests without one are rejected at the CDN edge.
NWS_BASE_URL = "https://api.weather.gov"
NWS_USER_AGENT = "(prescribed-burn-window, hegde.ana@northeastern.edu)"

# AirNow. Note: aqs.epa.gov is EPA's separate regulatory-data API, not this one.
AIRNOW_BASE_URL = "https://www.airnowapi.org"
AIRNOW_API_KEY = os.environ.get("AIRNOW_API_KEY", "")

# AirNow allows 500 requests/hour/key and issues forecasts once a day, so we
# hold each location's result for an hour.
AIRNOW_CACHE_TTL_SECONDS = 3600

HTTP_TIMEOUT_SECONDS = 15.0

# The ranked area list. NWS asks for roughly a request a second; one scan is
# ~60 requests done at most once an hour, so the sustained rate is far below
# that even though the scan runs a few requests at a time to stay responsive.
AREA_SCAN_CONCURRENCY = 4
AREA_SCAN_TTL_SECONDS = 3600

# Prescribed burns run during daylight. Aggregating all 24 hours would pull in
# overnight humidity and calm wind and make nearly every day a NO-GO.
BURN_HOUR_START = 9
BURN_HOUR_END = 17

FORECAST_DAYS = 5

# Rough bounding box for California, used to reject out-of-area requests.
CA_LAT_MIN, CA_LAT_MAX = 32.5, 42.1
CA_LON_MIN, CA_LON_MAX = -124.5, -114.1

# The local dev server, plus whatever the deployment sets. The frontend is on a
# different origin in production, so its URL arrives as configuration rather
# than a code change: CORS_ORIGINS="https://foo.vercel.app,https://bar.app"
_EXTRA_ORIGINS = os.environ.get("CORS_ORIGINS", "")
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"] + [
    origin.strip() for origin in _EXTRA_ORIGINS.split(",") if origin.strip()
]
