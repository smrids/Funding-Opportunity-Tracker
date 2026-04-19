"""
fetchers/nih_guide.py — NIH Global Health Opportunities Fetcher
================================================================
Uses the Grants.gov REST API filtered to NIH agency codes relevant to
global and international health, particularly Fogarty (HHS-NIH11).

This supplements the main grants_gov.py fetcher (which searches by keyword
across all agencies) by searching NIH-specific agencies with a broader set
of global health terms — catching announcements that don't match our exact
keywords but are still relevant to international health faculty.

No API key required.
"""

import hashlib
import logging
import time

import requests

SOURCE  = "NIH (Global Health)"
API_URL = "https://api.grants.gov/v1/api/search2"
HEADERS = {"Content-Type": "application/json"}
log = logging.getLogger(__name__)

# Agency codes for NIH institutes relevant to global/international health.
# HHS-NIH11 = Fogarty International Center (primary global health IC).
NIH_AGENCY_CODES = [
    "HHS-NIH11",   # Fogarty International Center
    "HHS-NIH-NIA", # National Institute on Aging (global aging)
    "HHS-NIH02",   # NIAID — Allergy & Infectious Diseases
    "HHS-NIH13",   # NICHD — Child Health & Human Development
    "HHS-NIH",     # Broad NIH catch-all
]

# Broader search terms used specifically for NIH — complements config.py keywords
NIH_KEYWORDS = [
    "global health",
    "international health",
    "low-income countries",
    "sub-Saharan Africa",
    "Fogarty",
    "D43",           # Fogarty's primary training grant mechanism
    "K43",           # Emerging Global Leader Award (Fogarty)
    "infectious disease",
    "maternal child health",
    "health systems",
]


def _normalize_date(raw: str) -> str:
    if not raw:
        return ""
    raw = str(raw).strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[4:8]}-{raw[0:2]}-{raw[2:4]}"
    return raw


def fetch(keywords: list[str]) -> list[dict]:
    seen_ids: set[str] = set()
    results:  list[dict] = []

    # Search with each NIH agency code + broad global health keywords
    for agency_code in NIH_AGENCY_CODES[:3]:   # top 3 most relevant
        for kw in NIH_KEYWORDS[:5]:            # top 5 keywords per agency
            try:
                payload = {
                    "keyword":     kw,
                    "agencyCode":  agency_code,
                    "oppStatuses": "posted|forecasted",
                    "rows":        25,
                    "startRecordNum": 0,
                    "sortBy":      "openDate|desc",
                }
                resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                hits = (
                    data.get("data", {}).get("oppHits", [])
                    or data.get("oppHits", [])
                    or []
                )
                for opp in hits:
                    opp_id = str(
                        opp.get("id")
                        or opp.get("oppNumber")
                        or hashlib.md5(opp.get("title", kw).encode()).hexdigest()
                    )
                    if opp_id in seen_ids:
                        continue
                    seen_ids.add(opp_id)

                    agency_name = opp.get("agencyName") or opp.get("agencyCode", agency_code)
                    if agency_code == "HHS-NIH11" or "fogarty" in str(agency_name).lower():
                        agency_name = "NIH/Fogarty International Center"

                    results.append({
                        "id":            opp_id,
                        "title":         opp.get("title", "Untitled"),
                        "agency":        agency_name,
                        "deadline":      _normalize_date(opp.get("closeDate", "")),
                        "award_ceiling": str(opp.get("awardCeiling", "") or ""),
                        "url":           f"https://www.grants.gov/search-results-detail/{opp_id}",
                        "source":        SOURCE,
                        "description":   (opp.get("synopsis") or opp.get("description") or "")[:400],
                    })

            except requests.RequestException as e:
                log.warning("[%s] Request failed (%s / %s): %s", SOURCE, agency_code, kw, e)
            time.sleep(0.3)

    log.info("[%s] Fetched %d opportunities.", SOURCE, len(results))
    return results
