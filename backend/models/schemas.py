"""Pydantic models for the burn window API.

These are the contract between the services, the threshold engine, and the
endpoint. Endpoints return these models, never raw dicts.
"""

from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class Location(BaseModel):
    lat: float
    lon: float


class Range(BaseModel):
    """A min/max pair for a parameter that varies across the burn hours."""

    min: float
    max: float


class DayConditions(BaseModel):
    """The measured/forecast values for one day. AQI is optional because
    AirNow does not cover every California location or every forecast day."""

    wind_speed_mph: Range
    humidity_pct: Range
    temp_max_f: float
    precip_prob_pct: float
    aqi: Optional[int] = None


class ParameterAssessment(BaseModel):
    """How one parameter fared: ok | marginal | blocking | unknown."""

    status: str
    detail: str


class BurnWindow(BaseModel):
    """The longest run of consecutive hours that sit inside every threshold."""

    start_hour: int
    end_hour: int  # exclusive: a 10:00-15:00 window is start 10, end 15
    hours: int


class DayAssessment(BaseModel):
    date: date
    status: str  # GO | MARGINAL | NO-GO
    blocking_factors: List[str]
    conditions: DayConditions
    thresholds: Dict[str, ParameterAssessment]
    # The workable window this verdict is based on, or None when the day has
    # no run long enough to be worth mobilising a crew for.
    burn_window: Optional[BurnWindow] = None
    # True when NWS gave us only part of the burn window for this day, which
    # happens for today once the day is already underway.
    partial_day: bool = False


class BurnWindowResponse(BaseModel):
    location: Location
    generated_at: datetime
    days: List[DayAssessment]


class AreaAssessment(BaseModel):
    """One named burn area and its outlook, for the ranked area list."""

    # NWS fire weather zone id, e.g. "CAZ130" - what this area actually is.
    zone_id: str
    name: str
    location: Location
    days: List[DayAssessment]
    # Best verdict across the forecast, so the list can be ranked and the UI
    # can colour a marker without re-deriving it.
    best_status: str
    best_window_hours: int
    # Set when this area's forecast could not be fetched; days is then empty.
    error: Optional[str] = None


class BurnAreasResponse(BaseModel):
    generated_at: datetime
    areas: List[AreaAssessment]


class HealthResponse(BaseModel):
    status: str


class HourWeather(BaseModel):
    """One hour of the forecast, inside the daytime burn window."""

    hour: int  # local hour of day, 0-23
    wind_mph: float
    humidity_pct: float
    temp_f: float
    precip_prob_pct: float


class DailyWeather(BaseModel):
    """What nws.py returns per day, before air quality is merged in.

    Hours are kept individually rather than pre-aggregated: a burn needs a
    run of consecutive workable hours, and collapsing the day to a single
    min/max would let one calm or humid hour veto an otherwise good day.
    """

    date: date
    hours: List[HourWeather]
    partial_day: bool
