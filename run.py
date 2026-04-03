"""
run.py — Funding Opportunity Scanner
======================================
Entry point with a daily scheduler (default: 4 PM UTC).

QUICK START
-----------
1. Copy .env.example → .env and fill in credentials:
       cp .env.example .env

2. Create/activate a virtual environment:
       python3 -m venv .venv && source .venv/bin/activate

3. Install dependencies:
       pip install -r requirements.txt

4. Test with a dry-run (no email sent):
       python run.py --dry-run

5. Run once immediately (sends real email):
       python run.py --now

6. Start the daily scheduler (runs at ALERT_SCHEDULE_TIME, default 4 PM):
       python run.py
"""

import argparse
import logging
import sys
from pathlib import Path

# ── Load .env if present ───────────────────────────────────────────────────────
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
        print(f"Loaded environment from {_env_file}")
    except ImportError:
        pass   # python-dotenv optional; user can source .env manually

# ── Logging ────────────────────────────────────────────────────────────────────
Path(__file__).parent.joinpath("outputs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent / "outputs" / "scanner.log",
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger("run")

# ── Import scanner AFTER env vars are loaded ───────────────────────────────────
from scanner import run
from config import SCHEDULE_TIME


def _scheduler_loop(dry_run: bool) -> None:
    """Run via APScheduler — fires once daily at SCHEDULE_TIME."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.error(
            "APScheduler is not installed. "
            "Run: pip install apscheduler  or use `--now` for a one-shot run."
        )
        sys.exit(1)

    hour, minute = SCHEDULE_TIME.split(":")
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: run(dry_run=dry_run),
        trigger=CronTrigger(hour=int(hour), minute=int(minute)),
        id="funding_scanner",
        name="Funding Opportunity Scanner",
        replace_existing=True,
    )
    log.info(
        "Scheduler started — will run daily at %s UTC. Press Ctrl+C to stop.",
        SCHEDULE_TIME,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Funding Opportunity Scanner — Daily Funding Alert Agent"
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run one scan immediately then exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and filter but do NOT send any email.",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Skip saving opportunities.json output.",
    )
    args = parser.parse_args()

    save_json = not args.no_json

    if args.now or args.dry_run:
        log.info("Running one-shot scan (dry_run=%s, save_json=%s)…", args.dry_run, save_json)
        count = run(dry_run=args.dry_run, save_json=save_json)
        log.info("Done — %d new opportunities found.", count)
    else:
        _scheduler_loop(dry_run=False)


if __name__ == "__main__":
    main()
