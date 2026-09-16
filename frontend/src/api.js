import mockResponse from "./mocks/burnWindow.json";
import mockAreas from "./mocks/burnAreas.json";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

// Fetches the 5-day burn window assessment for a point.
// With VITE_USE_MOCK=true we return canned data so the UI can be built
// before the backend exists.
export async function fetchBurnWindow(lat, lon) {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 600));
    return mockResponse;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/burn-window?lat=${lat}&lon=${lon}`
  );

  if (!response.ok) {
    // The backend sends errors as { "detail": "..." }.
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Request failed (${response.status})`);
  }

  return response.json();
}

// Every named burn area, already ranked best-first by the backend. The scan is
// cached server-side for an hour, so this is cheap to call on page load.
export async function fetchBurnAreas() {
  if (USE_MOCK) {
    await new Promise((resolve) => setTimeout(resolve, 600));
    return mockAreas;
  }

  const response = await fetch(`${API_BASE_URL}/api/burn-areas`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Request failed (${response.status})`);
  }

  return response.json();
}
