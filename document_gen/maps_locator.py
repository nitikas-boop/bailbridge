"""
BailBridge — e-Seva / Legal Aid Centre Locator  (Developer 4 · Phase 1)

Provides find_nearest_eseva(lat, lng) which queries the Google Maps Places API
for the closest Common Service Centres (CSCs / e-Seva kendras), District Legal
Services Authorities (DLSAs), courts, and police stations in India.

These locations are the primary physical touch-points for defendants who need
to file NALSA bail applications or access government e-services.
"""

import os
import math
import urllib.parse
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────

_NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
_TEXT_SEARCH_URL   = "https://maps.googleapis.com/maps/api/place/textsearch/json"

# Place types (Google Maps) used for primary nearby search
_PRIMARY_PLACE_TYPES: list[tuple[str, str]] = [
    ("courthouse",   "District Court / DLSA"),
    ("police",       "Police Station"),
    ("local_government_office", "Government Office / e-Seva"),
]

# Keyword-based text searches to supplement nearby results
_KEYWORD_SEARCHES: list[tuple[str, str]] = [
    ("CSC common service centre",           "Common Service Centre (CSC)"),
    ("e-Seva kendra",                        "e-Seva Kendra"),
    ("District Legal Services Authority",    "DLSA Legal Aid Centre"),
    ("lok adalat",                           "Lok Adalat"),
    ("NALSA legal aid",                      "NALSA Legal Aid Clinic"),
]

_SEARCH_RADIUS_METERS = 15_000   # 15 km for rural/semi-urban coverage
_MAX_RESULTS          = 5        # Return up to 5 nearest locations


# ── Internal helpers ───────────────────────────────────────────────────────────

def _get_api_key() -> str:
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        raise EnvironmentError(
            "GOOGLE_MAPS_API_KEY is not set. Add it to your .env file."
        )
    return key


def _maps_url(lat: float, lng: float, name: Optional[str] = None) -> str:
    """Build a Google Maps deep-link for a coordinate / place."""
    query = f"{name},{lat},{lng}" if name else f"{lat},{lng}"
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(query)}"


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Straight-line distance in kilometres between two lat/lng points."""
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


def _nearby_search(
    lat: float, lng: float, place_type: str, api_key: str
) -> list[dict]:
    """Run a single Places Nearby Search and return raw result list."""
    params = {
        "location": f"{lat},{lng}",
        "radius":   _SEARCH_RADIUS_METERS,
        "type":     place_type,
        "key":      api_key,
    }
    resp = requests.get(_NEARBY_SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(
            f"Maps API error [{place_type}]: {status} — "
            f"{data.get('error_message', 'no detail')}"
        )
    return data.get("results", [])


def _text_search(
    lat: float, lng: float, keyword: str, api_key: str
) -> list[dict]:
    """Run a Places Text Search biased to the given location."""
    params = {
        "query":    keyword,
        "location": f"{lat},{lng}",
        "radius":   _SEARCH_RADIUS_METERS,
        "key":      api_key,
    }
    resp = requests.get(_TEXT_SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(
            f"Maps Text Search error [{keyword!r}]: {status} — "
            f"{data.get('error_message', 'no detail')}"
        )
    return data.get("results", [])


def _parse_place(
    place: dict, category: str, ref_lat: float, ref_lng: float
) -> dict:
    """Extract a normalised location dict from a raw Places API result."""
    loc = place.get("geometry", {}).get("location", {})
    p_lat = loc.get("lat", ref_lat)
    p_lng = loc.get("lng", ref_lng)
    return {
        "name":         place.get("name", "Unknown"),
        "address":      place.get("vicinity") or place.get("formatted_address", "Address not available"),
        "category":     category,
        "distance_km":  round(_haversine_km(ref_lat, ref_lng, p_lat, p_lng), 2),
        "maps_url":     _maps_url(p_lat, p_lng, place.get("name")),
        "place_id":     place.get("place_id", ""),
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def find_nearest_eseva(lat: float, lng: float) -> list[dict]:
    """
    Find the nearest e-Seva kendras, CSCs, and legal aid centres to the given
    GPS coordinates using the Google Maps Places API.

    This is the Developer 4 entry-point for physical location discovery —
    complementing NALSA form generation by pointing defendants to the nearest
    place where they can submit the form or access government e-services.

    Search strategy:
      1. Nearby Search for courthouses, police stations, and government offices.
      2. Keyword Text Searches for CSC / e-Seva / DLSA / Lok Adalat / NALSA.
      3. Deduplicate by place_id.
      4. Sort by straight-line distance; return top 5.

    Args:
        lat: Latitude of the defendant's / agent's current location.
        lng: Longitude of the defendant's / agent's current location.

    Returns:
        A list of up to 5 location dicts, sorted nearest-first:
        [
            {
                "name":         "District Court Complex",
                "address":      "Court Road, Patna, Bihar",
                "category":     "District Court / DLSA",
                "distance_km":  1.3,
                "maps_url":     "https://www.google.com/maps/search/?...",
                "place_id":     "ChIJ...",
            },
            ...
        ]

    Raises:
        EnvironmentError:   GOOGLE_MAPS_API_KEY is missing.
        requests.HTTPError: Network / HTTP error from Maps API.
        RuntimeError:       Non-OK status returned by Maps API.
    """
    api_key = _get_api_key()
    seen_ids: set[str] = set()
    candidates: list[dict] = []

    # ── Step 1: Nearby Search (typed place categories) ────────────────────────
    for place_type, category_label in _PRIMARY_PLACE_TYPES:
        try:
            results = _nearby_search(lat, lng, place_type, api_key)
        except Exception as exc:
            print(f"[MapsLocator] ⚠️  Nearby search '{place_type}' failed: {exc}")
            continue

        for place in results:
            pid = place.get("place_id", "")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            candidates.append(_parse_place(place, category_label, lat, lng))

    # ── Step 2: Text Search (keyword-based for e-Seva / CSC / DLSA) ──────────
    for keyword, category_label in _KEYWORD_SEARCHES:
        try:
            results = _text_search(lat, lng, keyword, api_key)
        except Exception as exc:
            print(f"[MapsLocator] ⚠️  Text search {keyword!r} failed: {exc}")
            continue

        for place in results:
            pid = place.get("place_id", "")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            candidates.append(_parse_place(place, category_label, lat, lng))

    # ── Step 3: Sort & cap ────────────────────────────────────────────────────
    candidates.sort(key=lambda x: x["distance_km"])
    top = candidates[:_MAX_RESULTS]

    if not top:
        print(
            f"[MapsLocator] ⚠️  No e-Seva / legal aid centres found "
            f"within 15 km of ({lat}, {lng})."
        )
    else:
        for loc in top:
            print(
                f"[MapsLocator] 📍 {loc['category']}: {loc['name']} "
                f"— {loc['distance_km']} km"
            )

    return top
