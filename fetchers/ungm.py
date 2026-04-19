"""
fetchers/ungm.py — UN Global Marketplace (UNGM) Fetcher
=========================================================
Searches UNGM's public notice board for WHO, UNICEF, UNDP, UNFPA and other
UN agency consultancy calls, grants, and implementing partner requests relevant
to global health faculty.

API: POST https://www.ungm.org/Public/Notice/Search (no auth required)
Returns HTML rows that we parse with BeautifulSoup.
"""

import hashlib
import logging
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SOURCE  = "UNGM (UN Agencies)"
SEARCH_URL = "https://www.ungm.org/Public/Notice/Search"
BASE_URL   = "https://www.ungm.org"
log = logging.getLogger(__name__)
HEADERS = {
    "User-Agent":   "Mozilla/5.0 (compatible; FundingScanner/1.0)",
    "Content-Type": "application/json",
    "Accept":       "text/html, */*",
    "Referer":      "https://www.ungm.org/Public/Notice",
}

# UN agency IDs to search (health-focused UN bodies).
# Leave empty to search across all agencies.
HEALTH_AGENCIES = []  # Empty = all agencies (more results, then keyword-filter)

# Notice types most relevant to global health faculty
RELEVANT_TYPES = {
    "grant support",
    "call for proposal",
    "call for implementing",
    "call for individual",
    "request for proposal",
    "consultancy",
    "technical assistance",
}

# Global health keywords to filter results
HEALTH_KEYWORDS = [
    "health", "nutrition", "HIV", "malaria", "tuberculosis", "TB",
    "maternal", "child", "reproductive", "epidemiology", "disease",
    "vaccine", "immunization", "WASH", "sanitation", "mental health",
    "NCDs", "cancer", "pandemic", "surveillance", "one health",
    "public health", "community health", "primary care",
]


def _parse_deadline(raw: str) -> str:
    """Convert '31-May-2026 23:59 (GMT -4.00)' → '2026-05-31'."""
    if not raw:
        return ""
    m = re.search(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", raw)
    if not m:
        return ""
    try:
        return datetime.strptime(f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "%d-%b-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _matches(text: str) -> bool:
    tl = text.lower()
    return any(kw.lower() in tl for kw in HEALTH_KEYWORDS)


def _is_relevant_type(notice_type: str) -> bool:
    nt = notice_type.lower()
    return any(t in nt for t in RELEVANT_TYPES)


def _search(keyword: str, page: int = 0) -> list[dict]:
    payload = {
        "PageIndex":   page,
        "PageSize":    25,
        "Title":       keyword,
        "Description": "",
        "IsActive":    True,
        "SortField":   "Deadline",
        "SortAscending": True,
        "Agencies":    HEALTH_AGENCIES,
        "Countries":   [],
        "UNSPSCs":     [],
        "NoticeTypes": [],
        "TypeOfCompetitions": [],
        "isPicker":    False,
        "IsSustainable": False,
    }
    try:
        resp = requests.post(SEARCH_URL, json=payload, headers=HEADERS, timeout=25)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("[%s] Search failed for '%s': %s", SOURCE, keyword, e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    rows = soup.find_all("div", attrs={"role": "row", "data-noticeid": True})
    results = []
    for row in rows:
        notice_id = row.get("data-noticeid", "")
        if not notice_id:
            continue

        title_el  = row.find(class_="ungm-title")
        title     = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        # Collect all span texts for deadline / agency / type
        spans = [s.get_text(strip=True) for s in row.find_all("span") if s.get_text(strip=True)]

        deadline    = ""
        agency      = ""
        notice_type = ""
        for span in spans:
            if re.search(r"\d{1,2}-[A-Za-z]{3}-\d{4}", span) and not deadline:
                deadline = _parse_deadline(span)
            elif any(a in span for a in ["WHO", "UNICEF", "UNDP", "UNFPA", "WFP", "UN ", "ILO", "FAO", "UNAIDS"]):
                agency = span
            elif any(t in span.lower() for t in RELEVANT_TYPES) and not notice_type:
                notice_type = span

        # Filter: skip if not health-related in title/type
        if not (_matches(title) or _is_relevant_type(notice_type)):
            continue

        results.append({
            "id":            f"ungm-{notice_id}",
            "title":         title,
            "agency":        agency or "UN Agency",
            "deadline":      deadline,
            "award_ceiling": "",
            "url":           f"{BASE_URL}/Public/Notice/{notice_id}",
            "source":        SOURCE,
            "description":   notice_type,
        })
    return results


def fetch(keywords: list[str]) -> list[dict]:
    seen_ids: set[str] = set()
    results:  list[dict] = []

    # Use a focused set of UNGM-specific health search terms
    ungm_terms = [
        "global health", "public health", "maternal health", "child health",
        "nutrition", "HIV", "malaria", "tuberculosis", "epidemiology",
        "health systems", "reproductive health",
    ]

    for term in ungm_terms:
        for opp in _search(term):
            if opp["id"] not in seen_ids:
                seen_ids.add(opp["id"])
                results.append(opp)
        time.sleep(1.0)

    log.info("[%s] Fetched %d relevant opportunities.", SOURCE, len(results))
    return results
