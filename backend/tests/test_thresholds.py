"""Tests for the burn window threshold engine.

Run from backend/:  pytest
"""

from core.thresholds import (
    AQI_MAX,
    HUMIDITY_MAX_PCT,
    HUMIDITY_MIN_PCT,
    MARGINAL_BAND_PCT,
    PRECIP_MAX_PCT,
    TEMP_MAX_F,
    WIND_MAX_MPH,
    WIND_MIN_MPH,
    assess_day,
)
from models.schemas import DayConditions, Range


def make_day(
    wind_min=5,
    wind_max=10,
    humidity_min=35,
    humidity_max=45,
    temp_max_f=78,
    precip_prob_pct=5,
    aqi=42,
):
    """A known-good day, with any parameter overridable per test."""
    return DayConditions(
        wind_speed_mph=Range(min=wind_min, max=wind_max),
        humidity_pct=Range(min=humidity_min, max=humidity_max),
        temp_max_f=temp_max_f,
        precip_prob_pct=precip_prob_pct,
        aqi=aqi,
    )


# --- Required spec cases ----------------------------------------------------


def test_all_params_good_is_go():
    verdict = assess_day(make_day())

    assert verdict.status == "GO"
    assert verdict.blocking_factors == []
    assert set(verdict.thresholds) == {
        "wind",
        "humidity",
        "temperature",
        "precipitation",
        "air_quality",
    }


def test_wind_14_mph_is_marginal():
    # 14 is inside the 3-15 window but within 10% of the 15 mph limit.
    verdict = assess_day(make_day(wind_max=14))

    assert verdict.status == "MARGINAL"
    assert verdict.blocking_factors == []
    assert verdict.thresholds["wind"].status == "marginal"
    assert verdict.thresholds["wind"].detail == "5-14 mph, close to 15 mph limit"


def test_wind_20_mph_is_no_go_blocking_on_wind():
    verdict = assess_day(make_day(wind_max=20))

    assert verdict.status == "NO-GO"
    assert verdict.blocking_factors == ["wind"]
    assert verdict.thresholds["wind"].status == "blocking"
    assert verdict.thresholds["wind"].detail == "5-20 mph, exceeds 15 mph limit"


def test_multiple_blocking_params_are_all_listed():
    verdict = assess_day(
        make_day(wind_max=25, humidity_min=10, temp_max_f=101, precip_prob_pct=80)
    )

    assert verdict.status == "NO-GO"
    assert verdict.blocking_factors == [
        "wind",
        "humidity",
        "temperature",
        "precipitation",
    ]


# --- Boundary values: inclusive, so inside the window but marginal ----------


def test_wind_exactly_at_min_is_marginal_not_blocking():
    verdict = assess_day(make_day(wind_min=WIND_MIN_MPH, wind_max=10))

    assert verdict.status == "MARGINAL"
    assert verdict.blocking_factors == []
    assert verdict.thresholds["wind"].status == "marginal"
    assert verdict.thresholds["wind"].detail == "3-10 mph, close to 3 mph minimum"


def test_wind_exactly_at_max_is_marginal_not_blocking():
    verdict = assess_day(make_day(wind_max=WIND_MAX_MPH))

    assert verdict.status == "MARGINAL"
    assert verdict.blocking_factors == []
    assert verdict.thresholds["wind"].status == "marginal"
    assert verdict.thresholds["wind"].detail == "5-15 mph, close to 15 mph limit"


def test_humidity_exactly_at_min_is_marginal_not_blocking():
    verdict = assess_day(make_day(humidity_min=HUMIDITY_MIN_PCT, humidity_max=45))

    assert verdict.status == "MARGINAL"
    assert verdict.blocking_factors == []
    assert verdict.thresholds["humidity"].status == "marginal"
    assert verdict.thresholds["humidity"].detail == "25-45%, close to 25% minimum"


