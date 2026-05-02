"""
fetchers/pcori.py — Patient-Centered Outcomes Research Institute Fetcher
=========================================================================
Scrapes PCORI's funding opportunities table for open/upcoming calls.
Particularly relevant for AI/ML methods in comparative effectiveness research.

No API key required. Page: https://www.pcori.org/funding-opportunities/
"""

import hashlib
import logging
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SOURCE   = "PCORI"
BASE_URL = "https://www.pcori.org"
LIST_URL = "https://www.pcori.org/funding-opportunities/"
log = logging.getLogger(__name__)
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; FundingScanner/1.0)"}


def _parse_date(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try extracting from free text
    m = re.search(r"([A-Za-z]+ \d{1,2},?\s*\d{4})", raw)
    if m:
        for fmt in ("%B %d %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(m.group(1).rstrip(","), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return ""


def _fetch_page(url: str) -> list[dict]:
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Each opportunity row: look for table rows or list items with links + dates
        rows = (
            soup.select("tr.views-row")
            or soup.select("tr[class*='odd'], tr[class*='even']")
            or soup.select("table tr")[1:]   # skip header row
            or soup.select(".views-row")
        )

        for row in rows:
            # Title + URL
            link_el = row.find("a", href=True)
            if not link_el:
                continue
            title = link_el.get_text(strip=True)
            href  = link_el["href"]
            url_  = href if href.startswith("http") else BASE_URL + href

            # Skip closed opportunities
            status_el = row.find(string=re.compile(r"closed|archived", re.I))
            if status_el:
                continue

            # Extract all date-like text from the row
            row_text  = row.get_text(" ", strip=True)
            deadline  = ""

            # Prefer "Application Deadline" over "LOI Deadline"
            for label in ["application deadline", "application due", "deadline"]:
                m = re.search(label + r"[:\s]+([0-9/A-Za-z, ]+\d{4})", row_text, re.IGNORECASE)
                if m:
                    deadline = _parse_date(m.group(1).strip())
                    if deadline:
                        break

            if not deadline:
                # Grab any date that looks future
                for raw_date in re.findall(r"\d{1,2}/\d{1,2}/\d{4}", row_text):
                    deadline = _parse_date(raw_date)
                    if deadline:
                        break

            opp_id = "pcori-" + hashlib.md5(url_.encode()).hexdigest()[:10]
            results.append({
                "id":            opp_id,
                "title":         title,
                "agency":        "Patient-Centered Outcomes Research Institute (PCORI)",
                "deadline":      deadline,
                "award_ceiling": "",
                "url":           url_,
                "source":        SOURCE,
                "description":   "",
            })
    except requests.RequestException as e:
        log.warning("[%s] Request failed for %s: %s", SOURCE, url, e)
    return results


def fetch(keywords: list[str]) -> list[dict]:
    seen_ids: set[str] = set()
    results:  list[dict] = []

    # Fetch first two pages of open opportunities
    urls = [LIST_URL, LIST_URL + "?page=1"]
    for url in urls:
        for opp in _fetch_page(url):
            if opp["id"] not in seen_ids:
                seen_ids.add(opp["id"])
                results.append(opp)
        time.sleep(0.8)

    log.info("[%s] Fetched %d opportunities.", SOURCE, len(results))
    return results
