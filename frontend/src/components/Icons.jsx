// Small inline icons, one per burn parameter, so a blocking reason can be
// recognised at a glance rather than read. Inline SVG rather than an icon
// package: six glyphs is not worth a dependency.

const BASE = "h-4 w-4 shrink-0";

function Svg({ children, title }) {
  return (
    <svg
      className={BASE}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-label={title}
    >
      {children}
    </svg>
  );
}

export function WindIcon() {
  return (
    <Svg title="wind">
      <path d="M3 8h10a3 3 0 1 0-3-3" />
      <path d="M3 12h14a3 3 0 1 1-3 3" />
      <path d="M3 16h7" />
    </Svg>
  );
}

export function HumidityIcon() {
  return (
    <Svg title="humidity">
      <path d="M12 2.7S6 9.2 6 13a6 6 0 0 0 12 0c0-3.8-6-10.3-6-10.3z" />
    </Svg>
  );
}

export function TemperatureIcon() {
  return (
    <Svg title="temperature">
      <path d="M10 13.5V5a2 2 0 1 1 4 0v8.5a4 4 0 1 1-4 0z" />
    </Svg>
  );
}

export function PrecipitationIcon() {
  return (
    <Svg title="precipitation">
      <path d="M6 14a4 4 0 0 1 .8-7.9 5 5 0 0 1 9.7 1.2A3.5 3.5 0 0 1 17 14" />
      <path d="M8 18l-1 2M12 18l-1 2M16 18l-1 2" />
    </Svg>
  );
}

export function AirQualityIcon() {
  return (
    <Svg title="air quality">
      <path d="M4 8h12a2.5 2.5 0 1 0-2.5-2.5" />
      <path d="M4 12h15" />
      <path d="M4 16h9a2.5 2.5 0 1 1-2.5 2.5" />
    </Svg>
  );
}

export function ClockIcon() {
  return (
    <Svg title="burn window">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </Svg>
  );
}
