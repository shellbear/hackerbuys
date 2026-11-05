#!/usr/bin/env python3
"""Pick a random sample of comments the keyword filter rejected that mention a discovered product name and carry an opinion signal.
Writes their ids for 22_build_queue.py --ids and prints how many such comments exist. No LLM.
usage: 27_recall_sample.py analysis/eval/recall_ids.json [sample size]"""
import collections
import csv
import json
import sys

sys.path.insert(0, "scripts")
import duckdb
import extract_lib as L
import recall_names as R
from lexicon import OWN, REC

out, size = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 500
SCAN_SHARE = 50  # scan 1 comment in 50, which is plenty to estimate and sample from
with open("/usr/share/dict/words") as f:
    english = {w.strip().lower() for w in f}
english |= {w + "s" for w in english}
multi, single = R.collect(L.iter_results("extract/out"))
multis, singles = R.clean_names(collections.Counter(multi), collections.Counter(single), english)
print("names", len(multis), len(singles))
esc = lambda t: t.replace(".", "[.]").replace("+", "[+]")
# Curated benchmark names cover products the filter under-counts and ones not yet seen in extraction.
benchmark = []
for path in ("analysis/benchmark_products.tsv", "analysis/benchmark_external.tsv"):
    with open(path) as f:
        benchmark += [row["pattern"] for row in csv.DictReader(f, delimiter="\t")]
rx_lower = r"\b(?:" + "|".join(esc(t) for t in sorted(multis, key=len, reverse=True)) + "|" + "|".join(f"(?:{p})" for p in benchmark) + r")\b|" + R.NICKNAMES
rx_case = r"\b(?:" + "|".join(esc(t) for t in sorted(singles, key=len, reverse=True)) + r")\b"
c = duckdb.connect()
c.sql("set threads=6; set memory_limit='14GB'; set timezone='UTC'")
c.sql(r"""create macro clean(t) as regexp_replace(regexp_replace(replace(replace(replace(replace(replace(replace(t,'&#x27;',''''),'&quot;','"'),'&#x2F;','/'),'&gt;','>'),'&lt;','<'),'&amp;','&'),'<p>',' ','g'),'<[^>]+>',' ','g')""")
c.execute(
    f"""create table s as select id,clean(text) txt from read_parquet('data/raw/*.parquet')
    where type=2 and coalesce(deleted,0)=0 and coalesce(dead,0)=0 and text is not null and "by"<>''
      and hash(id||'recall')%{SCAN_SHARE}=0 and length(text)>=25
      and id not in (select id from 'data/derived/cand.parquet')"""
)
total = c.execute("select count(*) from s").fetchall()[0][0]
c.execute("create table h as select id,txt from s where regexp_matches(lower(txt),?) or regexp_matches(txt,?)", [rx_lower, rx_case])
named = c.execute("select count(*) from h").fetchall()[0][0]
signal = f"regexp_matches(lower(txt),$${OWN}$$) or regexp_matches(lower(txt),$${REC}$$)"
ids = [r[0] for r in c.execute(f"select id from h where {signal} order by hash(id||'pick')").fetchall()]
print(f"scanned {total:,} rejected comments; {named:,} name a product ({named * SCAN_SHARE:,} overall); {len(ids):,} also have a signal ({len(ids) * SCAN_SHARE:,} overall)")
with open(out, "w") as f:
    json.dump([{"id": i} for i in ids[:size]], f)
print("wrote", min(size, len(ids)), "ids to", out)
