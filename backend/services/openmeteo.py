"""Open-Meteo air quality: a keyless fallback for where AirNow does not reach.

AirNow reporting areas track population centres, so most California wildland --
exactly where prescribed burns happen -- has no AirNow forecast at all. This
fills those gaps. The tradeoff is that Open-Meteo's US AQI is *modelled* from
the CAMS ensemble rather than issued by an air district, so it is reported with
its source and must not be mistaken for a permit decision.

No API key and no registration. Like airnow.py, nothing here raises.
"""

import logging
import time
from datetime import date, datetime
from typing import Dict, Optional, Tuple

import httpx

from core import config

logger = logging.getLogger(__name__)

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Same shape and reasoning as the AirNow cache: identical answers for an hour.
_cache: Dict[Tuple[float, float], Tuple[float, Dict[date, Optional[int]]]] = {}


async def fetch_daily_aqi(
    client: httpx.AsyncClient, lat: float, lon: float
) -> Dict[date, Optional[int]]:
    """Return {date: worst modelled US AQI that day}, or {} on any problem."""
    key = (round(lat, 2), round(lon, 2))
    cached = _cache.get(key)
    if cached is not None and cached[0] > time.time():
        return cached[1]

    try:
        response = await client.get(
            URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "us_aqi",
                # Ask for local times so the dates line up with the NWS days.
                "timezone": "America/Los_Angeles",
                "forecast_days": config.FORECAST_DAYS,
            },
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # network, timeout, bad status, bad JSON
        logger.warning("Open-Meteo request failed for %s, %s: %s", lat, lon, exc)
        return {}

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    values = hourly.get("us_aqi") or []

    daily: Dict[date, Optional[int]] = {}
    for timestamp, value in zip(times, values):
        if value is None:
            continue
        try:
            # With timezone set these are naive local times, so the first ten
            # characters are already the local date.
            day = datetime.strptime(timestamp[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        current = daily.get(day)
        if current is None or value > current:
            daily[day] = int(value)

    _cache[key] = (time.time() + config.AIRNOW_CACHE_TTL_SECONDS, daily)
    return daily
