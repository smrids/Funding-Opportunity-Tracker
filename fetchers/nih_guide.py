"""
fetchers/nih_guide.py — NIH Guide for Grants & Contracts Fetcher
=================================================================
Parses the official NIH Guide RSS feeds for Program Announcements (PAs)
and Requests for Applications (RFAs). Particularly relevant for finding
Fogarty International Center (FIC) and other global-health NIH funding.

No API key required — public RSS feeds.
Feeds:
  https://grants.nih.gov/grants/guide/rss/pa_rss.xml   (Program Announcements)
  https://grants.nih.gov/grants/guide/rss/rfa_rss.xml  (Requests for Applications)
"""

import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET

import requests

SOURCE = "NIH Guide"
log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FundingScanner/1.0)"}

RSS_FEEDS = [
    "https://grants.nih.gov/grants/guide/rss/rfa_rss.xml",  # RFAs — highest priority
    "https://grants.nih.gov/grants/guide/rss/pa_rss.xml",   # Program Announcements
]

# NIH Institute/Center codes relevant to global & international health.
# Any announcement mentioning one of these is included regardless of keywords.
GLOBAL_HEALTH_ICS = {
    "FIC",    # Fogarty International Center — primary global health IC
    "NIAID",  # Allergy & Infectious Diseases
    "NICHD",  # Child Health & Human Development
    "NIMH",   # Mental Health
    "NIDA",   # Drug Abuse (global substance use)
    "NCI",    # Cancer (global oncology)
    "NHLBI",  # Heart, Lung, Blood
    "NIMHD",  # Minority Health & Health Disparities
    "OBSSR",  # Behavioral & Social Sciences Research
    "ODP",    # Disease Prevention
    "ODS",    # Dietary Supplements
}


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    tl = text.lower()
    return any(kw.lower() in tl for kw in keywords)


def _extract_deadline(text: str) -> str:
    """Try to pull an expiration/close date from the HTML description."""
    if not text:
        return ""
    patterns = [
        r"expiration\s+date[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"due\s+date[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{2}/\d{2}/\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip().rstrip(",")
            for fmt in ("%B %d %Y", "%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    from datetime import datetime
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return ""


def _agency_label(combined: str) -> str:
    """Build a readable agency string from detected IC codes."""
    found = [ic for ic in GLOBAL_HEALTH_ICS if re.search(r"\b" + ic + r"\b", combined)]
    if not found:
        return "NIH"
    if "FIC" in found:
        others = [ic for ic in found if ic != "FIC"]
        if others:
            return f"NIH/Fogarty ({', '.join(others[:2])})"
        return "NIH/Fogarty International Center"
    return f"NIH ({', '.join(found[:3])})"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _parse_feed(feed_url: str, keywords: list[str]) -> list[dict]:
    results: list[dict] = []
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        for item in root.findall(".//item"):
            def gtext(tag: str) -> str:
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""

            title    = gtext("title")
            link     = gtext("link") or gtext("guid")
            raw_desc = gtext("description")
            desc     = _strip_html(raw_desc)

            if not title or not link:
                continue

            combined = f"{title} {desc}".upper()
            ic_hit   = any(re.search(r"\b" + ic + r"\b", combined) for ic in GLOBAL_HEALTH_ICS)
            kw_hit   = _matches_keywords(f"{title} {desc}", keywords)

            if not (ic_hit or kw_hit):
                continue

            opp_id   = hashlib.md5(link.encode()).hexdigest()
            deadline = _extract_deadline(desc)
            agency   = _agency_label(combined)

            results.append({
                "id":            opp_id,
                "title":         title,
                "agency":        agency,
                "deadline":      deadline,
                "award_ceiling": "",
                "url":           link,
                "source":        SOURCE,
                "description":   desc[:400],
            })

    except requests.RequestException as e:
        log.warning("[%s] Could not fetch %s: %s", SOURCE, feed_url, e)
    except ET.ParseError as e:
        log.warning("[%s] XML parse error for %s: %s", SOURCE, feed_url, e)

    return results


def fetch(keywords: list[str]) -> list[dict]:
    seen_ids: set[str] = set()
    results:  list[dict] = []

    for feed_url in RSS_FEEDS:
        for opp in _parse_feed(feed_url, keywords):
            if opp["id"] not in seen_ids:
                seen_ids.add(opp["id"])
                results.append(opp)
        time.sleep(0.5)

    log.info("[%s] Fetched %d relevant opportunities.", SOURCE, len(results))
    return results
