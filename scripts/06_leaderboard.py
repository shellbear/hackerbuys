import duckdb,sys,time,math,json
sys.path.insert(0,'scripts')
from products import P
from lexicon import OWN,TENURE
POS=r"\b(?:love|loved|great|excellent|amazing|fantastic|awesome|best|recommend|recommended|happy with|favorite|favourite|worth|solid|perfect|swear by|game[- ]?changer|still (?:going|works|working|use|running)|no regrets|bulletproof|indestructible|superb|wonderful)\b"
NEG=r"\b(?:avoid|hate|hated|regret|returned|sent (?:it|them) back|junk|crap|shit|garbage|broke|broken|died|stopped working|fell apart|waste of money|terrible|awful|disappointed|disappointing|overpriced|don'?t buy|do not buy|worst|sucks|unreliable|failed)\b"
c=duckdb.connect('data/derived/work.duckdb'); c.sql("set threads=12;set memory_limit='24GB'")
# Base: all candidates with enrichment if in funnel
c.sql("""create or replace temp table b as select c.id,c."by" a,c.time,lower(c.txt) lt,c.nkids,c.f_own,c.f_ten,c.f_mycat,f.f_thread,f.sib_pct,f.sib_k,f.root_score
 from 'data/derived/cand.parquet' c left join 'data/derived/funnel.parquet' f using(id)""")
c.sql("create or replace table pm(product varchar,cat varchar,id uinteger,a varchar,y int,own bool,ten bool,thread bool,top bool,nkids int,pol int)")
t=time.time();n=0
for cat,ps in P.items():
  for name,rx in ps.items():
    win=rf"[^.!?]{{0,160}}(?:{rx})[^.!?]{{0,160}}"
    c.execute(rf"""insert into pm with h as (select *,regexp_extract_all(lt,$${win}$$) w from b where regexp_matches(lt,$${rx}$$)),
     s as (select *,list_aggregate(w,'string_agg',' ') wt from h)
     select ?,?,id,a,year(time),coalesce(f_own,false) or coalesce(f_mycat,false),coalesce(f_ten,false),coalesce(f_thread,false),
       coalesce(sib_pct>=.8 and sib_k>=5,false),nkids,
       case when regexp_matches(wt,$${POS}$$) and not regexp_matches(wt,$${NEG}$$) then 1 when regexp_matches(wt,$${NEG}$$) and not regexp_matches(wt,$${POS}$$) then -1 else 0 end from s""",[name,cat]); n+=1
print('scan',n,time.time()-t,c.sql("select count(*) from pm").fetchall())
c.sql("copy pm to 'data/derived/product_mentions.parquet' (format parquet)")