def test_humidity_exactly_at_max_is_marginal_not_blocking():
    verdict = assess_day(make_day(humidity_max=HUMIDITY_MAX_PCT))

    assert verdict.status == "MARGINAL"
    assert verdict.blocking_factors == []
    assert verdict.thresholds["humidity"].status == "marginal"
    assert verdict.thresholds["humidity"].detail == "35-55%, close to 55% limit"


def test_just_outside_a_boundary_blocks():
    assert assess_day(make_day(wind_max=WIND_MAX_MPH + 0.5)).status == "NO-GO"
    assert assess_day(make_day(wind_min=WIND_MIN_MPH - 0.5)).status == "NO-GO"
    assert (
        assess_day(make_day(humidity_max=HUMIDITY_MAX_PCT + 0.5)).status == "NO-GO"
    )
    assert (
        assess_day(make_day(humidity_min=HUMIDITY_MIN_PCT - 0.5)).status == "NO-GO"
    )


# --- Air quality: missing data is non-blocking but caps the day at MARGINAL --


def test_missing_aqi_is_unknown_marginal_and_never_blocking():
    verdict = assess_day(make_day(aqi=None))

    assert verdict.status == "MARGINAL"
    assert verdict.thresholds["air_quality"].status == "unknown"
    assert "air_quality" not in verdict.blocking_factors
    assert verdict.blocking_factors == []
    assert (
        verdict.thresholds["air_quality"].detail
        == "no AirNow data for this location/date"
    )


def test_missing_aqi_does_not_mask_a_real_blocker():
    verdict = assess_day(make_day(aqi=None, wind_max=20))

    assert verdict.status == "NO-GO"
    assert verdict.blocking_factors == ["wind"]


def test_aqi_over_limit_is_no_go():
    verdict = assess_day(make_day(aqi=105))

    assert verdict.status == "NO-GO"
    assert verdict.blocking_factors == ["air_quality"]
    assert verdict.thresholds["air_quality"].status == "blocking"
    assert verdict.thresholds["air_quality"].detail == "AQI 105, exceeds 100 limit"


def test_aqi_just_under_limit_is_marginal():
    verdict = assess_day(make_day(aqi=AQI_MAX - 1))

    assert verdict.status == "MARGINAL"
    assert verdict.thresholds["air_quality"].status == "marginal"
    assert verdict.thresholds["air_quality"].detail == "AQI 99, close to 100 limit"


# --- One-sided limits -------------------------------------------------------


def test_temperature_over_limit_blocks():
    verdict = assess_day(make_day(temp_max_f=TEMP_MAX_F + 5))

    assert verdict.blocking_factors == ["temperature"]
    assert verdict.thresholds["temperature"].detail == "95°F, exceeds 90°F limit"


def test_precipitation_over_limit_blocks():
    verdict = assess_day(make_day(precip_prob_pct=PRECIP_MAX_PCT + 15))

    assert verdict.blocking_factors == ["precipitation"]
    assert (
        verdict.thresholds["precipitation"].detail == "45% chance, exceeds 30% limit"
    )


# --- Regression: this test is what pins MARGINAL_BAND_PCT at 10% ------------


def test_spec_sample_day_is_go_pins_the_10_percent_band():
    """The exact sample day from the project spec must come out GO with every
    parameter "ok".

    This is the reason MARGINAL_BAND_PCT is 0.10 and not the 0.15 the spec's
    prose mentions: at a 15% band, 78°F would fall inside 15% of the 90°F limit
    (>= 76.5) and this day would be MARGINAL, contradicting the spec's own
    worked example. If someone raises the band back to 15%, this test fails
    first and explains why.
    """
    verdict = assess_day(
        DayConditions(
            wind_speed_mph=Range(min=5, max=10),
            humidity_pct=Range(min=35, max=45),
            temp_max_f=78,
            precip_prob_pct=5,
            aqi=42,
        )
    )

    assert MARGINAL_BAND_PCT == 0.10
    assert verdict.status == "GO"
    assert verdict.blocking_factors == []
    assert all(
        assessment.status == "ok" for assessment in verdict.thresholds.values()
    )

    # And the detail strings match the spec's documented format exactly.
    assert verdict.thresholds["wind"].detail == "5-10 mph, within 3-15 range"
    assert verdict.thresholds["humidity"].detail == "35-45%, within 25-55 range"
    assert verdict.thresholds["temperature"].detail == "78°F, below 90°F limit"
    assert verdict.thresholds["precipitation"].detail == "5% chance, below 30% limit"
    assert verdict.thresholds["air_quality"].detail == "AQI 42, below 100 limit"


