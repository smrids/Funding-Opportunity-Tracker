# Funding Opportunity Scanner

A standalone tool that browses multiple funding websites daily and identifies new opportunities, sending email alerts for anything new.

## Sources

| Source | Auth Required | Description |
|--------|--------------|-------------|
| **Grants.gov** | None | US federal grants (REST API) |
| **Simpler Grants.gov** | API key | Newer Grants.gov API with richer metadata |
| **WHO** | None | World Health Organization news & funding pages |
| **Gates Foundation** | None | Grand Challenges open calls (HTML scraping) |
| **Wellcome Trust** | None | Open funding schemes (sitemap parsing) |
| **ReliefWeb** | Appname | Humanitarian funding reports & appeals |
| **EU Funding Portal** | None | EU4Health, Horizon Europe health calls |
| **UN Partner Portal** | Token | UN agency Calls for Expressions of Interest |

## Quick Start

```bash
# 1. Clone / navigate to this directory
cd funding-opportunity-scanner

# 2. Create virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
# Edit .env with your Gmail App Password and recipients

# 5. Test with a dry run (no email sent)
python run.py --dry-run

# 6. Run once immediately
python run.py --now

# 7. Start daily scheduler (default: 4 PM UTC)
python run.py
```

## Usage

```
python run.py [OPTIONS]

Options:
  --now       Run one scan immediately then exit
  --dry-run   Fetch and filter but do NOT send email
  --no-json   Skip saving opportunities.json output
```

## Configuration

All settings via environment variables (or `.env` file):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALERT_EMAIL_FROM` | For email | — | Gmail sender address |
| `ALERT_EMAIL_PASSWORD` | For email | — | Gmail App Password |
| `ALERT_EMAIL_TO` | For email | — | Comma-separated recipients |
| `ALERT_SCHEDULE_TIME` | No | `16:00` | Daily run time (HH:MM, 24h UTC) |
| `ALERT_KEYWORDS` | No | health keywords | Comma-separated search terms |
| `RELIEFWEB_APPNAME` | No | set | Your registered ReliefWeb appname |
| `SIMPLER_GRANTS_API_KEY` | No | — | Simpler Grants.gov API key |
| `UN_PORTAL_TOKEN` | No | — | UN Partner Portal API token |

Disable any source by setting its toggle to `false`:
```
ALERTS_GRANTS_GOV=false
ALERTS_WHO=false
# etc.
```

## Project Structure

```
funding-opportunity-scanner/
├── run.py                  # Entry point with daily scheduler
├── scanner.py              # Main orchestrator
├── config.py               # Configuration (env vars)
├── state.py                # Tracks seen opportunities (dedup)
├── emailer.py              # Gmail SMTP alert sender
├── fetchers/
│   ├── grants_gov.py       # Grants.gov API
│   ├── simpler_grants.py   # Simpler Grants.gov API
│   ├── who.py              # WHO news & funding pages
│   ├── gates.py            # Gates Grand Challenges
│   ├── wellcome.py         # Wellcome Trust sitemap
│   ├── reliefweb.py        # ReliefWeb API
│   ├── eu_health.py        # EU Funding Portal
│   └── un_portal.py        # UN Partner Portal
├── data/
│   └── seen_opportunities.json  # Auto-generated state file
├── outputs/
│   ├── opportunities.json       # Latest scan results
│   └── scanner.log              # Log file
├── requirements.txt
├── .env.example
└── .gitignore
```

## How It Works

1. **Fetch** — Each enabled fetcher queries its source API/website for opportunities matching your keywords
2. **Deduplicate** — New results are checked against `data/seen_opportunities.json` to avoid repeat alerts
3. **Save** — All results are written to `outputs/opportunities.json`
4. **Alert** — New opportunities are emailed as a formatted HTML digest
5. **Schedule** — APScheduler runs the cycle daily at your configured time
