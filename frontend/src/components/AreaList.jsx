import StatusBadge from "./StatusBadge";

// NWS fire weather zones, already ranked best-first by the backend. Clicking
// one selects its coordinates, so the detail panel below shows its forecast.
export default function AreaList({ areas, loading, error, onSelect, selectedName }) {
  if (loading) return <p className="text-sm text-slate-600">Loading areas...</p>;

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

      <ul className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {areas.map((area) => (
          <li key={area.name}>
            <button
              type="button"
              onClick={() => onSelect(area.location.lat, area.location.lon, area.name)}
              className={`flex w-full min-w-0 items-center justify-between gap-2 rounded border p-2 text-left text-sm hover:bg-slate-50 ${
                area.name === selectedName
                  ? "border-slate-400 bg-slate-50"
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
                <span className="shrink-0 text-xs text-slate-400">no forecast</span>
              ) : (
                <>
                  <span className="shrink-0 text-xs text-slate-500">
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
        ))}
      </ul>
    </div>
  );
}