def test_verdict_unpacks_like_a_tuple():
    status, blocking_factors, thresholds = assess_day(make_day())

    assert status == "GO"
    assert blocking_factors == []
    assert len(thresholds) == 5


# --- Burn window: a day is judged on its longest run of workable hours -------
#
# These cover the flaw the hourly data exposed: collapsing 09:00-17:00 into one
# min/max range let a single calm or humid morning hour veto a day that had a
# perfectly workable afternoon window.

from models.schemas import HourWeather  # noqa: E402
from core.thresholds import (  # noqa: E402
    MIN_BURN_HOURS,
    find_longest_burn_window,
    hour_is_within_window,
    summarize_hours,
)


def _hour(hour, wind=8.0, humidity=40.0, temp=75.0, precip=0.0):
    """A workable hour by default; override one field to make it unworkable."""
    return HourWeather(
        hour=hour,
        wind_mph=wind,
        humidity_pct=humidity,
        temp_f=temp,
        precip_prob_pct=precip,
    )


def test_hour_is_within_window_accepts_a_good_hour():
    assert hour_is_within_window(_hour(10)) is True


def test_hour_is_within_window_rejects_each_bad_parameter():
    assert hour_is_within_window(_hour(10, wind=2.0)) is False
    assert hour_is_within_window(_hour(10, wind=20.0)) is False
    assert hour_is_within_window(_hour(10, humidity=80.0)) is False
    assert hour_is_within_window(_hour(10, humidity=10.0)) is False
    assert hour_is_within_window(_hour(10, temp=95.0)) is False
    assert hour_is_within_window(_hour(10, precip=60.0)) is False


def test_find_longest_burn_window_returns_every_hour_when_all_are_good():
    hours = [_hour(h) for h in range(9, 17)]
    assert len(find_longest_burn_window(hours)) == 8


def test_find_longest_burn_window_skips_a_humid_morning():
    # "...ooooo" - the shape Sacramento showed on 2026-09-18.
    hours = [_hour(h, humidity=80.0) for h in range(9, 12)]
    hours += [_hour(h) for h in range(12, 17)]
    window = find_longest_burn_window(hours)
    assert [h.hour for h in window] == [12, 13, 14, 15, 16]


def test_find_longest_burn_window_picks_the_longer_of_two_runs():
    hours = [_hour(9), _hour(10), _hour(11, wind=25.0)]
    hours += [_hour(12), _hour(13), _hour(14), _hour(15)]
    assert len(find_longest_burn_window(hours)) == 4


def test_find_longest_burn_window_does_not_bridge_a_gap_in_the_forecast():
    # 12:00 is missing, so this is two short runs, not one long one.
    hours = [_hour(9), _hour(10), _hour(11), _hour(13), _hour(14)]
    assert len(find_longest_burn_window(hours)) == 3


def test_find_longest_burn_window_returns_empty_when_nothing_works():
    hours = [_hour(h, wind=30.0) for h in range(9, 17)]
    assert find_longest_burn_window(hours) == []


def test_summarize_hours_reports_the_range_across_the_window():
    hours = [_hour(9, wind=4.0, humidity=50.0, temp=70.0, precip=5.0),
             _hour(10, wind=12.0, humidity=30.0, temp=80.0, precip=20.0)]
    conditions = summarize_hours(hours, aqi=42)
    assert (conditions.wind_speed_mph.min, conditions.wind_speed_mph.max) == (4.0, 12.0)
    assert (conditions.humidity_pct.min, conditions.humidity_pct.max) == (30.0, 50.0)
    assert conditions.temp_max_f == 80.0
    assert conditions.precip_prob_pct == 20.0  # worst hour wins
    assert conditions.aqi == 42


