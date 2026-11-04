#!/usr/bin/env python3
"""Fetch one UTC day of HN items from the ClickHouse public demo into data/daily/<day>.parquet,
in the same schema as data/raw. Pages by id (the demo caps results at 10,000 rows per query) and
re-fetches placeholder comments from the official HN API.
usage: 20_fetch_day.py 2026-11-01"""
import concurrent.futures as cf, datetime as dt, json, os, pathlib, sys, tempfile, urllib.parse, urllib.request
import duckdb

CH = "https://sql-clickhouse.clickhouse.com/?user=demo"
FB = "https://hacker-news.firebaseio.com/v0/item/%d.json"
PAGE = 5000
PLACEHOLDER = "[delayed]"
COLS = """id,deleted,CAST(type,'Int8') AS type,by,time,text,dead,parent,poll,kids,url,score,title,parts,descendants,words"""

def ch(sql):
    req = urllib.request.Request(CH, data=sql.encode(), method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def fb(i):
    with urllib.request.urlopen(FB % i, timeout=30) as r:
        return json.load(r)

day = dt.date.fromisoformat(sys.argv[1])
end = day + dt.timedelta(days=1)
out = pathlib.Path(f"data/daily/{day}.parquet")
out.parent.mkdir(parents=True, exist_ok=True)
where = f"time>=toDateTime('{day} 00:00:00','UTC') AND time<toDateTime('{end} 00:00:00','UTC')"

with tempfile.TemporaryDirectory() as tmp:
    last, n, pages = 0, 0, 0
    while True:
        p = os.path.join(tmp, f"{pages:05}.parquet")
        body = ch(f"SELECT {COLS} FROM hackernews.hackernews WHERE {where} AND id>{last} ORDER BY id LIMIT {PAGE} FORMAT Parquet")
        if not body:
            break
        open(p, "wb").write(body)
        got, mx = duckdb.sql(f"select count(*),max(id) from read_parquet('{p}')").fetchall()[0]
        if not got:
            os.remove(p)
            break
        n += got; last = mx; pages += 1
        if got < PAGE:
            break
    print(f"fetched {n} items in {pages} pages")

    c = duckdb.connect()
    c.execute("set timezone='UTC'")
    c.execute(f"""create table t as select id::uinteger id,deleted::utinyint deleted,type::tinyint type,"by"::varchar "by",
      (time::timestamp at time zone 'UTC') time,text::varchar text,dead::utinyint dead,parent::uinteger parent,poll::uinteger poll,
      kids::uinteger[] kids,url::varchar url,score::integer score,title::varchar title,parts::uinteger[] parts,
      descendants::integer descendants,words::varchar[] words from read_parquet('{tmp}/*.parquet')""")

    ids = [r[0] for r in c.execute("select id from t where text=?", [PLACEHOLDER]).fetchall()]
    fixed = 0
    with cf.ThreadPoolExecutor(8) as ex:
        for i, item in zip(ids, ex.map(fb, ids)):
            txt = (item or {}).get("text")
            if txt and txt != PLACEHOLDER:
                c.execute("update t set text=? where id=?", [txt, i]); fixed += 1
    print(f"placeholders: {len(ids)}, repaired from HN API: {fixed}")
    c.execute(f"copy (select * from t order by id) to '{out}' (format parquet, compression zstd)")
print(f"wrote {out} ({out.stat().st_size/1e6:.1f} MB)")
