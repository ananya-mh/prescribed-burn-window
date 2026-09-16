"""FastAPI app for the Prescribed Burn Window Finder.

Two endpoints, no database. Every request fetches fresh weather and air
quality for the requested point, compares them against the burn window
thresholds, and returns a 5-day assessment.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from core import config
from core.thresholds import assess_days
from models.schemas import (
    BurnAreasResponse,
    BurnWindowResponse,
    HealthResponse,
    Location,
)
from services import aqi
from services.area_scan import get_burn_areas
from services.nws import NWSError, fetch_daily_forecast

logging.basicConfig(level=logging.INFO)

# httpx logs every request URL at INFO, and the AirNow URL carries the API key
# as a query parameter, so that would write the key into the logs.
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(
    title="Prescribed Burn Window Finder",
    description="Is it safe to run a prescribed burn at this California location?",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/burn-window", response_model=BurnWindowResponse)
async def burn_window(
    lat: float = Query(..., description="Latitude, within California"),
    lon: float = Query(..., description="Longitude, within California"),
) -> BurnWindowResponse:
    if not (config.CA_LAT_MIN <= lat <= config.CA_LAT_MAX) or not (
        config.CA_LON_MIN <= lon <= config.CA_LON_MAX
    ):
        raise HTTPException(
            status_code=400,
            detail="This tool covers California only. Pick a point inside the state.",
        )

    async with httpx.AsyncClient() as client:
        # Weather and air quality are independent lookups, so run them together
        # rather than paying for one after the other.
        try:
            weather_days, aqi_by_date = await asyncio.gather(
                fetch_daily_forecast(client, lat, lon),
                aqi.fetch_daily_aqi(client, lat, lon),
            )
        except NWSError as exc:
            # Weather is required; without it there is nothing to assess.
            # Air quality is not - fetch_daily_aqi returns {} instead of raising.
            raise HTTPException(status_code=502, detail=str(exc))

    days = assess_days(weather_days, aqi_by_date)

    return BurnWindowResponse(
        location=Location(lat=lat, lon=lon),
        generated_at=datetime.now(timezone.utc),
        days=days,
    )


@app.get("/api/burn-areas", response_model=BurnAreasResponse)
async def burn_areas() -> BurnAreasResponse:
    """Every named California burn area, most promising first.

    The scan is shared and cached for an hour, so this is cheap to call even
    though a cold refresh fetches a forecast for each area.
    """
    async with httpx.AsyncClient() as client:
        return await get_burn_areas(client)
