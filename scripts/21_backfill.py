#!/usr/bin/env python3
"""Fetch missing days into data/daily, newest first, staying inside the ClickHouse demo's hourly quota: on a failure it waits and retries.
Safe to stop and rerun. usage: 21_backfill.py 2026-08-22 2026-11-03"""
import os, subprocess, sys, time
sys.path.insert(0, "scripts")
from extract_lib import missing_days

WAIT = 600
MAX_FAILS_PER_DAY = 12  # two hours of retries spans a quota window, so longer means something else is wrong
first, last = sys.argv[1], sys.argv[2]
have = {f[:-8] for f in os.listdir("data/daily") if f.endswith(".parquet")}
for day in missing_days(first, last, have):
    for attempt in range(MAX_FAILS_PER_DAY):
        r = subprocess.run([sys.executable, "scripts/20_fetch_day.py", day], capture_output=True, text=True)
        if r.returncode == 0:
            print(day, r.stdout.strip().splitlines()[-1], flush=True)
            break
        print(day, f"attempt {attempt + 1} failed: {r.stderr.strip().splitlines()[-1][:120]}; waiting {WAIT}s", flush=True)
        time.sleep(WAIT)
    else:
        sys.exit(f"{day} kept failing; rerun later to continue")
print("BACKFILL COMPLETE", flush=True)
