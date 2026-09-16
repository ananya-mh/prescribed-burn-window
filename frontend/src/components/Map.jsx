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
const AREA_COLORS = {
  "GO": "#16a34a",
  "MARGINAL": "#ca8a04",
  "NO-GO": "#dc2626",
};

const CALIFORNIA_CENTER = [37.5, -119.5];
const CALIFORNIA_ZOOM = 6;

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

export default function Map({ location, onSelect, areas = [] }) {
  return (
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
      <ClickHandler onSelect={onSelect} />

      {areas.map((area) => (
        <CircleMarker
          key={area.name}
          center={[area.location.lat, area.location.lon]}
          radius={6}
          pathOptions={{
            color: "#ffffff",
            weight: 1.5,
            fillColor: AREA_COLORS[area.best_status] || "#64748b",
            fillOpacity: 0.9,
          }}
          eventHandlers={{
            click: () => onSelect(area.location.lat, area.location.lon, area.name),
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
  );
}
