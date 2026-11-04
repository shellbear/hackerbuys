#!/usr/bin/env python3
"""Show extraction progress: overall, by year, spend and recent pace. Read-only, uses no credits. usage: 26_progress.py"""
import glob, json, os, sys, time
sys.path.insert(0, "scripts")
import duckdb
import extract_lib as L

OUT, QUEUE = "extract/out", "data/extract/queue.parquet"
done = L.load_done(OUT)
years = {}
for i, y in duckdb.sql(f"select id,y from '{QUEUE}'").fetchall():
    d = years.setdefault(y, [0, 0])
    d[0] += 1
    d[1] += i in done
total, finished = sum(v[0] for v in years.values()), sum(v[1] for v in years.values())
docs = list(L.iter_results(OUT))
spent = sum(d.get("spent", 0) for d in docs)
print(f"Overall: {finished:,} of {total:,} comments ({finished / total:.1%}), about {spent:.1f} credits in saved batches")
for y in sorted(years, reverse=True):
    n, k = years[y]
    print(f"  {y}: {k / n:6.1%}  {k:>8,} of {n:,}")
    if k == 0:
        print("  older years not started")
        break
now = time.time()
recent = [f for f in glob.glob(f"{OUT}/*.json") if now - os.path.getmtime(f) < 1800]
if recent:
    rate = len(recent) * 50 / 0.5
    print(f"Last 30 min: {len(recent)} batches, about {rate:,.0f} comments an hour; {(total - finished) / rate:,.0f} hours left for the whole queue at this pace")
else:
    print("Last 30 min: no batches saved")
