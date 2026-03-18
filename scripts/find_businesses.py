"""
VisRender — Business Finder (DuckDuckGo)
Finds UK landscaping businesses by scraping DuckDuckGo search results.
No API key required — completely free.

Setup:
  pip3 install requests beautifulsoup4

Usage:
  python3 find_businesses.py
  python3 find_businesses.py --location "Manchester"
  python3 find_businesses.py --location "Bristol" --output bristol.csv
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import argparse
import re
import random
from urllib.parse import urlparse, unquote

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

UK_CITIES = [
    "London", "Manchester", "Birmingham", "Leeds", "Glasgow",
    "Bristol", "Edinburgh", "Sheffield", "Liverpool", "Nottingham",
    "Cardiff", "Leicester", "Southampton", "Brighton", "Newcastle",
    "Oxford", "Cambridge", "Exeter", "Norwich", "York",
]


def ddg_search(query):
    """Scrape DuckDuckGo HTML results for a query."""
    results = []
    url = "https://html.duckduckgo.com/html/"
    data = {"q": query, "kl": "uk-en"}

    for attempt in range(3):
        resp = requests.post(url, data=data, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            break
        time.sleep(random.uniform(10, 20))
    if resp.status_code != 200:
        return results

    soup = BeautifulSoup(resp.text, "html.parser")
    for result in soup.select(".result__body"):
        title_el = result.select_one(".result__title a")
        snippet_el = result.select_one(".result__snippet")
        url_el = result.select_one(".result__url")

        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        href = title_el.get("href", "")

        # Extract real URL from DDG redirect
        website = ""
        if "uddg=" in href:
            match = re.search(r"uddg=([^&]+)", href)
            if match:
                website = unquote(match.group(1))
        elif href.startswith("http"):
            website = href

        # Skip directories, social media, job sites
        skip_domains = ["yell.com", "checkatrade.com", "facebook.com",
                        "linkedin.com", "indeed.com", "reed.co.uk",
                        "bark.com", "yelp.com", "trustpilot.com"]
        if any(d in website for d in skip_domains):
            continue

        # Try to extract a phone number from the snippet
        phone_match = re.search(r"(\b0[0-9]{4}\s?[0-9]{3}\s?[0-9]{3,4}\b|\b07[0-9]{9}\b)", snippet)
        phone = phone_match.group(0) if phone_match else ""

        results.append({
            "name":    title,
            "snippet": snippet,
            "website": website,
            "phone":   phone,
        })

    return results


def derive_email(website):
    """Guess a likely contact email from a domain."""
    if not website:
        return ""
    try:
        domain = urlparse(website).netloc.replace("www.", "")
        if domain and "." in domain:
            return f"info@{domain}"
    except Exception:
        pass
    return ""


def find_businesses(locations=None, output_file="businesses.csv"):
    if locations is None:
        locations = UK_CITIES

    all_rows = []
    seen_websites = set()

    for city in locations:
        print(f"\nSearching {city}...")
        queries = [
            f"landscaping company {city} UK",
            f"landscape gardener {city} UK",
            f"garden design {city} UK",
        ]

        for query in queries:
            results = ddg_search(query)
            print(f"  '{query}': {len(results)} results")

            for r in results:
                site = r["website"].lower().strip("/")
                if site and site in seen_websites:
                    continue
                if site:
                    seen_websites.add(site)

                email = derive_email(r["website"])
                all_rows.append({
                    "name":    r["name"],
                    "website": r["website"],
                    "email":   email,
                    "phone":   r["phone"],
                    "city":    city,
                    "emailed": "no",
                })

            time.sleep(random.uniform(6, 10))  # avoid rate limiting

    fieldnames = ["name", "website", "email", "phone", "city", "emailed"]
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nDone. {len(all_rows)} businesses saved to {output_file}")
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find UK landscaping businesses via DuckDuckGo")
    parser.add_argument("--location", help="City to search (e.g. Bristol)")
    parser.add_argument("--output", default="businesses.csv")
    args = parser.parse_args()

    locations = [args.location] if args.location else None
    find_businesses(locations=locations, output_file=args.output)
