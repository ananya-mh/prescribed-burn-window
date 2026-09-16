import { useEffect, useState } from "react";
import { fetchBurnAreas, fetchBurnWindow } from "./api";
import Map from "./components/Map";
import AreaList from "./components/AreaList";
import DayCardList from "./components/DayCardList";

export default function App() {
  const [location, setLocation] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [areas, setAreas] = useState(null);
  const [areasLoading, setAreasLoading] = useState(true);
  const [areasError, setAreasError] = useState(null);
  const [selectedName, setSelectedName] = useState(null);
  // Set only when the pick came from the list, so the map flies to it. The id
  // changes every time so picking the same zone twice still moves the map.
  const [focus, setFocus] = useState(null);

  // The ranked area list is the same for everyone and is cached server-side,
  // so fetch it once when the page loads.
  useEffect(() => {
    fetchBurnAreas()
      .then((data) => setAreas(data.areas))
      .catch((err) => setAreasError(err.message))
      .finally(() => setAreasLoading(false));
  }, []);

  async function handleSelect(lat, lon, name = null, focusMap = false) {
    setSelectedName(name);
    if (focusMap) {
      setFocus((previous) => ({ lat, lon, id: (previous?.id || 0) + 1 }));
    }
    setLocation({ lat, lon });
    setResult(null);
    setError(null);
    setLoading(true);

    try {
      const data = await fetchBurnWindow(lat.toFixed(4), lon.toFixed(4));
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-4 py-4">
        <h1 className="text-xl font-bold">Prescribed Burn Window Finder</h1>
        <p className="text-sm text-slate-600">
          Pick a ranked area, or click anywhere in California, to check the
          next 5 days of burn conditions.
        </p>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-4 p-4">
        <div className="flex flex-col gap-4 lg:flex-row">
          <div className="h-[400px] min-w-0 overflow-hidden rounded-lg border border-slate-200 shadow-sm lg:h-[500px] lg:flex-1">
            <Map
              location={location}
              onSelect={handleSelect}
              areas={areas || []}
              focus={focus}
            />
          </div>

          <div className="min-w-0 rounded-lg border border-slate-200 bg-white p-3 shadow-sm lg:h-[500px] lg:w-80 lg:shrink-0">
            <AreaList
              areas={areas}
              loading={areasLoading}
              error={areasError}
              onSelect={handleSelect}
              selectedName={selectedName}
            />
          </div>
        </div>

        <section>
          {!location && (
            <p className="text-sm text-slate-600">
              No location selected yet.
            </p>
          )}

          {location && (
            <p className="mb-3 text-sm text-slate-600">
              Selected: {selectedName ? `${selectedName} - ` : ""}
              {location.lat.toFixed(4)}, {location.lon.toFixed(4)}
            </p>
          )}

          {loading && <p className="text-sm text-slate-600">Loading...</p>}

          {error && (
            <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
              Could not load burn conditions: {error}
            </p>
          )}

          {result && <DayCardList days={result.days} />}
        </section>
      </main>
    </div>
  );
}
