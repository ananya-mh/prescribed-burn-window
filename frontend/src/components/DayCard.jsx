import { useState } from "react";
import StatusBadge from "./StatusBadge";
import {
  AirQualityIcon,
  ClockIcon,
  HumidityIcon,
  PrecipitationIcon,
  TemperatureIcon,
  WindIcon,
} from "./Icons";

// Keyed by the parameter names the API uses in `thresholds` and
// `blocking_factors`. "burn_window" is not a weather parameter - it means no
// run of hours was long enough to mobilise a crew for.
const PARAMETER_ICONS = {
  wind: WindIcon,
  humidity: HumidityIcon,
  temperature: TemperatureIcon,
  precipitation: PrecipitationIcon,
  air_quality: AirQualityIcon,
  burn_window: ClockIcon,
};

// The five parameters, in the order we show them, with a label and a function
// that turns the day's `conditions` into a display value.
const PARAMETERS = [
  {
    key: "wind",
    label: "Wind",
    format: (c) => `${c.wind_speed_mph.min}-${c.wind_speed_mph.max} mph`,
  },
  {
    key: "humidity",
    label: "Humidity",
    format: (c) => `${c.humidity_pct.min}-${c.humidity_pct.max}%`,
  },
  {
    key: "temperature",
    label: "Temperature",
    format: (c) => `${c.temp_max_f}°F max`,
  },
  {
    key: "precipitation",
    label: "Precipitation",
    format: (c) => `${c.precip_prob_pct}% chance`,
  },
  {
    key: "air_quality",
    label: "Air quality",
    format: (c) => (c.aqi === null ? "unknown" : `AQI ${c.aqi}`),
  },
];

const FACTOR_LABELS = {
  wind: "wind",
  humidity: "humidity",
  temperature: "temperature",
  precipitation: "rain",
  air_quality: "air quality",
  burn_window: "no long enough window",
};

// Full literal class strings - see the note in StatusBadge.jsx.
const ROW_STYLES = {
  ok: "border-slate-200 bg-white text-slate-700",
  marginal: "border-yellow-300 bg-yellow-50 text-yellow-900",
  blocking: "border-red-300 bg-red-50 text-red-900",
  unknown: "border-slate-200 bg-slate-50 text-slate-400",
};

const CARD_ACCENTS = {
  "GO": "border-t-4 border-t-green-500",
  "MARGINAL": "border-t-4 border-t-yellow-500",
  "NO-GO": "border-t-4 border-t-red-500",
};

// The burn window is the most actionable thing on the page - it tells a crew
// when to start and how long they have - so it is tinted by verdict rather
// than left as body text.
const WINDOW_STYLES = {
  "GO": "text-green-700",
  "MARGINAL": "text-yellow-700",
  "NO-GO": "text-slate-600",
};

// "2026-09-15" -> "Tue, Sep 15". Split by hand rather than using `new Date`,
// which would read the string as UTC midnight and can land on the day before.
function formatDate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

// 10:00-15:00 across 5 hours. end_hour is exclusive.
function formatWindow(window) {
  const pad = (h) => String(h).padStart(2, "0");
  return `${pad(window.start_hour)}:00-${pad(window.end_hour)}:00`;
}

export default function DayCard({ day }) {
  const [expanded, setExpanded] = useState(false);
  const blocked = day.blocking_factors.length > 0;

  return (
    <div
      className={`flex-1 rounded-lg border border-slate-200 bg-white shadow-sm ${
        CARD_ACCENTS[day.status] || "border-t-4 border-t-slate-400"
      }`}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full flex-col gap-2 p-4 text-left hover:bg-slate-50"
        aria-expanded={expanded}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-slate-900">
            {formatDate(day.date)}
          </span>
          <StatusBadge status={day.status} />
        </div>

        {/* When you can burn, and for how long. */}
        {day.burn_window ? (
          <span
            className={`flex items-center gap-1.5 text-lg font-bold ${
              WINDOW_STYLES[day.status] || "text-slate-800"
            }`}
          >
            <ClockIcon />
            {formatWindow(day.burn_window)}
            <span className="text-sm font-medium">
              · {day.burn_window.hours}h
            </span>
          </span>
        ) : (
          <span className="text-sm font-medium text-slate-500">
            No workable window
          </span>
        )}

        {/* Why you can't, if you can't. The answer to "why not today?" */}
        {blocked ? (
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-semibold text-red-700">
            {day.blocking_factors.map((factor) => {
              const Icon = PARAMETER_ICONS[factor];
              return (
                <span key={factor} className="flex items-center gap-1">
                  {Icon && <Icon />}
                  {FACTOR_LABELS[factor] || factor}
                </span>
              );
            })}
          </span>
        ) : (
          <span className="text-xs text-slate-500">
            All parameters within range
          </span>
        )}

        {day.partial_day && (
          <span className="text-xs italic text-slate-500">
            Partial day — only part of today's burn window remains
          </span>
        )}

        <span className="text-xs text-slate-400">
          {expanded ? "Hide details" : "Show details"}
        </span>
      </button>

      {expanded && (
        <div className="flex flex-col gap-2 border-t border-slate-200 p-4">
          <p className="text-xs text-slate-500">
            {day.burn_window
              ? "Conditions across the burn window above."
              : "Conditions across the whole day, showing what ruled it out."}
          </p>
          {PARAMETERS.map((parameter) => {
            const threshold = day.thresholds[parameter.key];
            const Icon = PARAMETER_ICONS[parameter.key];
            return (
              <div
                key={parameter.key}
                className={`rounded border p-2 text-sm ${
                  ROW_STYLES[threshold.status] || ROW_STYLES.unknown
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 font-medium">
                    {Icon && <Icon />}
                    {parameter.label}
                  </span>
                  <span>{parameter.format(day.conditions)}</span>
                </div>
                <p className="mt-1 text-xs opacity-80">{threshold.detail}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
