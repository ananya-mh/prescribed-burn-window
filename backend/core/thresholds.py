"""Burn window threshold definitions and comparison logic.

Pure functions only: no I/O, no API calls, no global state. Feed in one day's
conditions, get back a per-parameter verdict and an overall GO / MARGINAL /
NO-GO. This is the core decision logic of the app, so it lives in one file and
is covered by tests in tests/test_thresholds.py.
"""

from typing import Dict, List, NamedTuple, Optional, Tuple

from datetime import date as date_type

from models.schemas import (
    BurnWindow,
    DailyWeather,
    DayAssessment,
    DayConditions,
    HourWeather,
    ParameterAssessment,
    Range,
)

# --- Burn window thresholds -------------------------------------------------
# Named constants, never magic numbers inline. These are the conditions under
# which a prescribed burn is generally considered safe and permittable.

WIND_MIN_MPH = 3  # below this, smoke won't disperse
WIND_MAX_MPH = 15  # above this, fire spread is uncontrollable
HUMIDITY_MIN_PCT = 25  # below this, fuel is too dry and fire escapes
HUMIDITY_MAX_PCT = 55  # above this, fuel won't ignite properly
TEMP_MAX_F = 90  # above this, compounds with low humidity
PRECIP_MAX_PCT = 30  # above this, rain likely wastes burn prep
AQI_MAX = 100  # above this, the air district won't permit burning

# A prescribed burn needs 3-6 hours of active burning plus setup and mop-up,
# so a shorter run of good conditions is not worth mobilising a crew for.
# Judging the whole day as one block instead would let a single calm or humid
# morning hour veto a day that has a perfectly workable afternoon window.
MIN_BURN_HOURS = 4

# "Close to a boundary" = within 10% of it. The written spec says 15%, but 15%
# contradicts the spec's own worked example: a sample day at 78 F against the
# 90 F limit is marked "ok" / overall GO, yet 15% of 90 would flag anything at
# or above 76.5 F as marginal. 10% satisfies every worked example, including
# "wind at 14 mph is MARGINAL" (10% of 15 makes >= 13.5 mph marginal).
# Deliberate: please don't "fix" this back to 15. See the regression test
# test_spec_sample_day_is_go_pins_the_10_percent_band.
MARGINAL_BAND_PCT = 0.10

# Status values used by ParameterAssessment.
OK = "ok"
MARGINAL = "marginal"
BLOCKING = "blocking"
UNKNOWN = "unknown"

# Overall day verdicts.
GO = "GO"
MARGINAL_DAY = "MARGINAL"
NO_GO = "NO-GO"


class DayVerdict(NamedTuple):
    """What assess_day returns.

    A NamedTuple so it can be unpacked like a plain tuple but still read with
    named attributes, and so it stays a pure stdlib value (no Pydantic
    validation cost in the hot path).
    """

    status: str  # GO | MARGINAL | NO-GO
    blocking_factors: List[str]
    thresholds: Dict[str, ParameterAssessment]


def _band(boundary: float) -> float:
    """How far from a boundary still counts as 'close to' it."""
    return abs(boundary) * MARGINAL_BAND_PCT


def _fmt(value: float) -> str:
    """Format a number for a detail string without a trailing '.0'."""
    if float(value) == int(value):
        return str(int(value))
    return str(round(float(value), 1))


def evaluate_range(
    low_value: float,
    high_value: float,
    low_bound: float,
    high_bound: float,
    unit: str,
) -> ParameterAssessment:
    """Assess a two-sided parameter (wind, humidity).

    The day's [low_value, high_value] must sit inside [low_bound, high_bound].
    Boundaries are inclusive: wind of exactly 3 or exactly 15 mph is still
    inside the window, just marginal.
    """
    observed = "{0}-{1}{2}".format(_fmt(low_value), _fmt(high_value), unit)

    if high_value > high_bound:
        return ParameterAssessment(
            status=BLOCKING,
            detail="{0}, exceeds {1}{2} limit".format(observed, _fmt(high_bound), unit),
        )
    if low_value < low_bound:
        return ParameterAssessment(
            status=BLOCKING,
            detail="{0}, below {1}{2} minimum".format(observed, _fmt(low_bound), unit),
        )
    if high_value >= high_bound - _band(high_bound):
        return ParameterAssessment(
            status=MARGINAL,
            detail="{0}, close to {1}{2} limit".format(observed, _fmt(high_bound), unit),
        )
    if low_value <= low_bound + _band(low_bound):
        return ParameterAssessment(
            status=MARGINAL,
            detail="{0}, close to {1}{2} minimum".format(
                observed, _fmt(low_bound), unit
            ),
        )
    return ParameterAssessment(
        status=OK,
        detail="{0}, within {1}-{2} range".format(
            observed, _fmt(low_bound), _fmt(high_bound)
        ),
    )


