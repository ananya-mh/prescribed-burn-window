"""California fire weather zones used for the ranked burn-area list.

GENERATED FILE -- do not edit by hand. Regenerate with:
    .venv/bin/python ../scripts/generate_areas.py

These are National Weather Service fire weather zones: the units fire agencies
forecast against, from the same API that serves our weather. Each coordinate was
verified by asking /points which zone it falls in and keeping only matches, so
every point below is known to lie inside the zone it is labelled with.
"""

from typing import List, NamedTuple


class Area(NamedTuple):
    zone_id: str
    name: str
    lat: float
    lon: float


AREAS: List[Area] = [
    Area("CAZ121", "Western Shasta County Mountains Above 3000 ft", 40.7916, -122.5641),  # near French Gulch
    Area("CAZ126", "Eastern Shasta County Mountains and Southern Cascades Above 3000 ft", 40.7293, -121.8033),  # near Whitmore
    Area("CAZ131", "Northern Motherlode Between 1000-3000 ft", 39.2292, -120.9644),  # near Grass Valley
    Area("CAZ136", "Sierra Nevada of El Dorado-Amador-Northern Alpine Counties Above 5000 ft Including Highway 50", 38.7060, -120.3297),  # near Grizzly Flats
    Area("CAZ140", "Tehama County Coast Range Above 3000 ft", 40.0734, -122.8023),  # near Rancho Tehama Reserve
    Area("CAZ255", "San Bernardino County Mountains-Including The Mountain Top And Front Country Ranger Districts Of The San Bernardino National Forest", 34.1895, -117.0830),  # near Running Springs
    Area("CAZ256", "Riverside County Mountains-Including The San Jacinto Ranger District Of The San Bernardino National Forest", 33.6751, -116.6557),  # near Mountain Center
    Area("CAZ257", "Santa Ana Mountains-Including The Trabuco Ranger District of the Cleveland National Forest", 33.6289, -117.4832),  # near Lakeland Village
    Area("CAZ258", "San Diego County Mountains-Including The Palomar And Descanso Ranger Districts of the Cleveland National Forest", 33.0761, -116.5468),  # near Julian
    Area("CAZ271", "Western Lassen, Eastern Plumas, and Eastern Sierra Counties", 40.1169, -120.6436),  # near Taylorsville
    Area("CAZ278", "Eastern Lassen County", 40.7160, -120.3518),  # near Stones Landing
    Area("CAZ280", "Western Klamath National Forest", 41.7364, -123.0757),  # near Fort Jones
    Area("CAZ281", "Central Siskiyou County Including Shasta Valley", 41.6856, -122.5639),  # near Montague
    Area("CAZ282", "Shasta-Trinity National Forest in Siskiyou County", 41.2894, -122.3619),  # near Mount Shasta
    Area("CAZ284", "Siskiyou County from the Cascade Mountains East and South to Mt Shasta", 41.5901, -121.8540),  # near Tennant
    Area("CAZ342", "Santa Lucia Mountains", 35.4830, -120.7859),  # near Atascadero
    Area("CAZ351", "Santa Ynez Mountains Western Range", 34.5163, -119.9605),  # near Goleta
    Area("CAZ370", "Eastern Santa Monica Mountains Recreational Area", 34.0859, -118.5427),  # near Los Angeles
    Area("CAZ379", "Western San Gabriel Mountains and Highway 14 Corridor", 34.4499, -118.2150),  # near Acton
    Area("CAZ403", "Northeastern Interior Humboldt and Southwestern Siskiyou Including Orleans", 41.4321, -123.4935),  # near Kep'el
    Area("CAZ407", "Southwestern Humboldt Including the King Range and the Eel River Valley", 40.2950, -124.1165),  # near Weott
    Area("CAZ410", "Northeastern Trinity Including Trinity Lake", 41.0249, -122.7628),  # near Trinity Center
    Area("CAZ414", "Northern Interior Mendocino Including Leggett and Willits", 39.6290, -123.4724),  # near Laytonville
    Area("CAZ504", "North Bay Interior Mountains", 38.6355, -122.4513),  # near Angwin
    Area("CAZ512", "Santa Cruz Mountains", 37.1456, -121.9910),  # near Lexington Hills
    Area("CAZ517", "Santa Lucia Mountains and Los Padres National Forest", 36.1633, -121.4415),  # near Greenfield
    Area("CAZ518", "Mountains Of San Benito County And Interior Monterey County Including Pinnacles National Park", 36.2474, -120.7080),  # near San Ardo
    Area("CAZ590", "Central Sierra Foothills", 37.5710, -120.1017),  # near Bear Valley
    Area("CAZ591", "Southern Sierra Foothills", 36.0964, -118.8865),  # near Springville
    Area("CAZ592", "Central Sierra", 37.9486, -119.4065),  # near Virginia Lakes
]
