"""
fetchers/gates.py — Gates Foundation Grand Challenges Fetcher
==============================================================
Scrapes open funding challenges from the Grand Challenges website
(https://gcgh.grandchallenges.org/challenges).
"""

import hashlib
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SOURCE    = "Gates Foundation (Grand Challenges)"
BASE_URL  = "https://gcgh.grandchallenges.org"
CHALLENGES_URL = f"{BASE_URL}/challenges"
log = logging.getLogger(__name__)
HEADERS   = {"User-Agent": "Mozilla/5.0"}


def _matches(text: str, keywords: list[str]) -> bool:
    tl = text.lower()
    if not keywords:
        return True
    return any(kw.lower() in tl for kw in keywords)


def fetch(keywords: list[str]) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    try:
        resp = requests.get(CHALLENGES_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for a in soup.select("h3 a"):
            href  = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or not href:
                continue
            full_url = urljoin(BASE_URL, href)
            title_key = title.lower().strip()
            if title_key in seen:
                continue
            seen.add(title_key)
            opp_id = hashlib.md5(full_url.encode()).hexdigest()
            results.append({
                "id":          opp_id,
                "title":       title,
                "agency":      "Bill & Melinda Gates Foundation",
                "deadline":    "",
                "url":         full_url,
                "source":      SOURCE,
                "description": "",
            })
    except requests.RequestException as e:
        log.warning("[%s] Failed to fetch challenges page: %s", SOURCE, e)
    except Exception as e:
        log.warning("[%s] Unexpected error: %s", SOURCE, e)

    log.info("[%s] Fetched %d keyword-matching entries.", SOURCE, len(results))
    return results