def evaluate_max(
    value: float,
    limit: float,
    value_text: str,
    limit_text: str,
) -> ParameterAssessment:
    """Assess a one-sided parameter (temperature, precipitation, AQI).

    value_text and limit_text are the already-formatted phrases for this
    parameter, e.g. "78°F" and "90°F", or "5% chance" and "30%".
    """
    if value > limit:
        return ParameterAssessment(
            status=BLOCKING,
            detail="{0}, exceeds {1} limit".format(value_text, limit_text),
        )
    if value >= limit - _band(limit):
        return ParameterAssessment(
            status=MARGINAL,
            detail="{0}, close to {1} limit".format(value_text, limit_text),
        )
    return ParameterAssessment(
        status=OK,
        detail="{0}, below {1} limit".format(value_text, limit_text),
    )


def evaluate_wind(low_mph: float, high_mph: float) -> ParameterAssessment:
    return evaluate_range(low_mph, high_mph, WIND_MIN_MPH, WIND_MAX_MPH, " mph")


def evaluate_humidity(low_pct: float, high_pct: float) -> ParameterAssessment:
    return evaluate_range(
        low_pct, high_pct, HUMIDITY_MIN_PCT, HUMIDITY_MAX_PCT, "%"
    )


def evaluate_temperature(temp_f: float) -> ParameterAssessment:
    return evaluate_max(
        temp_f,
        TEMP_MAX_F,
        "{0}°F".format(_fmt(temp_f)),
        "{0}°F".format(_fmt(TEMP_MAX_F)),
    )


def evaluate_precipitation(precip_pct: float) -> ParameterAssessment:
    return evaluate_max(
        precip_pct,
        PRECIP_MAX_PCT,
        "{0}% chance".format(_fmt(precip_pct)),
        "{0}%".format(_fmt(PRECIP_MAX_PCT)),
    )


def evaluate_air_quality(aqi: Optional[int]) -> ParameterAssessment:
    """AirNow has no coverage in much of rural California, so a missing AQI is
    a normal outcome, not an error. Unknown never blocks a day, but it does cap
    it at MARGINAL so the user knows to check with their air district."""
    if aqi is None:
        return ParameterAssessment(
            status=UNKNOWN,
            detail="no AirNow data for this location/date",
        )
    return evaluate_max(
        aqi,
        AQI_MAX,
        "AQI {0}".format(_fmt(aqi)),
        _fmt(AQI_MAX),
    )


def hour_is_within_window(hour: HourWeather) -> bool:
    """Is this single hour inside every weather threshold?

    Air quality is deliberately not considered here: it is a daily figure, not
    an hourly one, so it is applied to the day once a window has been found.
    """
    return (
        WIND_MIN_MPH <= hour.wind_mph <= WIND_MAX_MPH
        and HUMIDITY_MIN_PCT <= hour.humidity_pct <= HUMIDITY_MAX_PCT
        and hour.temp_f <= TEMP_MAX_F
        and hour.precip_prob_pct <= PRECIP_MAX_PCT
    )


def find_longest_burn_window(hours: List[HourWeather]) -> List[HourWeather]:
    """Return the longest run of consecutive workable hours, or [] if none.

    Hours must be adjacent on the clock to count as a run, so a gap in the
    forecast splits the window rather than silently bridging it.
    """
    best: List[HourWeather] = []
    current: List[HourWeather] = []

    for hour in hours:
        if not hour_is_within_window(hour):
            current = []
            continue
        if current and hour.hour != current[-1].hour + 1:
            current = []
        current.append(hour)
        if len(current) > len(best):
            best = list(current)

    return best


