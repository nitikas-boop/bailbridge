"""
BailBridge — Google Maps Places Client

Provides find_nearest_help(lat, lng) which queries the Google Maps Places
API (Nearby Search) for the closest police stations, courthouses, and legal
service offices within 10 km of a given coordinate.
"""

import os
import urllib.parse
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

# Google Maps Places API endpoint
_NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

# Place types to query (run as separate searches and merge results)
_PLACE_TYPES = ["police", "courthouse", "lawyer"]

# Human-readable labels aligned with the types above
_TYPE_LABELS = {
    "police": "Police Station",
    "courthouse": "Courthouse",
    "lawyer": "Legal Services",
}

_SEARCH_RADIUS_METERS = 10_000   # 10 km
_MAX_RESULTS = 3


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_api_key() -> str:
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        raise EnvironmentError(
            "GOOGLE_MAPS_API_KEY is not set. Add it to your .env file."
        )
    return key


def _maps_url(lat: float, lng: float, name: Optional[str] = None) -> str:
    """
    Build a Google Maps deep-link URL for a coordinate.
    If a place name is provided it is included in the query for better UX.
    """
    query = f"{name},{lat},{lng}" if name else f"{lat},{lng}"
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.google.com/maps/search/?api=1&query={encoded}"


def _nearby_search(lat: float, lng: float, place_type: str, api_key: str) -> list[dict]:
    """
    Call the Places API Nearby Search for a single place type.
    Returns a list of raw result dicts from the API.
    """
    params = {
        "location": f"{lat},{lng}",
        "radius": _SEARCH_RADIUS_METERS,
        "type": place_type,
        "key": api_key,
    }
    response = requests.get(_NEARBY_SEARCH_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(
            f"Google Maps API error for type '{place_type}': "
            f"{status} — {data.get('error_message', 'No details provided.')}"
        )

    return data.get("results", [])


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate straight-line distance in km between two coordinates."""
    import math
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def find_nearest_help(lat: float, lng: float) -> list[dict]:
    """
    Find the 3 nearest legal help locations within 10 km of the given
    coordinates using the Google Maps Places Nearby Search API.

    Searches across three categories simultaneously:
      • Police stations
      • Courthouses
      • Legal services / lawyers

    Args:
        lat: Latitude of the user's location.
        lng: Longitude of the user's location.

    Returns:
        A list of up to 3 dicts, sorted by distance (nearest first):
        [
            {
                "name":     "Central Police Station",
                "address":  "123 Main St, Springfield",
                "category": "Police Station",
                "distance_km": 1.4,
                "maps_url": "https://www.google.com/maps/search/?api=1&query=...",
            },
            ...
        ]

    Raises:
        EnvironmentError:   If GOOGLE_MAPS_API_KEY is missing.
        requests.HTTPError: On network/HTTP errors.
        RuntimeError:       On Places API error statuses.
    """
    api_key = _get_api_key()
    seen_place_ids: set[str] = set()
    candidates: list[dict] = []

    # Gather results from all three category searches
    for place_type in _PLACE_TYPES:
        try:
            results = _nearby_search(lat, lng, place_type, api_key)
        except Exception as exc:
            print(f"[MapsClient] ⚠️  Skipping '{place_type}': {exc}")
            continue

        for place in results:
            place_id = place.get("place_id")
            if not place_id or place_id in seen_place_ids:
                continue
            seen_place_ids.add(place_id)

            place_lat = place["geometry"]["location"]["lat"]
            place_lng = place["geometry"]["location"]["lng"]
            distance_km = _haversine_km(lat, lng, place_lat, place_lng)

            candidates.append(
                {
                    "name": place.get("name", "Unknown"),
                    "address": place.get("vicinity", "Address not available"),
                    "category": _TYPE_LABELS.get(place_type, place_type.title()),
                    "distance_km": round(distance_km, 2),
                    "maps_url": _maps_url(place_lat, place_lng, place.get("name")),
                }
            )

    # Sort by proximity and return top 3
    candidates.sort(key=lambda x: x["distance_km"])
    top = candidates[:_MAX_RESULTS]

    if not top:
        print(f"[MapsClient] ⚠️  No legal help locations found within 10 km of ({lat}, {lng}).")
    else:
        for loc in top:
            print(
                f"[MapsClient] 📍 {loc['category']}: {loc['name']} "
                f"— {loc['distance_km']} km"
            )

    return top
