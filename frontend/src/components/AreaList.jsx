import { useEffect, useRef } from "react";
import StatusBadge from "./StatusBadge";

// NWS fire weather zones, already ranked best-first by the backend. Clicking
// one selects it and flies the map to it; clicking its dot on the map selects
// it here, which is what `selectedName` scrolls into view.
export default function AreaList({
  areas,
  loading,
  error,
  onSelect,
  selectedName,
}) {
  const listRef = useRef(null);

  // A highlighted row is useless if it is scrolled out of sight, which it
  // usually is in a 30-row panel when the selection came from the map.
  useEffect(() => {
    if (!selectedName || !listRef.current) return;
    const row = listRef.current.querySelector('[data-selected="true"]');
    if (row) row.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedName]);

  if (loading) {
    // The backend sleeps when idle on the free tier, and a cold start also
    // means an empty cache, so the first load really can take this long.
    return (
      <div className="text-sm text-slate-600">
        <p>Loading zones...</p>
        <p className="mt-1 text-xs text-slate-500">
          The backend sleeps when idle, so the first load can take up to a
          minute.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
        Could not load burn areas: {error}
      </p>
    );
  }

  if (!areas || areas.length === 0) return null;

  const withWindow = areas.filter((area) => area.best_window_hours > 0);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-2">
        <h2 className="font-semibold text-slate-900">Fire weather zones</h2>
        <p className="text-xs text-slate-500">
          {withWindow.length} of {areas.length} have a workable window in the
          next 5 days
        </p>
      </div>

      <ul
        ref={listRef}
        className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto"
      >
        {areas.map((area) => {
          const selected = area.name === selectedName;
          return (
            <li key={area.zone_id || area.name}>
              <button
                type="button"
                data-selected={selected}
                onClick={() =>
                  onSelect(area.location.lat, area.location.lon, area.name, true)
                }
                className={`flex w-full min-w-0 items-center justify-between gap-2 rounded border p-2 text-left text-sm hover:bg-slate-50 ${
                  selected
                    ? "border-slate-400 bg-slate-50 ring-1 ring-slate-300"
                    : "border-slate-200 bg-white"
                }`}
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium text-slate-800">
                    {area.name}
                  </span>
                  <span className="block text-xs text-slate-400">
                    {area.zone_id}
                  </span>
                </span>
                {area.error ? (
                  <span className="shrink-0 text-xs text-slate-400">
                    no forecast
                  </span>
                ) : (
                  <>
                    <span className="shrink-0 text-xs font-medium text-slate-600">
                      {area.best_window_hours > 0
                        ? `${area.best_window_hours}h`
                        : "--"}
                    </span>
                    <span className="shrink-0">
                      <StatusBadge status={area.best_status} />
                    </span>
                  </>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
