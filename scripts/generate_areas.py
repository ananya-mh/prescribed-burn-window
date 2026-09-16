"""Regenerate backend/core/areas.py from the NWS fire weather zone list.

Run from the backend directory:  .venv/bin/python ../scripts/generate_areas.py

Fire weather zones are the units fire agencies actually forecast against, and
they come from the same API that serves our weather, so the area list and the
forecast agree by construction.

Every coordinate this writes is verified: we derive a candidate point from the
zone's own polygon and then ask /points which zone that coordinate falls in,
keeping it only if the answer matches. Centroids land outside their zone about
a fifth of the time -- concave shapes put the centroid in a neighbour, and
coastal zones put it in the ocean -- so unverified centroids would be wrong.
"""

import re
import sys
import time

import httpx

USER_AGENT = "(prescribed-burn-window, hegde.ana@northeastern.edu)"
BASE = "https://api.weather.gov"
HEADERS = {"User-Agent": USER_AGENT}
TARGET_COUNT = 30

# Prescribed burns happen in forest and shrubland, so keep the zones that are
# actually wildland and drop cities, desert and islands. Matching on the zone
# name is crude but the NWS names are descriptive enough to make it work, and
# the result is reviewable in the generated file.
WILDLAND = re.compile(
    r"national forest|mountains|sierra|foothills|motherlode|range|above 3000"
    r"|cascade|trinity|shasta|santa cruz|diablo|mendocino|lassen|modoc"
    r"|klamath|los padres|santa lucia|santa ynez|siskiyou|humboldt", re.I)

UNSUITABLE = re.compile(
    r"desert|death valley|joshua tree|colorado river|imperial|island|metro"
    r"|san francisco|urban|beaches|coastal|owens|inland empire"
    r"|orange county inland", re.I)

session = httpx.Client(headers=HEADERS, timeout=90)


def get(url, **params):
    """GET with a short pause, so the generator stays polite to NWS."""
    time.sleep(0.3)
    return session.get(url, params=params or None)


def list_zones():
    features = get(BASE + "/zones", type="fire", area="CA").json()["features"]
    zones = [
        (f["properties"]["id"], f["properties"]["name"],
         (f["properties"].get("cwa") or ["?"])[0])
        for f in features
    ]
    return [z for z in zones
            if WILDLAND.search(z[1]) and not UNSUITABLE.search(z[1])]


def pick_spread(zones):
    """Spread the picks across the state.

    Zones are grouped by forecast office and quotas handed out round-robin, so
    every region is represented. Within an office we take evenly spaced zones
    rather than the first few, because zone ids run geographically and taking
    the first few would pile them all into one county.
    """
    by_office = {}
    for zone in zones:
        by_office.setdefault(zone[2], []).append(zone)

    offices = sorted(by_office, key=lambda o: -len(by_office[o]))
    quota = dict((office, 0) for office in offices)
    while sum(quota.values()) < min(TARGET_COUNT, len(zones)):
        for office in offices:
            if quota[office] < len(by_office[office]):
                quota[office] += 1
                if sum(quota.values()) == min(TARGET_COUNT, len(zones)):
                    break

    picked = []
    for office in offices:
        bucket = by_office[office]
        take = quota[office]
        if take == 0:
            continue
        step = len(bucket) / float(take)
        for i in range(take):
            picked.append(bucket[int(i * step)])
    return sorted(picked, key=lambda z: z[0])


def largest_ring(geometry):
    polygons = (geometry["coordinates"] if geometry["type"] == "MultiPolygon"
                else [geometry["coordinates"]])
    best, best_area = None, -1.0
    for polygon in polygons:
        ring = polygon[0]
        area = abs(sum(ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
                       for i in range(len(ring) - 1)) / 2.0)
        if area > best_area:
            best_area, best = area, ring
    return best


def candidate_points(ring):
    """Points to try, best guess first: the centroid, then points pulled in
    from the edge, then a coarse grid over the bounding box."""
    lats = [p[1] for p in ring]
    lons = [p[0] for p in ring]
    centre = (sum(lats) / len(lats), sum(lons) / len(lons))
    yield centre

    step = max(1, len(ring) // 8)
    for vertex in ring[::step]:
        # Halfway from the edge toward the middle, so we stay inside.
        yield ((centre[0] + vertex[1]) / 2, (centre[1] + vertex[0]) / 2)

    for i in range(1, 4):
        for j in range(1, 4):
            yield (min(lats) + (max(lats) - min(lats)) * i / 4,
                   min(lons) + (max(lons) - min(lons)) * j / 4)


def verified_point(zone_id):
    """A coordinate inside zone_id, confirmed by /points, or None."""
    detail = get("%s/zones/fire/%s" % (BASE, zone_id)).json()
    if not detail.get("geometry"):
        return None
    ring = largest_ring(detail["geometry"])

    for attempt, (lat, lon) in enumerate(candidate_points(ring)):
        if attempt >= 12:
            break
        response = get("%s/points/%.4f,%.4f" % (BASE, lat, lon))
        if response.status_code != 200:
            continue
        properties = response.json()["properties"]
        if properties.get("fireWeatherZone", "").rsplit("/", 1)[-1] == zone_id:
            return round(lat, 4), round(lon, 4), properties["relativeLocation"]["properties"]["city"]
    return None


def main():
    zones = list_zones()
    print("%d non-urban California fire weather zones" % len(zones), file=sys.stderr)

    rows = []
    for zone_id, name, office in pick_spread(zones):
        found = verified_point(zone_id)
        if found is None:
            print("  skip %s (no point verified inside it)" % zone_id, file=sys.stderr)
            continue
        lat, lon, city = found
        rows.append((zone_id, name, lat, lon, city))
        print("  %-8s %-46s %.4f,%.4f near %s" % (zone_id, name[:46], lat, lon, city),
              file=sys.stderr)

    out = ['"""California fire weather zones used for the ranked burn-area list.',
           "",
           "GENERATED FILE -- do not edit by hand. Regenerate with:",
           "    .venv/bin/python ../scripts/generate_areas.py",
           "",
           "These are National Weather Service fire weather zones: the units fire agencies",
           "forecast against, from the same API that serves our weather. Each coordinate was",
           "verified by asking /points which zone it falls in and keeping only matches, so",
           "every point below is known to lie inside the zone it is labelled with.",
           '"""',
           "",
           "from typing import List, NamedTuple",
           "",
           "",
           "class Area(NamedTuple):",
           "    zone_id: str",
           "    name: str",
           "    lat: float",
           "    lon: float",
           "",
           "",
           "AREAS: List[Area] = ["]
    for zone_id, name, lat, lon, city in rows:
        out.append('    Area("%s", "%s", %.4f, %.4f),  # near %s'
                   % (zone_id, name.replace('"', "'"), lat, lon, city))
    out.append("]")
    print("\n".join(out))


if __name__ == "__main__":
    main()
