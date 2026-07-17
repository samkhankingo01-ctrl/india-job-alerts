"""Tests for the India location parser – the core of the location requirement."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make repo importable when run from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scripts.location_parser import (  # noqa: E402
    is_india_location,
    parse_location,
)


# ── parse_location: State / City / Area splitting ───────────────────────────
def test_area_city_state_full():
    r = parse_location("Dadar, Mumbai, Maharashtra")
    assert r["area"] == "Dadar"
    assert r["city"] == "Mumbai"
    assert r["state"] == "Maharashtra"
    assert r["location_raw"] == "Dadar, Mumbai, Maharashtra"


def test_city_state_no_area():
    r = parse_location("Mumbai, Maharashtra")
    assert r["city"] == "Mumbai"
    assert r["state"] == "Maharashtra"
    assert r["area"] == ""


def test_city_only_infers_state():
    r = parse_location("Bangalore")
    assert r["city"] == "Bangalore"
    assert r["state"] == "Karnataka"
    assert r["area"] == ""


def test_bengaluru_variant():
    r = parse_location("Bengaluru")
    assert r["city"] == "Bengaluru"
    assert r["state"] == "Karnataka"


def test_area_city_infers_state():
    r = parse_location("Whitefield, Bangalore")
    assert r["area"] == "Whitefield"
    assert r["city"] == "Bangalore"
    assert r["state"] == "Karnataka"


def test_vashi_navi_mumbai():
    r = parse_location("Vashi, Navi Mumbai")
    assert r["area"] == "Vashi"
    assert r["city"] == "Navi Mumbai"
    assert r["state"] == "Maharashtra"


def test_delhi_ut():
    r = parse_location("Connaught Place, New Delhi")
    assert r["area"] == "Connaught Place"
    assert r["city"] == "New Delhi"
    assert r["state"] == "Delhi"


def test_with_india_suffix():
    r = parse_location("Whitefield, Bangalore, Karnataka, India")
    assert r["area"] == "Whitefield"
    assert r["city"] == "Bangalore"
    assert r["state"] == "Karnataka"


def test_remote_is_kept_raw_no_fields():
    r = parse_location("Remote")
    assert r["state"] == ""
    assert r["city"] == ""
    assert r["area"] == ""
    assert r["location_raw"] == "Remote"


def test_empty_string():
    r = parse_location("")
    assert r["state"] == ""
    assert r["city"] == ""
    assert r["area"] == ""
    assert r["location_raw"] == ""


def test_preserves_raw_verbatim():
    """The raw string must be preserved EXACTLY – never replaced with India."""
    raw = "Andheri East, Mumbai, Maharashtra"
    r = parse_location(raw)
    assert r["location_raw"] == raw
    assert r["location_raw"] != "India"


# ── is_india_location: hard filter ──────────────────────────────────────────
def test_india_detection_known_city():
    assert is_india_location("Bangalore") is True


def test_india_detection_known_state():
    assert is_india_location("Maharashtra") is True


def test_india_detection_explicit_token():
    assert is_india_location("Berlin, Germany") is False
    assert is_india_location("Anywhere, India") is True


def test_foreign_city_rejected():
    assert is_india_location("Berlin") is False
    assert is_india_location("Cologne") is False
    assert is_india_location("New York, USA") is False


def test_empty_rejected():
    assert is_india_location("") is False


def test_remote_rejected():
    """Pure 'Remote' with no India token must be rejected by the hard filter."""
    assert is_india_location("Remote") is False
    assert is_india_location("Worldwide") is False
