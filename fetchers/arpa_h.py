"""
fetchers/arpa_h.py — ARPA-H (Advanced Research Projects Agency for Health) Fetcher
====================================================================================
Scrapes open programs and funding opportunities from ARPA-H.
Highly relevant for AI-enabled health innovation at JHU.

No API key required. Programs: https://arpa-h.gov/explore-funding/
"""

import hashlib
import logging
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SOURCE   = "ARPA-H"
BASE_URL = "https://arpa-h.gov"
PAGES    = [
    "/explore-funding/programs/",
    "/explore-funding/open-opportunities/",
    "/explore-funding/broad-agency-announcements/",
]
log = logging.getLogger(__name__)
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; FundingScanner/1.0)"}


def _parse_date(raw: str) -> str:
    if not raw:
        return ""
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return __import__("datetime").datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r"([A-Za-z]+ \d{1,2},?\s*\d{4})", raw)
    if m:
        for fmt in ("%B %d %Y", "%B %d, %Y"):
            try:
                from datetime import datetime
                return datetime.strptime(m.group(1).rstrip(","), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return ""


def _scrape_listing(path: str) -> list[dict]:
    url = BASE_URL + path
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Collect all meaningful links (headings, cards, list items)
        candidates = (
            soup.select("article a[href]")
            or soup.select(".card a[href]")
            or soup.select("h2 a[href], h3 a[href], h4 a[href]")
            or soup.select("li a[href]")
        )

        seen_hrefs: set[str] = set()
        for el in candidates:
            title = el.get_text(strip=True)
            href  = el.get("href", "")
            if not title or len(title) < 10 or not href:
                continue
            if any(s in href for s in ["#", "mailto:", "tel:", "/about", "/news", "/events"]):
                continue
            full_url = urljoin(BASE_URL, href) if not href.startswith("http") else href
            if full_url in seen_hrefs:
                continue
            seen_hrefs.add(full_url)

            # Try to get a description + deadline from the surrounding context
            parent = el.find_parent(["article", "li", "div", "section"])
            ctx_text = parent.get_text(" ", strip=True) if parent else title
            deadline = ""
            for label in ["deadline", "due date", "closes", "applications due"]:
                m = re.search(label + r"[:\s]+([A-Za-z0-9/, ]+\d{4})", ctx_text, re.IGNORECASE)
                if m:
                    deadline = _parse_date(m.group(1).strip())
                    if deadline:
                        break

            desc = re.sub(r"\s+", " ", ctx_text).strip()
            if desc.startswith(title):
                desc = desc[len(title):].strip(" —:-")
            desc = desc[:400]

            opp_id = "arpa-h-" + hashlib.md5(full_url.encode()).hexdigest()[:10]
            results.append({
                "id":            opp_id,
                "title":         title,
                "agency":        "ARPA-H",
                "deadline":      deadline,
                "award_ceiling": "",
                "url":           full_url,
                "source":        SOURCE,
                "description":   desc,
            })
    except requests.RequestException as e:
        log.warning("[%s] Could not fetch %s: %s", SOURCE, url, e)
    return results


def fetch(keywords: list[str]) -> list[dict]:
    seen_ids: set[str] = set()
    results:  list[dict] = []

    for path in PAGES:
        for opp in _scrape_listing(path):
            if opp["id"] not in seen_ids:
                seen_ids.add(opp["id"])
                results.append(opp)
        time.sleep(0.8)

    log.info("[%s] Fetched %d opportunities.", SOURCE, len(results))
    return results