def summarize_hours(hours: List[HourWeather], aqi: Optional[int]) -> DayConditions:
    """Collapse a run of hours into the conditions to report and judge."""
    return DayConditions(
        wind_speed_mph=Range(
            min=min(h.wind_mph for h in hours), max=max(h.wind_mph for h in hours)
        ),
        humidity_pct=Range(
            min=min(h.humidity_pct for h in hours),
            max=max(h.humidity_pct for h in hours),
        ),
        temp_max_f=max(h.temp_f for h in hours),
        precip_prob_pct=max(h.precip_prob_pct for h in hours),
        aqi=aqi,
    )


def assess_day(
    conditions: DayConditions, window_hours: Optional[int] = None
) -> DayVerdict:
    """Run one day's conditions through every threshold and combine them.

    Overall status:
      - no long enough window   -> NO-GO (blocked on "burn_window")
      - any blocking parameter  -> NO-GO (blocking_factors lists them)
      - else any marginal or unknown parameter -> MARGINAL
      - else -> GO

    window_hours is the length of the longest run of workable hours. Pass None
    to judge the conditions on their own without the window rule.
    """
    thresholds = {
        "wind": evaluate_wind(
            conditions.wind_speed_mph.min, conditions.wind_speed_mph.max
        ),
        "humidity": evaluate_humidity(
            conditions.humidity_pct.min, conditions.humidity_pct.max
        ),
        "temperature": evaluate_temperature(conditions.temp_max_f),
        "precipitation": evaluate_precipitation(conditions.precip_prob_pct),
        "air_quality": evaluate_air_quality(conditions.aqi),
    }

    # Fixed, human-meaningful order so blocking_factors reads the same way
    # every time rather than following dict insertion by accident.
    names = ["wind", "humidity", "temperature", "precipitation", "air_quality"]

    blocking_factors = [
        name for name in names if thresholds[name].status == BLOCKING
    ]
    has_soft_flag = any(
        thresholds[name].status in (MARGINAL, UNKNOWN) for name in names
    )

    if window_hours is not None and window_hours < MIN_BURN_HOURS:
        # Good conditions that never last long enough are still a NO-GO, and
        # if no single parameter is at fault the window itself is the reason.
        status = NO_GO
        if not blocking_factors:
            blocking_factors = ["burn_window"]
    elif blocking_factors:
        status = NO_GO
    elif has_soft_flag:
        status = MARGINAL_DAY
    else:
        status = GO

    return DayVerdict(
        status=status,
        blocking_factors=blocking_factors,
        thresholds=thresholds,
    )


def assess_days(
    weather_days: List[DailyWeather],
    aqi_by_date: Dict[date_type, Optional[int]],
) -> List[DayAssessment]:
    """Turn a location's forecast into one assessment per day.

    Pure: the callers fetch the data, this decides what it means. Shared by the
    single-location endpoint and the area scan so they cannot drift apart.
    """
    assessments = []

    for weather in weather_days:
        aqi = aqi_by_date.get(weather.date)
        window = find_longest_burn_window(weather.hours)

        if len(window) >= MIN_BURN_HOURS:
            # Judge the day on the window a crew would actually burn in.
            conditions = summarize_hours(window, aqi)
            burn_window = BurnWindow(
                start_hour=window[0].hour,
                end_hour=window[-1].hour + 1,
                hours=len(window),
            )
        else:
            # No workable window, so report the whole day to show what ruled it
            # out rather than the handful of hours that happened to pass.
            conditions = summarize_hours(weather.hours, aqi)
            burn_window = None

        verdict = assess_day(conditions, window_hours=len(window))
        assessments.append(
            DayAssessment(
                date=weather.date,
                status=verdict.status,
                blocking_factors=verdict.blocking_factors,
                conditions=conditions,
                thresholds=verdict.thresholds,
                burn_window=burn_window,
                partial_day=weather.partial_day,
            )
        )

    return assessments


# Best first, so an area list can be ranked by how promising it is.
STATUS_RANK = {GO: 0, MARGINAL_DAY: 1, NO_GO: 2}


def best_of(days: List[DayAssessment]) -> Tuple[str, int]:
    """The most promising verdict across a forecast, and its window length."""
    if not days:
        return NO_GO, 0
    best = min(days, key=lambda d: (STATUS_RANK.get(d.status, 3),
                                    -(d.burn_window.hours if d.burn_window else 0)))
    return best.status, best.burn_window.hours if best.burn_window else 0
