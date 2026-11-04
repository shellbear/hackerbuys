"""Funnel = strong signal rows from cand. Attach root story, depth, sibling rank percentile."""
import duckdb,sys,time
sys.path.insert(0,'scripts')
from lexicon import THREAD
glob=sys.argv[1] if len(sys.argv)>1 else 'data/raw/*.parquet'
c=duckdb.connect('data/derived/work.duckdb'); c.sql("set memory_limit='24GB'; set threads=12; set preserve_insertion_order=false")
t=time.time()
c.sql("create or replace table cand as select * from 'data/derived/cand.parquet' where f_mycat or f_own or f_rec or f_link")
print('funnel rows',c.sql("select count(*) from cand").fetchall(),flush=True)
c.sql("create or replace table g as select id,parent,type,title,score,descendants from 'data/derived/graph.parquet'")
c.sql("create or replace table walk as select id,parent cur,1 depth from cand")
for i in range(40):
    c.sql("""create or replace table walk as
      select w.id,case when g.type=2 then g.parent else w.cur end cur,w.depth+(g.type=2)::int depth,g.type t
      from walk w left join g on g.id=w.cur""")
    n=c.sql("select count(*) from walk where t=2").fetchall()[0][0]
    print(i,n,flush=True)
    if n==0: break
c.sql(f"""create or replace table sib as
 select unnest(kids) kid,generate_subscripts(kids,1) pos,len(kids) k from read_parquet('{glob}') where len(kids)>=2""")
c.sql(rf"""copy (
 select f.*,w.cur root_id,w.depth,r.title root_title,r.score root_score,r.descendants root_desc,s.pos sib_pos,s.k sib_k,
   case when s.k is null then null when s.k=1 then 0.5 else 1-(s.pos-1.0)/(s.k-1) end sib_pct,
   coalesce(regexp_matches(r.title,$${THREAD}$$),false) f_thread
 from cand f join walk w using(id) left join g r on r.id=w.cur left join sib s on s.kid=f.id
) to 'data/derived/funnel.parquet' (format parquet,compression zstd)""")
print('ok',time.time()-t)
