#!/usr/bin/env python3
"""Trace a benchmark of known products through the pipeline to find where each is lost. Read-only, no LLM.
Stages: mentioned on HN -> passes the filter -> processed -> extracted as that product -> on the site.
usage: 28_coverage.py [analysis/benchmark_products.tsv] [output.tsv]"""
import collections as C
import csv
import json
import re
import sys

sys.path.insert(0, "scripts")
import duckdb
import extract_lib as L

src = sys.argv[1] if len(sys.argv) > 1 else "analysis/benchmark_products.tsv"
dest = sys.argv[2] if len(sys.argv) > 2 else "analysis/benchmark_coverage.tsv"
with open(src) as f:
    bench = list(csv.DictReader(f, delimiter="\t"))
# Whole words only: "oura" must not match "encouraged".
for b in bench:
    b["pattern"] = rf"\b(?:{b['pattern']})\b"
union = "|".join(f"(?:{b['pattern']})" for b in bench)
c = duckdb.connect()
c.sql("set threads=6; set memory_limit='14GB'; set timezone='UTC'")
c.execute(
    """create table hits as select id,year(time) y,lower(text) t from read_parquet(['data/raw/*.parquet','data/daily/*.parquet'],union_by_name=true)
    where type=2 and coalesce(deleted,0)=0 and coalesce(dead,0)=0 and text is not null and regexp_matches(lower(text),?)""",
    [union],
)
rows = c.execute("select id,y,t from hits").fetchall()
print("comments mentioning any benchmark product", len(rows), flush=True)
queued = {r[0] for r in c.execute("select id from read_parquet('data/extract/queue.parquet')").fetchall()}
cand = {r[0] for r in c.execute("select id from 'data/derived/cand.parquet'").fetchall()}
done = L.load_done("extract/out")
extracted = C.defaultdict(list)
for d in L.iter_results("extract/out"):
    for r in d["results"]:
        for p in r["products"]:
            extracted[r["id"]].append(" ".join(str(p.get(k) or "") for k in ("brand", "line", "model")).lower())
sample = set()
for line in open("analysis/run41k/meta.jsonl"):
    sample.add(json.loads(line)["id"])
sample_products = C.defaultdict(list)
import glob
for path in glob.glob("analysis/run41k/out/*.jsonl"):
    for line in open(path):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        for p in d["products"]:
            sample_products[d["id"]].append(" ".join(str(p.get(k) or "") for k in ("brand", "line", "model")).lower())
with open("site/data/index.json") as f:
    site = json.load(f)["products"]
out = []
for b in bench:
    rx = re.compile(b["pattern"])
    ids = [(i, y) for i, y, t in rows if rx.search(t)]
    n = len(ids)
    in_filter = sum(i in cand or i in queued or i in sample for i, _ in ids)
    processed = sum(i in done or i in sample for i, _ in ids)
    found = sum(any(rx.search(x) for x in extracted.get(i, []) + sample_products.get(i, [])) for i, _ in ids)
    recent = sum(y >= 2025 for _, y in ids)
    pages = sorted(((p["n"], p["own"]) for p in site if rx.search(p["n"].lower())), key=lambda x: -x[1])
    out.append(dict(category=b["category"], product=b["product"], mentions=n, since_2025=recent, in_filter=in_filter, processed=processed, extracted=found, site_pages=len(pages), top_page=pages[0][0] if pages else "", top_owners=pages[0][1] if pages else 0))
with open(dest, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]), delimiter="\t")
    w.writeheader()
    w.writerows(out)
print("wrote", dest)
