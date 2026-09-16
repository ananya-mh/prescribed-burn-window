import { useEffect } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Leaflet's default icon points at image paths that don't survive bundling,
// so we hand it the URLs Vite generates for those assets.
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// Leaflet path colours, not Tailwind classes, so these are plain hex values.
// They match the badge colours so the map and the list read as one scale.
const AREA_COLORS = {
  "GO": "#16a34a",
  "MARGINAL": "#ca8a04",
  "NO-GO": "#dc2626",
};

const LEGEND = [
  { status: "GO", label: "GO — burn window available" },
  { status: "MARGINAL", label: "MARGINAL — close to a limit" },
  { status: "NO-GO", label: "NO-GO — outside limits" },
];

const CALIFORNIA_CENTER = [37.5, -119.5];
const CALIFORNIA_ZOOM = 6;
const ZONE_ZOOM = 9;

// Listens for clicks on the map and reports the clicked coordinates upward.
function ClickHandler({ onSelect }) {
  useMapEvents({
    click(event) {
      onSelect(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

// Leaflet measures its container once on creation and caches the result, so if
// the container changes size afterwards -- which it does here when the area
// list loads beside it -- the tiles are laid out for the old width. Watching
// the container and calling invalidateSize keeps the two in step.
function ResizeHandler() {
  const map = useMap();

  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);

  return null;
}

// Flies to a zone picked from the list. `focus.id` changes on every pick, so
// choosing the same zone twice still moves the map.
function FocusHandler({ focus }) {
  const map = useMap();

  useEffect(() => {
    if (focus) {
      map.flyTo([focus.lat, focus.lon], ZONE_ZOOM, { duration: 0.8 });
    }
  }, [map, focus]);

  return null;
}

function Legend() {
  return (
    <div className="absolute bottom-3 left-3 z-[1000] rounded-md border border-slate-200 bg-white/95 px-3 py-2 shadow-md">
      <p className="mb-1 text-xs font-semibold text-slate-700">
        Fire weather zones
      </p>
      <ul className="flex flex-col gap-1">
        {LEGEND.map((entry) => (
          <li
            key={entry.status}
            className="flex items-center gap-2 text-xs text-slate-600"
          >
            <span
              className="inline-block h-3 w-3 shrink-0 rounded-full border border-white shadow-sm"
              style={{ backgroundColor: AREA_COLORS[entry.status] }}
            />
            {entry.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Map({ location, onSelect, areas = [], focus }) {
  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={CALIFORNIA_CENTER}
        zoom={CALIFORNIA_ZOOM}
        scrollWheelZoom={true}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ResizeHandler />
        <FocusHandler focus={focus} />
        <ClickHandler onSelect={onSelect} />

        {areas.map((area) => (
          <CircleMarker
            key={area.zone_id || area.name}
            center={[area.location.lat, area.location.lon]}
            radius={6}
            pathOptions={{
              color: "#ffffff",
              weight: 1.5,
              fillColor: AREA_COLORS[area.best_status] || "#64748b",
              fillOpacity: 0.9,
            }}
            eventHandlers={{
              click: (event) => {
                // Without this the map's own click handler also fires and
                // re-selects the bare coordinates, dropping the zone name.
                L.DomEvent.stopPropagation(event);
                onSelect(area.location.lat, area.location.lon, area.name);
              },
            }}
          >
            <Tooltip>
              {area.name} - {area.best_status}
              {area.best_window_hours > 0 && ` (${area.best_window_hours}h)`}
            </Tooltip>
          </CircleMarker>
        ))}

        {location && (
          <Marker position={[location.lat, location.lon]} icon={defaultIcon} />
        )}
      </MapContainer>

      <Legend />
    </div>
  );
}
