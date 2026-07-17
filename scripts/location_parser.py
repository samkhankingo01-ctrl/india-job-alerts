"""India location parser – splits a raw location string into State / City / Area.

The core requirement of this project is to PRESERVE the exact location from the
original job posting. We never replace a location with just "India".

Given any of these inputs:
    "Mumbai, Maharashtra"
    "Dadar, Mumbai, Maharashtra"
    "Vashi, Navi Mumbai"
    "Whitefield, Bangalore, Karnataka, India"
    "Bengaluru"            (state inferred from a known city list)
    "Remote"               (kept as-is, no state/area)

The parser returns a dict with the three granular fields plus the original raw
string so nothing is ever lost.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ── Canonical Indian states & UTs ────────────────────────────────────────────
STATES: dict[str, str] = {
    # canonical -> normalized display name
    "andhra pradesh": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "odisha (orissa)": "Odisha",
    "orissa": "Odisha",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "uttaranchal": "Uttarakhand",
    "west bengal": "West Bengal",
    # Union Territories
    "andaman and nicobar islands": "Andaman and Nicobar Islands",
    "chandigarh": "Chandigarh",
    "dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "jammu and kashmir": "Jammu and Kashmir",
    "jammu & kashmir": "Jammu and Kashmir",
    "ladakh": "Ladakh",
    "lakshadweep": "Lakshadweep",
    "puducherry": "Puducherry",
    "pondicherry": "Puducherry",
}

# ── Major cities → their state/UT (for state inference) ─────────────────────
# Multiple spellings / variants included. Keyed on the normalized lowercase name.
CITY_TO_STATE: dict[str, str] = {
    # Maharashtra
    "mumbai": "Maharashtra",
    "bombay": "Maharashtra",
    "navi mumbai": "Maharashtra",
    "thane": "Maharashtra",
    "pune": "Maharashtra",
    "nagpur": "Maharashtra",
    "nashik": "Maharashtra",
    "nasik": "Maharashtra",
    "aurangabad": "Maharashtra",
    "nashik road": "Maharashtra",
    # Delhi
    "new delhi": "Delhi",
    "delhi": "Delhi",
    "nct of delhi": "Delhi",
    # Karnataka
    "bengaluru": "Karnataka",
    "bangalore": "Karnataka",
    "mysuru": "Karnataka",
    "mysore": "Karnataka",
    "mangaluru": "Karnataka",
    "mangalore": "Karnataka",
    "hubli": "Karnataka",
    "hubballi": "Karnataka",
    "belgaum": "Karnataka",
    "belagavi": "Karnataka",
    # Tamil Nadu
    "chennai": "Tamil Nadu",
    "madras": "Tamil Nadu",
    "coimbatore": "Tamil Nadu",
    "madurai": "Tamil Nadu",
    "tiruchirappalli": "Tamil Nadu",
    "trichy": "Tamil Nadu",
    "salem": "Tamil Nadu",
    # Telangana / Andhra
    "hyderabad": "Telangana",
    "secunderabad": "Telangana",
    "warangal": "Telangana",
    "visakhapatnam": "Andhra Pradesh",
    "vishakhapatnam": "Andhra Pradesh",
    "vizag": "Andhra Pradesh",
    "vijayawada": "Andhra Pradesh",
    "guntur": "Andhra Pradesh",
    # West Bengal
    "kolkata": "West Bengal",
    "calcutta": "West Bengal",
    "howrah": "West Bengal",
    "durgapur": "West Bengal",
    # Gujarat
    "ahmedabad": "Gujarat",
    "amdavad": "Gujarat",
    "gandhinagar": "Gujarat",
    "surat": "Gujarat",
    "vadodara": "Gujarat",
    "baroda": "Gujarat",
    "rajkot": "Gujarat",
    # Rajasthan
    "jaipur": "Rajasthan",
    "jodhpur": "Rajasthan",
    "udaipur": "Rajasthan",
    "kota": "Rajasthan",
    "ajmer": "Rajasthan",
    # Uttar Pradesh
    "lucknow": "Uttar Pradesh",
    "kanpur": "Uttar Pradesh",
    "ghaziabad": "Uttar Pradesh",
    "noida": "Uttar Pradesh",
    "greater noida": "Uttar Pradesh",
    "varanasi": "Uttar Pradesh",
    "benaras": "Uttar Pradesh",
    "agra": "Uttar Pradesh",
    "meerut": "Uttar Pradesh",
    "prayagraj": "Uttar Pradesh",
    "allahabad": "Uttar Pradesh",
    "aligarh": "Uttar Pradesh",
    "bareilly": "Uttar Pradesh",
    "moradabad": "Uttar Pradesh",
    # Haryana
    "gurugram": "Haryana",
    "gurgaon": "Haryana",
    "faridabad": "Haryana",
    "panipat": "Haryana",
    "ambala": "Haryana",
    "karnal": "Haryana",
    "sonipat": "Haryana",
    # Punjab
    "ludhiana": "Punjab",
    "amritsar": "Punjab",
    "jalandhar": "Punjab",
    "mohali": "Punjab",
    "zirakpur": "Punjab",
    "chandigarh": "Chandigarh",
    # Madhya Pradesh
    "bhopal": "Madhya Pradesh",
    "indore": "Madhya Pradesh",
    "jabalpur": "Madhya Pradesh",
    "gwalior": "Madhya Pradesh",
    # Bihar
    "patna": "Bihar",
    "gaya": "Bihar",
    "bhagalpur": "Bihar",
    "muzaffarpur": "Bihar",
    # Odisha
    "bhubaneswar": "Odisha",
    "bhubaneshwar": "Odisha",
    "cuttack": "Odisha",
    # Kerala
    "thiruvananthapuram": "Kerala",
    "trivandrum": "Kerala",
    "kochi": "Kerala",
    "cochin": "Kerala",
    "kozhikode": "Kerala",
    "calicut": "Kerala",
    "thrissur": "Kerala",
    # Jharkhand
    "ranchi": "Jharkhand",
    "jamshedpur": "Jharkhand",
    "dhanbad": "Jharkhand",
    "bokaro": "Jharkhand",
    "bokaro steel city": "Jharkhand",
    # Uttarakhand
    "dehradun": "Uttarakhand",
    "dehra dun": "Uttarakhand",
    "haridwar": "Uttarakhand",
    "roorkee": "Uttarakhand",
    "nainital": "Uttarakhand",
    # Chhattisgarh
    "raipur": "Chhattisgarh",
    "bhilai": "Chhattisgarh",
    "bilaspur": "Chhattisgarh",
    # Assam
    "guwahati": "Assam",
    "dispur": "Assam",
    # Jammu & Kashmir / Ladakh
    "srinagar": "Jammu and Kashmir",
    "jammu": "Jammu and Kashmir",
    "leh": "Ladakh",
    # Puducherry
    "puducherry": "Puducherry",
    "pondicherry": "Puducherry",
}

# Set of all known city names (lowercased) – used to identify the "city" token
# when it is NOT the first token in a comma list.
_KNOWN_CITIES: set[str] = set(CITY_TO_STATE.keys())

# Tokens that are NOT a real area/locality and should be ignored when splitting.
_NON_AREA_TOKENS: set[str] = {
    "india", "remote", "work from home", "wfh", "hybrid", "onsite",
    "anywhere", "worldwide", "global", "not specified", "n/a", "na",
    "telecommute", "virtual", "distributed", "multiple locations",
}

_SPLIT_RE = re.compile(r"[,;|/]|(?: - )|(?:–)")


def _clean(token: str) -> str:
    """Trim and collapse internal whitespace in a token."""
    return re.sub(r"\s+", " ", token).strip(" .-–")


def _normalize(token: str) -> str:
    return _clean(token).lower()


def _lookup_state(token: str) -> str:
    """Return the canonical state name if *token* is a state/UT, else ''."""
    norm = _normalize(token)
    return STATES.get(norm, "")


def _lookup_city_state(token: str) -> str:
    """Return the state for a known city token, else ''."""
    return CITY_TO_STATE.get(_normalize(token), "")


def is_india_location(text: str) -> bool:
    """Return True if *text* appears to be an Indian location.

    Detects either an explicit 'India' token, a known Indian state, or a known
    Indian city. Used to hard-filter out foreign jobs (e.g. Berlin, Cologne).
    """
    if not text:
        return False
    norm = _normalize(text)
    if "india" in norm or "bharat" in norm:
        return True
    if _lookup_state(text):
        return True
    # check any comma-split token for a known city
    for tok in _SPLIT_RE.split(text):
        if _lookup_city_state(tok):
            return True
    return False


def parse_location(raw: str) -> dict[str, str]:
    """Parse a raw location string into structured Indian location fields.

    Preserves the original string in the ``location_raw`` field so nothing is
    ever lost. We never replace a real location with just "India".

    Args:
        raw: Raw location string from the job posting (e.g.
            "Dadar, Mumbai, Maharashtra").

    Returns:
        A dict with keys: ``state``, ``city``, ``area``, ``location_raw``.
        Fields that cannot be determined are empty strings.
    """
    original = (raw or "").strip()
    result: dict[str, str] = {
        "state": "",
        "city": "",
        "area": "",
        "location_raw": original,
    }

    if not original:
        return result

    # Tokenize on common delimiters: comma, semicolon, slash, pipe, dash
    tokens: list[str] = [_clean(t) for t in _SPLIT_RE.split(original)]
    # Drop empty / junk tokens
    tokens = [t for t in tokens if t and _normalize(t) not in _NON_AREA_TOKENS]

    if not tokens:
        # e.g. raw was just "Remote" – keep raw, leave granular fields empty
        return result

    # Pass 1 – pick the city and state tokens. We check CITY before STATE
    # because some names are both (e.g. "New Delhi" is a city AND maps to the
    # Delhi UT); the city reading is more specific in an "Area, City" context.
    state = ""
    city = ""
    area_candidates: list[str] = []

    for tok in tokens:
        if _lookup_city_state(tok) and not city:
            city = tok
            continue
        s = _lookup_state(tok)
        if s and not state:
            state = s
            continue
        area_candidates.append(tok)

    # Pass 2 – infer state from city if state still missing
    if not state and city:
        state = _lookup_city_state(city)

    # If only one token and it's a state, treat it as both city+state ambiguous:
    # keep state, leave city empty (we don't fabricate a city).
    if not city and not state and len(tokens) == 1:
        # Could be an unknown city/state – keep as city so it isn't lost.
        city = tokens[0]

    # If we have exactly one token that is a known city, state was inferred
    # above; area stays empty.

    # Assign area: leftover candidates that are NOT the chosen city/state.
    chosen = {_normalize(city), _normalize(state)}
    areas = [a for a in area_candidates if _normalize(a) not in chosen]
    area = ", ".join(dict.fromkeys(areas))  # preserve order, dedupe

    # Edge case: a single token like "Bangalore" → city + inferred state,
    # no area.
    # Edge case: "Whitefield, Bangalore" → area=Whitefield, city=Bangalore,
    # state inferred = Karnataka.
    if not city and area_candidates and state:
        # state was explicit, the rest are area/city but none matched a known
        # city – treat the FIRST as city to avoid losing it.
        city = area_candidates[0]
        areas = [a for a in area_candidates[1:] if _normalize(a) not in chosen]
        area = ", ".join(dict.fromkeys(areas))

    result["state"] = state
    result["city"] = city
    result["area"] = area
    return result


def enrich_job_location(job: Any) -> dict[str, str]:
    """Convenience: parse a Job's combined location into fields.

    Uses the Job's city/state/area fields as a starting point and tries to
    re-split a messy ``city`` value (common with raw API data where the whole
    location is dumped into one field).

    Args:
        job: A Job-like object with ``city``, ``state``, ``area`` attributes.

    Returns:
        Dict of normalized ``state`` / ``city`` / ``area`` to assign back.
    """
    city_val = getattr(job, "city", "") or ""
    state_val = getattr(job, "state", "") or ""
    area_val = getattr(job, "area", "") or ""

    # Combine whatever location pieces we have, state last.
    pieces = [p for p in (area_val, city_val, state_val) if p and p.strip()]
    combined = ", ".join(pieces) if pieces else ""

    parsed = parse_location(combined)

    # Don't clobber an already-correct explicit state with an empty parsed one
    if not parsed["state"] and state_val:
        parsed["state"] = state_val
    if not parsed["city"] and city_val:
        parsed["city"] = city_val
    return parsed
