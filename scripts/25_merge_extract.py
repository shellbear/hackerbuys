#!/usr/bin/env python3
"""Join results with comment metadata. Result folders are in priority order: the first to process a comment owns it.
Writes one row per product, plus the comments scanned per year that rising and fading tags need as denominators.
usage: 25_merge_extract.py data/extract/queue.parquet data/extract/merged extract/out [more folders]"""
import json, os, sys
sys.path.insert(0, "scripts")
import duckdb
import extract_lib as L

queue, out, dirs = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(out, exist_ok=True)
sources = [list(L.iter_results(d)) for d in dirs]
wanted = {r["id"] for docs in sources for doc in docs for r in doc["results"]}
c = duckdb.connect()
text = {i: t for i, t in c.execute(f"""select id,"text" from read_parquet('{queue}')""").fetchall() if i in wanted}
rows, seen = L.flatten(sources, text)
tmp = os.path.join(out, "mentions.jsonl")
with open(tmp, "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
c.execute("create table seen(id uinteger)")
c.executemany("insert into seen values (?)", [[i] for i in seen]) if len(seen) < 50000 else c.sql("insert into seen select unnest(?)", params=[list(seen)])
c.sql(f"""copy (select m.*,q."by",q.time,q.y,q.tier,q.root_id,q.thread from read_json_auto('{tmp}') m left join read_parquet('{queue}') q using(id))
  to '{out}/mentions.parquet' (format parquet,compression zstd)""")
c.sql(f"""copy (select q.y,count(*) n from read_parquet('{queue}') q join seen using(id) group by 1 order by 1) to '{out}/scanned_by_year.parquet' (format parquet)""")
os.remove(tmp)
print(f"{len(rows)} product mentions from {len(seen)} comments; quotes verified {sum(r['quote_ok'] for r in rows)}/{len(rows)}")
