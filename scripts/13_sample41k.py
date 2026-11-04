import duckdb,json,math,os
c=duckdb.connect(); c.sql("set threads=12;set memory_limit='24GB'")
F="'data/derived/funnel.parquet'"
plan=[('thread',"f_thread",10**9),('tenure_own',"f_ten and f_own and not f_thread",10**9),('mycat',"f_mycat and not f_thread and not (f_ten and f_own)",12000),('rec_only',"f_rec and not f_own and not f_mycat and not f_thread",4000),('own_only',"f_own and not f_rec and not f_mycat and not f_ten and not f_thread",3000)]
rows=[];seen=set();meta={}
for t,w,k in plan:
    pop=c.sql(f"select count(*) from {F} where {w}").fetchall()[0][0]
    rs=c.sql(f"""select id,"by",time,root_id,root_title,txt,nkids,sib_pct,sib_k from {F} where {w} and n>=25 order by hash(id||'r41') limit {k}""").fetchall()
    add=0
    for r in rs:
        if r[0] in seen: continue
        seen.add(r[0]);rows.append((t,)+r);add+=1
    meta[t]=dict(pop=pop,n=add);print(t,pop,add,flush=True)
fid="(select id from 'data/derived/funnel.parquet')"
pop=c.sql(f"select count(*) from 'data/derived/cand.parquet' where id not in {fid}").fetchall()[0][0]
for r in c.sql(f"""select id,"by",time,null,null,txt,nkids,null,null from 'data/derived/cand.parquet' where id not in {fid} and n>=25 order by hash(id||'x41') limit 2500""").fetchall():
    rows.append(('cand_excl',)+r);seen.add(r[0])
meta['cand_excl']=dict(pop=pop,n=2500)
# probe: comments that match nothing at all (~39M)
c.sql(r"""create macro clean(t) as regexp_replace(regexp_replace(replace(replace(replace(replace(replace(replace(t,'&#x27;',''''),'&quot;','"'),'&#x2F;','/'),'&gt;','>'),'&lt;','<'),'&amp;','&'),'<p>',' ','g'),'<[^>]+>',' ','g')""")
q=f"""select id,"by",time,null,null,clean(text),len(kids),null,null from read_parquet('data/raw/*.parquet') where type=2 and coalesce(deleted,0)=0 and coalesce(dead,0)=0 and length(text)>=60 and hash(id||'p41')%2000=0 and id not in (select id from 'data/derived/cand.parquet') order by hash(id||'q41') limit 3000"""
pr=c.sql(q).fetchall(); print('probe',len(pr),flush=True)
for r in pr: rows.append(('probe',)+r)
tot=c.sql("select sum(n) from 'data/derived/monthly.parquet'").fetchall()[0][0]; cand=c.sql("select count(*) from 'data/derived/cand.parquet'").fetchall()[0][0]
meta['probe']=dict(pop=int(tot)-cand,n=len(pr))
import random; random.Random(41).shuffle(rows)
BS=500
idx=[]
with open('analysis/run41k/meta.jsonl','w') as m:
  for b in range(0,len(rows),BS):
    with open(f'analysis/run41k/in/b{b//BS:03d}.jsonl','w') as o:
      for r in rows[b:b+BS]:
        o.write(json.dumps(dict(id=r[1],y=r[3].year,thread=r[5],text=(r[6] or '')[:1500]),ensure_ascii=False)+"\n")
        m.write(json.dumps(dict(id=r[1],tier=r[0],by=r[2],time=str(r[3]),root_id=r[4],root_title=r[5],nkids=r[7],sib_pct=r[8],sib_k=r[9]),ensure_ascii=False)+"\n")
    idx.append(b//BS)
json.dump(meta,open('analysis/run41k/tiers.json','w'),indent=1)
print('rows',len(rows),'batches',len(idx),'approx tok',sum(min(len(r[6] or ''),1500) for r in rows)//4,'share of comments',round(100*len(rows)/int(tot),3),'%')
