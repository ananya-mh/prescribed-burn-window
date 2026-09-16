"""National Weather Service client.

Fetches the hourly forecast for a point and boils it down to one summary per
day, covering only the hours a prescribed burn would actually happen in.

The NWS API needs no key, but it does require a User-Agent, and it is a
two-step lookup: /points/{lat},{lon} tells you which forecast URL to call.
"""

import re
from datetime import date as date_type
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx

from core import config
from models.schemas import DailyWeather, HourWeather

# NWS rejects requests without a User-Agent at the CDN edge (and answers with
# an HTML error page, not JSON). Accept keeps it on the documented GeoJSON.
_HEADERS = {
    "User-Agent": config.NWS_USER_AGENT,
    "Accept": "application/geo+json",
}

_NUMBER = re.compile(r"\d+(?:\.\d+)?")

# The burn window is BURN_HOUR_START..BURN_HOUR_END, so a complete day has
# this many hourly periods.
_FULL_DAY_HOURS = config.BURN_HOUR_END - config.BURN_HOUR_START


class NWSError(Exception):
    """Anything that went wrong talking to NWS, with a message fit to show a
    user. The caller only needs to catch this one."""


def parse_wind_speed(text: Optional[str]) -> Optional[Tuple[float, float]]:
    """Turn an NWS wind speed string into (min_mph, max_mph).

    The hourly endpoint sends single values ("12 mph"); the 12-hour endpoint
    sends ranges ("5 to 15 mph"). Anything without a number in it, such as
    "Light and variable" or "", has no usable speed and returns None.
    """
    if not text:
        return None
    numbers = [float(n) for n in _NUMBER.findall(text)]
    if not numbers:
        return None
    return min(numbers), max(numbers)


def _parse_local_time(start_time: str) -> Optional[datetime]:
    """Parse an NWS startTime, keeping its local offset.

    NWS has already localized these to the forecast point's time zone, so the
    hour and the date we read off them are the local ones we want. Converting
    to UTC first would shift days and break the burn-hour filter.
    """
    if not start_time:
        return None
    if start_time.endswith("Z"):
        start_time = start_time[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(start_time)
    except ValueError:
        return None


async def _get_json(client: httpx.AsyncClient, url: str) -> dict:
    """GET a NWS URL and return the decoded JSON, or raise NWSError."""
    try:
        response = await client.get(
            url, headers=_HEADERS, timeout=config.HTTP_TIMEOUT_SECONDS
        )
    except httpx.TimeoutException:
        raise NWSError("The National Weather Service took too long to respond.")
    except httpx.RequestError:
        raise NWSError("Could not reach the National Weather Service.")

    if response.status_code == 404:
        raise NWSError(
            "The National Weather Service has no forecast for this location. "
            "It may be offshore or outside the United States."
        )
    if response.status_code != 200:
        raise NWSError(
            "The National Weather Service returned an error "
            f"(HTTP {response.status_code})."
        )

    # An error page from the CDN is HTML, so do not assume the body is JSON.
    try:
        return response.json()
    except ValueError:
        raise NWSError("The National Weather Service returned an unreadable response.")


async def _fetch_hourly_url(client: httpx.AsyncClient, lat: float, lon: float) -> str:
    """Step one: ask /points which hourly forecast URL covers this location."""
    # NWS redirects requests with more than four decimal places, and the client
    # is not guaranteed to follow redirects, so round before asking.
    url = f"{config.NWS_BASE_URL}/points/{round(lat, 4)},{round(lon, 4)}"
    payload = await _get_json(client, url)
    hourly_url = (payload.get("properties") or {}).get("forecastHourly")
    if not hourly_url:
        raise NWSError(
            "The National Weather Service did not return an hourly forecast "
            "for this location."
        )
    return hourly_url


def _group_burn_hours_by_date(periods: List[dict]) -> Dict[date_type, List[dict]]:
    """Keep only hours inside the burn window and group them by local date."""
    by_date: Dict[date_type, List[dict]] = {}
    for period in periods:
        local_time = _parse_local_time(period.get("startTime", ""))
        if local_time is None:
            continue
        if not config.BURN_HOUR_START <= local_time.hour < config.BURN_HOUR_END:
            continue
        by_date.setdefault(local_time.date(), []).append(period)
    return by_date


def _day_hours(periods: List[dict]) -> List[HourWeather]:
    """Turn one day's raw hourly periods into HourWeather, newest data wins.

    An hour is dropped if wind, humidity or temperature is missing, since we
    cannot judge it. A null precipitation probability means no chance of rain
    rather than missing data, so it becomes 0.
    """
    hours: List[HourWeather] = []

    for period in periods:
        local_time = _parse_local_time(period.get("startTime", ""))
        if local_time is None:
            continue

        wind = parse_wind_speed(period.get("windSpeed"))
        humidity = (period.get("relativeHumidity") or {}).get("value")
        # Temperature is a bare number; the sibling temperatureUnit is "F"
        # because we never ask NWS for SI units.
        temp = period.get("temperature")
        if wind is None or humidity is None or temp is None:
            continue

        precip = (period.get("probabilityOfPrecipitation") or {}).get("value")

        hours.append(
            HourWeather(
                hour=local_time.hour,
                # Use the gustier end of a range, since that is what decides
                # whether the fire stays controllable.
                wind_mph=wind[1],
                humidity_pct=float(humidity),
                temp_f=float(temp),
                precip_prob_pct=float(precip) if precip is not None else 0.0,
            )
        )

    hours.sort(key=lambda h: h.hour)
    return hours


async def fetch_daily_forecast(
    client: httpx.AsyncClient, lat: float, lon: float
) -> List[DailyWeather]:
    """Return up to FORECAST_DAYS daily burn-hour summaries for a location.

    Raises NWSError if the forecast could not be fetched or contained nothing
    usable.
    """
    hourly_url = await _fetch_hourly_url(client, lat, lon)
    payload = await _get_json(client, hourly_url)

    periods = (payload.get("properties") or {}).get("periods") or []
    if not periods:
        raise NWSError("The National Weather Service returned an empty forecast.")

    by_date = _group_burn_hours_by_date(periods)

    days: List[DailyWeather] = []
    for day in sorted(by_date):
        hours = _day_hours(by_date[day])
        if hours:
            days.append(
                DailyWeather(
                    date=day,
                    hours=hours,
                    partial_day=len(hours) < _FULL_DAY_HOURS,
                )
            )

    if not days:
        raise NWSError(
            "The National Weather Service forecast had no usable daytime hours "
            "for this location."
        )

    return days[: config.FORECAST_DAYS]
