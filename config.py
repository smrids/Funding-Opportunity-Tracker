"""
config.py — Funding Opportunity Scanner Configuration
=====================================================
All settings are read from environment variables so no credentials
are ever hard-coded. Copy .env.example → .env and fill in the values.

Required env vars
-----------------
ALERT_EMAIL_FROM      Gmail sender address  (e.g. you@gmail.com)
ALERT_EMAIL_PASSWORD  Gmail App Password    (16-char, spaces ok)
ALERT_EMAIL_TO        Comma-separated recipient(s)

Optional env vars
-----------------
ALERT_SCHEDULE_TIME   HH:MM (24h) for daily run  [default: 16:00]
ALERT_KEYWORDS        Comma-separated keywords    [default list below]
"""

import os
import pathlib

# ── Project root ──────────────────────────────────────────────────────────────
ROOT_DIR = pathlib.Path(__file__).parent

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_FROM     = os.getenv("ALERT_EMAIL_FROM", "")
EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD", "")   # Gmail App Password
EMAIL_TO_RAW   = os.getenv("ALERT_EMAIL_TO", "")
EMAIL_TO       = [e.strip() for e in EMAIL_TO_RAW.split(",") if e.strip()]

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# ── Schedule ──────────────────────────────────────────────────────────────────
SCHEDULE_TIME = os.getenv("ALERT_SCHEDULE_TIME", "16:00")   # HH:MM, 24h

# ── Keywords ──────────────────────────────────────────────────────────────────
# Tuned for Department of International Health faculty at Johns Hopkins
# Bloomberg School of Public Health — research grants in global health,
# infectious disease, LMIC health systems, and related fields.
_default_keywords = (
    # Fogarty International Center & NIH global health
    "Fogarty International Center,"
    "global health research,"
    "international health research,"
    "low- and middle-income countries,"
    "LMIC health,"
    # Key infectious diseases
    "HIV AIDS global,"
    "tuberculosis global,"
    "malaria elimination,"
    "neglected tropical diseases,"
    "antimicrobial resistance global,"
    "emerging infectious disease global,"
    # Maternal, child & reproductive health
    "maternal mortality,"
    "child survival global,"
    "reproductive health LMIC,"
    "family planning global,"
    "neonatal health,"
    # Nutrition
    "global nutrition,"
    "malnutrition stunting,"
    # Health systems & policy
    "health systems strengthening,"
    "implementation science global,"
    "universal health coverage,"
    "health workforce global,"
    "health financing LMIC,"
    # Epidemiology & surveillance
    "global disease burden,"
    "disease surveillance global,"
    # Cross-cutting
    "global mental health,"
    "climate change health LMIC,"
    "one health zoonotic,"
    "health equity global"
)
KEYWORDS: list[str] = [
    kw.strip()
    for kw in os.getenv("ALERT_KEYWORDS", _default_keywords).split(",")
    if kw.strip()
]

# ── Sources toggle ────────────────────────────────────────────────────────────
# Set any of these env vars to "false" to disable a source.
ENABLED_SOURCES: dict[str, bool] = {
    # Primary sources for JHU International Health faculty
    "nih_guide":       os.getenv("ALERTS_NIH_GUIDE",        "true").lower() != "false",
    "ungm":            os.getenv("ALERTS_UNGM",             "true").lower() != "false",
    "wellcome_leap":   os.getenv("ALERTS_WELLCOME_LEAP",    "true").lower() != "false",
    "grants_gov":      os.getenv("ALERTS_GRANTS_GOV",        "true").lower() != "false",
    "gates":           os.getenv("ALERTS_GATES",             "true").lower() != "false",
    "wellcome":        os.getenv("ALERTS_WELLCOME",          "true").lower() != "false",
    # Secondary sources
    "who":             os.getenv("ALERTS_WHO",               "true").lower() != "false",
    "reliefweb":       os.getenv("ALERTS_RELIEFWEB",         "false").lower() != "false",  # API gone (410)
    "eu_health":       os.getenv("ALERTS_EU_HEALTH",         "true").lower() != "false",
    "simpler_grants":  os.getenv("ALERTS_SIMPLER_GRANTS",    "true").lower() != "false",
    "un_portal":       os.getenv("ALERTS_UN_PORTAL",         "true").lower() != "false",
}

# ── State file (tracks previously seen opportunities) ─────────────────────────
STATE_FILE = ROOT_DIR / "data" / "seen_opportunities.json"

# ── Output file for dashboard JSON ───────────────────────────────────────────
OUTPUT_JSON = ROOT_DIR / "outputs" / "opportunities.json"
