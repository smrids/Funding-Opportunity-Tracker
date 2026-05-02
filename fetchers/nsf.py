"""
fetchers/nsf.py — National Science Foundation Funding Opportunities Fetcher
============================================================================
Uses the NSF public awards API to find relevant active programs,
and also searches Grants.gov for open NSF solicitations.

API docs: https://resources.research.gov/common/webapi/awardapisearch-v1.htm
No API key required.
"""

import hashlib
import logging
import time

import requests

SOURCE  = "NSF"
# NSF open solicitations are posted to Grants.gov — we search via their API
GRANTS_GOV_URL = "https://api.grants.gov/v1/api/search2"
log = logging.getLogger(__name__)
HEADERS = {"Content-Type": "application/json"}

# NSF-specific health & AI keywords
NSF_KEYWORDS = [
    "smart health artificial intelligence",
    "global health data science",
    "public health informatics",
    "health disparities machine learning",
    "biomedical informatics",
    "digital health NSF",
    "global health NSF",
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

    for kw in NSF_KEYWORDS:
        try:
            payload = {
                "keyword":     kw,
                "agencyCode":  "NSF",
                "oppStatuses": "posted|forecasted",
                "rows":        25,
                "startRecordNum": 0,
                "sortBy":      "openDate|desc",
            }
            resp = requests.post(GRANTS_GOV_URL, headers=HEADERS, json=payload, timeout=30)
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
                results.append({
                    "id":            opp_id,
                    "title":         opp.get("title", "Untitled"),
                    "agency":        opp.get("agencyName") or "National Science Foundation",
                    "deadline":      _normalize_date(opp.get("closeDate", "")),
                    "award_ceiling": str(opp.get("awardCeiling", "") or ""),
                    "url":           f"https://www.grants.gov/search-results-detail/{opp_id}",
                    "source":        SOURCE,
                    "description":   (opp.get("synopsis") or opp.get("description") or "")[:400],
                })
        except requests.RequestException as e:
            log.warning("[%s] Request failed for '%s': %s", SOURCE, kw, e)
        time.sleep(0.3)

    log.info("[%s] Fetched %d opportunities.", SOURCE, len(results))
    return results
