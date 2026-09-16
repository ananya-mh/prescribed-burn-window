"""Scan every named burn area and rank them by how promising they look.

One scan covers ~30 areas and costs ~60 NWS requests, so the whole result is
cached for an hour and shared by all callers. That keeps the sustained rate to
roughly one request a minute, well inside what NWS asks for, even though the
scan itself runs a handful of requests concurrently to stay responsive.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import httpx

from core import config
from core.areas import AREAS, Area
from core.thresholds import assess_days, best_of
from models.schemas import AreaAssessment, BurnAreasResponse, Location
from services.aqi import fetch_daily_aqi
from services.nws import NWSError, fetch_daily_forecast

logger = logging.getLogger(__name__)

# One shared entry: (expiry timestamp, response).
_cache: Optional[Tuple[float, BurnAreasResponse]] = None

# Guards against a thundering herd: if several requests arrive on a cold cache,
# only the first does the work and the rest wait for it.
_lock = asyncio.Lock()


async def _scan_area(
    client: httpx.AsyncClient, semaphore: asyncio.Semaphore, area: Area
) -> AreaAssessment:
    """Assess a single area, degrading to an error entry rather than failing."""
    async with semaphore:
        location = Location(lat=area.lat, lon=area.lon)
        try:
            weather_days, aqi_by_date = await asyncio.gather(
                fetch_daily_forecast(client, area.lat, area.lon),
                fetch_daily_aqi(client, area.lat, area.lon),
            )
        except NWSError as exc:
            logger.warning("area scan failed for %s: %s", area.name, exc)
            return AreaAssessment(
                zone_id=area.zone_id, name=area.name, location=location, days=[],
                best_status="NO-GO", best_window_hours=0, error=str(exc),
            )

        days = assess_days(weather_days, aqi_by_date)
        status, hours = best_of(days)
        return AreaAssessment(
            zone_id=area.zone_id, name=area.name, location=location, days=days,
            best_status=status, best_window_hours=hours,
        )


async def get_burn_areas(client: httpx.AsyncClient) -> BurnAreasResponse:
    """Return every area, best-looking first. Cached for AREA_SCAN_TTL_SECONDS."""
    global _cache

    if _cache is not None and _cache[0] > time.time():
        return _cache[1]

    async with _lock:
        # Another request may have refreshed it while we waited for the lock.
        if _cache is not None and _cache[0] > time.time():
            return _cache[1]

        semaphore = asyncio.Semaphore(config.AREA_SCAN_CONCURRENCY)
        started = time.time()
        areas = await asyncio.gather(
            *[_scan_area(client, semaphore, area) for area in AREAS]
        )
        logger.info("scanned %d areas in %.1fs", len(areas), time.time() - started)

        ranked = sorted(
            areas,
            key=lambda a: (
                {"GO": 0, "MARGINAL": 1, "NO-GO": 2}.get(a.best_status, 3),
                -a.best_window_hours,
                a.name,
            ),
        )
        response = BurnAreasResponse(
            generated_at=datetime.now(timezone.utc), areas=ranked
        )
        _cache = (time.time() + config.AREA_SCAN_TTL_SECONDS, response)
        return response
