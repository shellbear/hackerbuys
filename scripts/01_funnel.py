"""Scan all comments, flag signals, keep funnel rows + graph + monthly denominators. Usage: 01_funnel.py [glob]"""
import duckdb,sys,time,os
sys.path.insert(0,'scripts')
from lexicon import *
glob=sys.argv[1] if len(sys.argv)>1 else 'data/raw/*.parquet'
os.makedirs('data/derived',exist_ok=True)
c=duckdb.connect(); c.sql("set memory_limit='24GB'; set threads=12; set preserve_insertion_order=false")
c.sql(r"""create macro clean(t) as regexp_replace(regexp_replace(replace(replace(replace(replace(replace(replace(t,'&#x27;',''''),'&quot;','"'),'&#x2F;','/'),'&gt;','>'),'&lt;','<'),'&amp;','&'),'<p>',' ','g'),'<[^>]+>',' ','g')""")
cat_cases=",\n".join(f"regexp_matches(lt, $$\\b(?:{v})s?\\b$$) as cat_{k}" for k,v in CATEGORIES.items())
cat_any="|".join(CATEGORIES.values())
t=time.time()
# 1. graph over everything (no text) for root resolution and kids-order tests
c.sql(f"""copy (select id,parent,type,"by",time,score,len(kids) nkids,title,descendants,deleted,dead from read_parquet('{glob}'))
 to 'data/derived/graph.parquet' (format parquet, compression zstd)""")
print('graph',time.time()-t,flush=True)
# 2. monthly denominators + flags
c.sql(rf"""copy (
 with base as (
  select id,parent,"by",time,len(kids) nkids,clean(text) txt from read_parquet('{glob}')
  where type=2 and coalesce(deleted,0)=0 and coalesce(dead,0)=0 and text is not null and "by"<>''
 ), l as (select *,lower(txt) lt from base),
 f as (select id,parent,"by",time,nkids,txt,length(txt) n,
   regexp_matches(lt,$${OWN}$$) f_own, regexp_matches(lt,$${REC}$$) f_rec,
   regexp_matches(lt,$${TENURE}$$) f_ten, regexp_matches(lt,$${NEG}$$) f_neg,
   regexp_matches(lt,$${RETAIL}$$) f_link,
   regexp_matches(lt,$$\bmy (?:\w+ ){{0,3}}(?:{cat_any})s?\b$$) f_mycat,
   {cat_cases}
  from l where regexp_matches(lt,$$\b(?:{cat_any})s?\b|{RETAIL}$$))
 select * from f) to 'data/derived/cand.parquet' (format parquet, compression zstd)""")
print('cand',time.time()-t,flush=True)
c.sql(f"""copy (select date_trunc('month',time) m,count(*) n,sum(length(text)) chars from read_parquet('{glob}')
 where type=2 and coalesce(deleted,0)=0 and coalesce(dead,0)=0 group by 1) to 'data/derived/monthly.parquet' (format parquet)""")
print('done',time.time()-t)
