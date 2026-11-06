#!/usr/bin/env python3
"""Build the queue for one day after the full queue ends, from data/daily/<day>.parquet alone. Thread titles and parent excerpts
for items outside that day come from the ClickHouse demo, then the HN API, so no archive is needed. No LLM.
Same selection and columns as 22_build_queue.py. usage: 30_daily_queue.py 2026-11-04"""
import json, os, sys, tempfile, urllib.request
sys.path.insert(0, "scripts")
import duckdb
import corpus as C
from extract_lib import REFERENCE_OPENING, SHORT_REPLY_CHARS
from queue_sql import CLEAN, daily_candidates

CH = "https://sql-clickhouse.clickhouse.com/?user=demo"
FB = "https://hacker-news.firebaseio.com/v0/item/%d.json"
CHUNK, MAX_DEPTH = 2000, 60
day = sys.argv[1]
src, out = f"data/daily/{day}.parquet", f"{C.DAILY}/{day}.parquet"
c = duckdb.connect()
c.sql("set timezone='UTC'")
c.sql(CLEAN)
c.sql(f"create table cands as {daily_candidates(repr(src))}")
c.sql("delete from cands where n<25")
c.sql(f"create table g as select id,parent,type,title,clean(text) txt from read_parquet('{src}')")


def fetch(ids):
    """Add items that are not in this day's file: ClickHouse first, the HN API for anything it lacks."""
    for k in range(0, len(ids), CHUNK):
        part = ids[k:k + CHUNK]
        req = urllib.request.Request(CH, method="POST", data=f"""SELECT id,parent,CAST(type,'Int8') AS type,title,text FROM hackernews.hackernews
            WHERE id IN ({','.join(map(str, part))}) FORMAT Parquet""".encode())
        with urllib.request.urlopen(req, timeout=120) as r, tempfile.NamedTemporaryFile(suffix=".parquet") as f:
            body = r.read()
            if body:
                f.write(body)
                f.flush()
                c.sql(f"insert into g select id,parent,type,title,clean(text) from read_parquet('{f.name}') where id not in (select id from g)")
    have = {i for (i,) in c.execute("select id from g").fetchall()}
    for i in set(ids) - have:
        with urllib.request.urlopen(FB % i, timeout=30) as r:
            d = json.load(r) or {}
        c.execute("insert into g select ?,?,?,?,clean(?)", [i, d.get("parent"), 2 if d.get("type") == "comment" else 1, d.get("title"), d.get("text")])


def missing(sql):
    return [i for (i,) in c.execute(f"select distinct x from ({sql}) where x is not null and x not in (select id from g)").fetchall()]


# Thread titles: walk each comment up to its story, fetching ancestors that started on an earlier day.
c.sql("create table walk as select id,parent cur from cands")
for _ in range(MAX_DEPTH):
    if need := missing("select cur x from walk"):
        fetch(need)
    c.sql("create or replace table walk as select w.id,case when g.type=2 then g.parent else w.cur end cur,g.type t from walk w left join g on g.id=w.cur")
    if c.sql("select count(*) from walk where t=2").fetchall()[0][0] == 0:
        break
c.sql("create table roots as select w.id,w.cur root_id,g.title thread from walk w left join g on g.id=w.cur")

# Parent excerpts, only for replies that likely depend on them.
c.sql(f"""create table need as select c.id,c.parent from cands c join g on g.id=c.parent
  where g.type=2 and (c.n<{SHORT_REPLY_CHARS} or regexp_matches(c.txt,$${REFERENCE_OPENING.pattern}$$))""")
os.makedirs(C.DAILY, exist_ok=True)
c.sql(f"""copy (
  select row_number() over (order by c.fun desc,hash(c.id)) seq,c.id,c."by",c.time,year(c.time) y,
    case when c.fun then 'funnel' else 'rest' end tier,r.root_id,r.thread,left(p.txt,300) parent,left(c.txt,2500) "text",c.n
  from cands c left join roots r using(id) left join need n2 on n2.id=c.id left join g p on p.id=n2.parent and p.txt is not null
  order by seq) to '{out}' (format parquet,compression zstd)""")
print("wrote", out, c.sql(f"select count(*),count(thread),count(parent) from '{out}'").fetchall()[0])
