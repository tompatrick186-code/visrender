"""
VisRender — Business Finder
Finds UK landscaping/gardening businesses using Google Places API
and saves them to a CSV for outreach.

Setup:
  pip install requests
  Set GOOGLE_API_KEY in config.py

Usage:
  python find_businesses.py
  python find_businesses.py --location "Manchester" --radius 30000
"""

import requests
import csv
import time
import argparse
import os
from config import GOOGLE_API_KEY

PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

# UK cities to search — expand as needed
DEFAULT_LOCATIONS = [
    ("London",       51.5074, -0.1278),
    ("Manchester",   53.4808, -2.2426),
    ("Birmingham",   52.4862, -1.8904),
    ("Leeds",        53.8008, -1.5491),
    ("Glasgow",      55.8642, -4.2518),
    ("Bristol",      51.4545, -2.5879),
    ("Edinburgh",    55.9533, -3.1883),
    ("Sheffield",    53.3811, -1.4701),
    ("Liverpool",    53.4084, -2.9916),
    ("Nottingham",   52.9548, -1.1581),
]

SEARCH_KEYWORDS = [
    "landscaping company",
    "landscape gardener",
    "garden design",
    "garden maintenance",
]


def search_places(lat, lng, keyword, radius=25000):
    """Search for businesses near a location."""
    results = []
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": keyword,
        "type": "establishment",
        "key": GOOGLE_API_KEY,
    }

    while True:
        resp = requests.get(PLACES_NEARBY_URL, params=params, timeout=10)
        data = resp.json()

        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            print(f"  API error: {data.get('status')} — {data.get('error_message', '')}")
            break

        results.extend(data.get("results", []))

        next_token = data.get("next_page_token")
        if not next_token:
            break

        # Google requires a short delay before using next_page_token
        time.sleep(2)
        params = {"pagetoken": next_token, "key": GOOGLE_API_KEY}

    return results


def get_place_details(place_id):
    """Get email, website and phone for a place."""
    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,website,formatted_address,url",
        "key": GOOGLE_API_KEY,
    }
    resp = requests.get(PLACES_DETAILS_URL, params=params, timeout=10)
    return resp.json().get("result", {})


def find_businesses(locations=None, radius=25000, output_file="businesses.csv"):
    if locations is None:
        locations = DEFAULT_LOCATIONS

    seen_ids = set()
    rows = []

    for city_name, lat, lng in locations:
        print(f"\nSearching {city_name}...")
        for keyword in SEARCH_KEYWORDS:
            print(f"  Keyword: {keyword}")
            places = search_places(lat, lng, keyword, radius)
            print(f"  Found {len(places)} results")

            for place in places:
                pid = place.get("place_id")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)

                print(f"    Getting details for: {place.get('name')}")
                details = get_place_details(pid)
                time.sleep(0.1)  # stay well within rate limits

                rows.append({
                    "name":     details.get("name", place.get("name", "")),
                    "address":  details.get("formatted_address", ""),
                    "phone":    details.get("formatted_phone_number", ""),
                    "website":  details.get("website", ""),
                    "maps_url": details.get("url", ""),
                    "city":     city_name,
                    "emailed":  "no",
                })

    # Write CSV
    fieldnames = ["name", "address", "phone", "website", "maps_url", "city", "emailed"]
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {len(rows)} businesses saved to {output_file}")
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find UK landscaping businesses")
    parser.add_argument("--location", help="Single city name to search")
    parser.add_argument("--radius", type=int, default=25000, help="Search radius in metres")
    parser.add_argument("--output", default="businesses.csv", help="Output CSV filename")
    args = parser.parse_args()

    if args.location:
        # Geocode the custom location
        geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geo = requests.get(geo_url, params={"address": args.location + " UK", "key": GOOGLE_API_KEY}).json()
        if geo.get("results"):
            loc = geo["results"][0]["geometry"]["location"]
            locations = [(args.location, loc["lat"], loc["lng"])]
        else:
            print("Could not geocode location. Using defaults.")
            locations = None
    else:
        locations = None

    find_businesses(locations=locations, radius=args.radius, output_file=args.output)
