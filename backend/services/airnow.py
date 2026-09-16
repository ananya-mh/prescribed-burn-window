"""AirNow client: the forecast AQI for a point, one number per day.

Air quality is the one input we are allowed to not have. Large parts of rural
Northern California -- exactly where prescribed burns happen -- have no AirNow
reporting area, and the API answers that with an empty list and HTTP 200. So
nothing in this module raises: on any problem we log and return {}, and the
caller reports air quality as "unknown" alongside a normal weather assessment.

Endpoint note: the retiring /aq/forecast/latLong/ path is deliberately not used
here; /aq/forecast/current/ is its replacement and takes no distance param.
"""

import logging
import time
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import httpx

from core import config

logger = logging.getLogger(__name__)

# location -> (expiry timestamp, result). AirNow allows 500 requests/hour/key
# with no soft throttle, and forecasts are issued once a day, so re-fetching on
# every map click would burn the quota for no new information.
_cache: Dict[Tuple[float, float], Tuple[float, Dict[date, Optional[int]]]] = {}


async def fetch_daily_aqi(
    client: httpx.AsyncClient, lat: float, lon: float
) -> Dict[date, Optional[int]]:
    """Return {date: max AQI across pollutants} for the days AirNow forecasts.

    The value is None for a day AirNow reports without a usable number. Returns
    {} when there is no data for this point or the request fails -- never raises.
    How many days come back is up to the local air district (often 1-3, not 5).
    """
    if not config.AIRNOW_API_KEY:
        logger.warning("AIRNOW_API_KEY is not set; skipping air quality lookup")
        return {}

    key = (round(lat, 2), round(lon, 2))
    cached = _cache.get(key)
    if cached is not None and cached[0] > time.time():
        return cached[1]

    try:
        response = await client.get(
            config.AIRNOW_BASE_URL + "/aq/forecast/current/",
            params={
                "latitude": lat,
                "longitude": lon,
                "format": "application/json",
                "API_KEY": config.AIRNOW_API_KEY,
            },
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # network error, timeout, bad status, bad JSON
        logger.warning("AirNow request failed for %s, %s: %s", lat, lon, exc)
        return {}

    # AirNow reports some errors in a 200 response body, so check the shape.
    if isinstance(payload, dict):
        messages = [
            error.get("Message", "")
            for error in (payload.get("WebServiceError") or [])
            if isinstance(error, dict)
        ]
        text = " ".join(messages).lower()
        if "no reporting area" in text or "no current forecasts" in text:
            # Not a failure: much of rural California has no reporting area,
            # which is a stable answer worth caching. Without this, every click
            # on a rural point -- the main use case -- re-hits the 500/hour cap.
            logger.info("AirNow has no forecast for %s, %s", lat, lon)
            _cache[key] = (time.time() + config.AIRNOW_CACHE_TTL_SECONDS, {})
            return {}
        logger.warning("AirNow returned an error for %s, %s: %s", lat, lon, messages)
        return {}

    if not isinstance(payload, list):
        logger.warning("AirNow returned unexpected data for %s, %s", lat, lon)
        return {}

    result = _max_aqi_by_date(payload)
    _cache[key] = (time.time() + config.AIRNOW_CACHE_TTL_SECONDS, result)
    return result


def _max_aqi_by_date(rows: List[dict]) -> Dict[date, Optional[int]]:
    """Collapse one-row-per-pollutant-per-day into one AQI per day.

    The worst pollutant sets the day's AQI, which is how AirNow itself reports
    it and how an air district decides whether to issue a burn permit.
    """
    daily: Dict[date, Optional[int]] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue

        valid_date = _parse_date(row.get("dateValid"))
        if valid_date is None:
            continue

        aqi = _parse_aqi(row.get("aqi"))

        # Record the day even with no number, so the caller can tell "AirNow
        # covers this place but had no value" from "no data at all".
        current = daily.get(valid_date)
        if aqi is not None and (current is None or aqi > current):
            daily[valid_date] = aqi
        elif valid_date not in daily:
            daily[valid_date] = None

    return daily


def _parse_date(value) -> Optional[date]:
    """Parse AirNow's "YYYY-MM-DD" dateValid; None if it is missing or odd."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_aqi(value) -> Optional[int]:
    """AirNow sends -1 when it issued a category but no number. Treat anything
    negative as missing -- it must never slip through as a value below the
    AQI limit and make a smoky day look like a GO."""
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if value < 0:
        return None
    return value