def test_short_window_is_no_go_even_when_every_parameter_is_fine():
    # Three perfect hours is not enough to mobilise a crew for.
    hours = [_hour(h) for h in range(9, 12)]
    verdict = assess_day(summarize_hours(hours, aqi=42), window_hours=len(hours))
    assert verdict.status == "NO-GO"
    assert verdict.blocking_factors == ["burn_window"]


def test_long_enough_window_of_good_hours_is_go():
    hours = [_hour(h) for h in range(9, 9 + MIN_BURN_HOURS)]
    verdict = assess_day(summarize_hours(hours, aqi=42), window_hours=len(hours))
    assert verdict.status == "GO"


def test_workable_afternoon_is_not_vetoed_by_a_bad_morning():
    """Regression: Susanville 2026-09-17 had a 7-hour window that the old
    whole-day min/max logic reported as NO-GO on humidity."""
    hours = [_hour(9, humidity=22.0)]  # too dry, on its own a blocker
    hours += [_hour(h, humidity=45.0) for h in range(10, 17)]
    window = find_longest_burn_window(hours)
    assert len(window) == 7
    verdict = assess_day(summarize_hours(window, aqi=42), window_hours=len(window))
    assert verdict.status == "GO"
    assert verdict.blocking_factors == []


# --- Ranking areas ----------------------------------------------------------

from datetime import date  # noqa: E402

from core.thresholds import assess_days, best_of  # noqa: E402
from models.schemas import DailyWeather  # noqa: E402


def _day(day_number, hours):
    return DailyWeather(
        date=date(2026, 9, day_number), hours=hours, partial_day=False
    )


def test_assess_days_maps_aqi_onto_the_right_day():
    weather = [_day(16, [_hour(h) for h in range(9, 17)]),
               _day(17, [_hour(h) for h in range(9, 17)])]
    days = assess_days(weather, {date(2026, 9, 16): 42})
    assert days[0].conditions.aqi == 42
    assert days[0].status == "GO"
    # No AirNow entry for the 17th, so it is unknown and capped at MARGINAL.
    assert days[1].conditions.aqi is None
    assert days[1].status == "MARGINAL"
    assert "air_quality" not in days[1].blocking_factors


def test_assess_days_reports_the_window_it_judged():
    weather = [_day(16, [_hour(h, humidity=85.0) for h in range(9, 12)]
                   + [_hour(h) for h in range(12, 17)])]
    days = assess_days(weather, {})
    assert days[0].burn_window.start_hour == 12
    assert days[0].burn_window.end_hour == 17
    assert days[0].burn_window.hours == 5


def test_best_of_prefers_go_over_a_longer_marginal_window():
    weather = [
        _day(16, [_hour(h, humidity=52.0) for h in range(9, 17)]),  # 8h, marginal
        _day(17, [_hour(h) for h in range(9, 14)]),                 # 5h, clean
    ]
    days = assess_days(weather, {date(2026, 9, 16): 42, date(2026, 9, 17): 42})
    assert (days[0].status, days[1].status) == ("MARGINAL", "GO")
    # A shorter GO still outranks a longer MARGINAL.
    assert best_of(days) == ("GO", 5)


def test_best_of_breaks_ties_on_window_length():
    weather = [_day(16, [_hour(h) for h in range(9, 13)]),   # 4h
               _day(17, [_hour(h) for h in range(9, 17)])]   # 8h
    days = assess_days(weather, {date(2026, 9, 16): 42, date(2026, 9, 17): 42})
    assert best_of(days) == ("GO", 8)


def test_best_of_handles_an_area_with_no_forecast():
    assert best_of([]) == ("NO-GO", 0)
