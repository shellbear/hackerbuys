#!/usr/bin/env python3
"""Build the extraction queue: candidates ordered newest year first, funnel comments first within each year. No LLM.
Full queue:  22_build_queue.py data/extract/queue.parquet
Test queue:  22_build_queue.py analysis/eval/queue_eval.parquet --ids analysis/eval/sample.json
Rerun at any time: progress is tracked by comment id, so a rebuilt queue never repeats finished comments."""
import argparse, glob, json, os, sys, time
sys.path.insert(0, "scripts")
import duckdb
from extract_lib import REFERENCE_OPENING, SHORT_REPLY_CHARS
from lexicon import CATEGORIES, OWN, REC, RETAIL

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--ids", help="JSON list of objects with id: build only these comments, without excluding scanned ones")
a = ap.parse_args()
t0 = time.time()
os.makedirs(os.path.dirname(a.out), exist_ok=True)
c = duckdb.connect()
c.sql("set threads=12; set memory_limit='24GB'; set preserve_insertion_order=false; set timezone='UTC'")
c.sql(r"""create macro clean(t) as regexp_replace(regexp_replace(replace(replace(replace(replace(replace(replace(t,'&#x27;',''''),'&quot;','"'),'&#x2F;','/'),'&gt;','>'),'&lt;','<'),'&amp;','&'),'<p>',' ','g'),'<[^>]+>',' ','g')""")
c.sql("""create table cands as select id,parent,"by",time,txt,n,(f_mycat or f_own or f_rec or f_link) fun from 'data/derived/cand.parquet'""")
daily = glob.glob("data/daily/*.parquet")
# The archive filter in 01_funnel.py ends where the raw files end; days after that get the same regexes here.
if daily:
    cat_any = "|".join(CATEGORIES.values())
    c.sql(rf"""insert into cands select id,parent,"by",time,txt,length(txt),
       regexp_matches(lt,$${OWN}$$) or regexp_matches(lt,$${REC}$$) or regexp_matches(lt,$${RETAIL}$$) or regexp_matches(lt,$$\bmy (?:\w+ ){{0,3}}(?:{cat_any})s?\b$$)
      from (select *,lower(txt) lt from (select id,parent,"by",time,clean(text) txt from read_parquet('data/daily/*.parquet')
            where type=2 and coalesce(deleted,0)=0 and coalesce(dead,0)=0 and text is not null and "by"<>'' and text<>'[delayed]'))
      where regexp_matches(lt,$$\b(?:{cat_any})s?\b|{RETAIL}$$)""")
if a.ids:
    with open(a.ids) as f:
        ids = [r["id"] for r in json.load(f)]
    c.execute("create table want(id uinteger)")
    c.executemany("insert into want values (?)", [[i] for i in ids])
    c.sql("delete from cands where id not in (select id from want)")
    # Labeled comments may fall outside the current filter, which is exactly what a recall test needs.
    c.sql("""insert into cands select id,parent,"by",time,clean(text),length(clean(text)),false from read_parquet('data/raw/*.parquet')
      where id in (select id from want) and id not in (select id from cands)""")
else:
    c.sql("delete from cands where n<25 or id in (select id from read_json_auto('analysis/run41k/meta.jsonl'))")
print("selected", c.sql("select count(*),sum(fun::int) from cands").fetchall(), f"{time.time()-t0:.0f}s", flush=True)

# Thread titles: walk each comment up to its story.
dsrc = "union all select id,parent,type,title from read_parquet('data/daily/*.parquet')" if daily else ""
c.sql(f"create table g as select id,parent,type,title from 'data/derived/graph.parquet' {dsrc}")
c.sql("create table walk as select id,parent cur from cands")
for _ in range(60):
    c.sql("create or replace table walk as select w.id,case when g.type=2 then g.parent else w.cur end cur,g.type t from walk w left join g on g.id=w.cur")
    if c.sql("select count(*) from walk where t=2").fetchall()[0][0] == 0:
        break
c.sql("create table roots as select w.id,w.cur root_id,g.title thread from walk w left join g on g.id=w.cur")
print("roots", f"{time.time()-t0:.0f}s", flush=True)

# Parent excerpts, only for replies that likely depend on them.
c.sql(f"""create table need as select c.id,c.parent from cands c join g on g.id=c.parent
  where g.type=2 and (c.n<{SHORT_REPLY_CHARS} or regexp_matches(c.txt,$${REFERENCE_OPENING.pattern}$$))""")
srcs = "['data/raw/*.parquet'" + (",'data/daily/*.parquet'" if daily else "") + "]"
c.sql(f"""create table ptext as select id pid,left(clean(text),300) parent_text from read_parquet({srcs}, union_by_name=true)
  where id in (select parent from need) and text is not null""")
print("parents", c.sql("select count(*) from need").fetchall()[0][0], f"{time.time()-t0:.0f}s", flush=True)

c.sql(f"""copy (
  select row_number() over (order by year(c.time) desc,c.fun desc,hash(c.id)) seq,c.id,c."by",c.time,year(c.time) y,
    case when c.fun then 'funnel' else 'rest' end tier,r.root_id,r.thread,p.parent_text parent,left(c.txt,2500) "text",c.n
  from cands c left join roots r using(id) left join need n2 on n2.id=c.id left join ptext p on p.pid=n2.parent
  order by seq) to '{a.out}' (format parquet,compression zstd)""")
print("wrote", a.out, c.sql(f"select count(*),count(thread),count(parent),sum(length(text)),sum(length(parent)),min(time),max(time) from '{a.out}'").fetchall(), f"{time.time()-t0:.0f}s")
