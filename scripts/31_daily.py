#!/usr/bin/env python3
"""Scheduled update, runnable from a plain checkout: fetch each day after the last one covered, queue it, extract every pending
daily comment, then rebuild the site. Committing is left to the caller (.github/workflows/daily.yml).
Extraction uses the Claude Code CLI, so it needs a logged-in `claude` or CLAUDE_CODE_OAUTH_TOKEN. A usage limit stops extraction
early; the comments left over are picked up by the next run.
usage: 31_daily.py [--lag 2] [--max-days 7] [--workers 4] [--no-extract] [--no-site]"""
import argparse, datetime as dt, glob, subprocess, sys
sys.path.insert(0, "scripts")
import corpus as C

ap = argparse.ArgumentParser()
ap.add_argument("--lag", type=int, default=2, help="leave the newest days alone until they are this many days old, so they are complete")
ap.add_argument("--max-days", type=int, default=7, help="fetch at most this many days per run; the ClickHouse demo has an hourly quota")
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--no-extract", action="store_true")
ap.add_argument("--no-site", action="store_true")
a = ap.parse_args()


def run(*cmd):
    print("+", " ".join(cmd), flush=True)
    subprocess.run([sys.executable, *cmd], check=True)


until = str(dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=a.lag))
days = C.days_after(C.last_day(), until)[:a.max_days]
print("days to add:", days or "none", flush=True)
for day in days:
    run("scripts/20_fetch_day.py", day)
    run("scripts/30_daily_queue.py", day)
if not a.no_extract and glob.glob(f"{C.DAILY}/*.parquet"):
    run("scripts/23_extract.py", "--queue", f"{C.DAILY}/*.parquet", "--adapter", "claude", "--model", "claude-haiku-5-5", "--effort", "low",
        "--workers", str(a.workers))
if not a.no_site:
    run("scripts/14_build_site.py")
