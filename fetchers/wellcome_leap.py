"""
fetchers/wellcome_leap.py — Wellcome Leap Fetcher
==================================================
Wellcome Leap is a separate organization from Wellcome Trust, funding
high-risk/high-reward health R&D programs. Uses the WordPress REST API
to find open programs.

API: GET https://wellcomeleap.org/wp-json/wp/v2/pages (no auth required)
"""

import hashlib
import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SOURCE   = "Wellcome Leap"
API_URL  = "https://wellcomeleap.org/wp-json/wp/v2/pages"
BASE_URL = "https://wellcomeleap.org"
log = logging.getLogger(__name__)
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; FundingScanner/1.0)"}

# Slugs/paths we know are not active program pages
SKIP_SLUGS = {
    "home", "about", "team", "news", "events", "contact", "privacy",
    "terms", "faq", "partners", "jobs", "careers", "media", "press",
    "annual-report", "our-approach", "portfolio", "blog",
}

# Keywords suggesting a page is an active funded program or open call
PROGRAM_SIGNALS = [
    "program", "challenge", "grant", "call", "apply", "application",
    "rfp", "award", "funding", "thrust",
]

# Global health relevance keywords
HEALTH_KEYWORDS = [
    "health", "disease", "clinical", "patient", "infection", "vaccine",
    "antibiotic", "nutrition", "maternal", "child", "mental", "cancer",
    "diagnostic", "treatment", "prevention", "malaria", "HIV", "TB",
    "microbiome", "drug", "medicine", "medical", "biotech", "genomic",
    "global health", "low-income",
]


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def _extract_deadline(html: str) -> str:
    """Try to pull a deadline date out of rendered HTML content."""
    text = _strip_html(html)
    patterns = [
        r"(?:abstract|letter of intent|application|deadline|due|close[sd]?)[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"(?:abstract|letter of intent|application|deadline|due|close[sd]?)[:\s]+(\d{1,2} [A-Za-z]+ \d{4})",
        r"(?:by|before|submit(?:ted)? by)[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip().rstrip(",")
            for fmt in ("%B %d %Y", "%B %d, %Y", "%d %B %Y"):
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return ""


def _is_health_relevant(title: str, content: str) -> bool:
    combined = (title + " " + _strip_html(content)).lower()
    return any(kw.lower() in combined for kw in HEALTH_KEYWORDS)


def _is_program_page(title: str, content: str, slug: str) -> bool:
    if slug in SKIP_SLUGS:
        return False
    combined = (title + " " + _strip_html(content)).lower()
    return any(sig in combined for sig in PROGRAM_SIGNALS)


def _extract_description(html: str, max_len: int = 400) -> str:
    text = _strip_html(html)
    # Take the first substantive paragraph
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] if text else ""


def fetch(keywords: list[str]) -> list[dict]:
    seen_ids: set[str] = set()
    results:  list[dict] = []

    try:
        resp = requests.get(
            API_URL,
            params={"per_page": 100, "_fields": "id,title,link,slug,content,date,modified"},
            headers=HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        pages = resp.json()
    except requests.RequestException as e:
        log.warning("[%s] Failed to fetch pages: %s", SOURCE, e)
        return []
    except (ValueError, KeyError) as e:
        log.warning("[%s] Failed to parse response: %s", SOURCE, e)
        return []

    for page in pages:
        page_id  = str(page.get("id", ""))
        title    = page.get("title", {}).get("rendered", "").strip()
        link     = page.get("link", "")
        slug     = page.get("slug", "")
        content  = page.get("content", {}).get("rendered", "")

        if not title or not link or page_id in seen_ids:
            continue
        if not _is_program_page(title, content, slug):
            continue
        if not _is_health_relevant(title, content):
            continue

        seen_ids.add(page_id)
        deadline = _extract_deadline(content)
        desc     = _extract_description(content)

        results.append({
            "id":            f"wleap-{page_id}",
            "title":         title,
            "agency":        "Wellcome Leap",
            "deadline":      deadline,
            "award_ceiling": "",
            "url":           link,
            "source":        SOURCE,
            "description":   desc,
        })

    log.info("[%s] Fetched %d relevant program pages.", SOURCE, len(results))
    return results
