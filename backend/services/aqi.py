"""Air quality for a location, preferring the air district's own forecast.

AirNow is what a California air district actually regulates against, so it wins
wherever it exists. It only covers about 5% of the day-values across our
wildland fire zones, though, so Open-Meteo's modelled AQI fills the rest. Every
reading carries its source, because "the district forecast 46" and "a global
model estimates 46" are not the same claim.
"""

import asyncio
from datetime import date
from typing import Dict

import httpx

from models.schemas import AqiReading
from services import airnow, openmeteo

AIRNOW = "airnow"
MODELED = "modeled"


async def fetch_daily_aqi(
    client: httpx.AsyncClient, lat: float, lon: float
) -> Dict[date, AqiReading]:
    """Merge both sources, AirNow first, day by day."""
    official, modeled = await asyncio.gather(
        airnow.fetch_daily_aqi(client, lat, lon),
        openmeteo.fetch_daily_aqi(client, lat, lon),
    )

    readings: Dict[date, AqiReading] = {}
    for day, value in modeled.items():
        if value is not None:
            readings[day] = AqiReading(value=value, source=MODELED)
    # Applied second so an air district's number always overrides the model.
    for day, value in official.items():
        if value is not None:
            readings[day] = AqiReading(value=value, source=AIRNOW)
    return readings
