import duckdb,json
c=duckdb.connect(); c.sql("select setseed(0.42)")
F="'data/derived/funnel.parquet'"
tiers={
 'thread':"f_thread",
 'mycat':"f_mycat and not f_thread",
 'tenure_own':"f_ten and f_own and not f_mycat and not f_thread",
 'rec_only':"f_rec and not f_own and not f_mycat and not f_thread",
 'own_only':"f_own and not f_rec and not f_mycat and not f_ten and not f_thread",
 'link':"f_link and not f_own and not f_rec and not f_mycat and not f_thread",
}
rows=[]
for t,w in tiers.items():
    pop=c.sql(f"select count(*) from {F} where {w}").fetchall()[0][0]
    for r in c.sql(f"select id,root_title,txt from {F} where {w} and n<2500 order by hash(id||'s1') limit 50").fetchall():
        rows.append(dict(id=r[0],tier=t,pop=pop,title=r[1],text=r[2]))
    print(t,pop)
# recall set A: excluded candidates (category word but no signal)
c.sql("create temp table fid as select id from "+F)
pop=c.sql("select count(*) from 'data/derived/cand.parquet' where id not in (select id from fid)").fetchall()[0][0]
print('cand_excl',pop)
for r in c.sql("select id,txt from 'data/derived/cand.parquet' where id not in (select id from fid) and n<2500 order by hash(id||'s2') limit 50").fetchall():
    rows.append(dict(id=r[0],tier='cand_excl',pop=pop,title=None,text=r[1]))
# recall set B: comments in hardware-rec threads that never matched the lexicon at all (top-level)
c.sql("""create temp table hw as select id,title from 'data/derived/graph.parquet' where type=1 and regexp_matches(lower(title),'^(ask|tell) hn.*(office chair|desk chair|good desk|standing desk|headphones|keyboards|mattress|purchases|purchase|bought|buy it for life|gift|best-designed|accessories|laptop for|good laptop|monitors?)')""")
print('hw threads',c.sql("select count(*) from hw").fetchall())
q="""select g.id,h.title,replace(replace(replace(r.text,'&#x27;',''''),'&quot;','"'),'<p>',' ') t from 'data/derived/graph.parquet' g join hw h on g.parent=h.id
  join read_parquet('data/raw/*.parquet') r on r.id=g.id
  where g.type=2 and coalesce(g.deleted,0)=0 and coalesce(g.dead,0)=0 and g.id not in (select id from fid) and length(r.text)<2500"""
c.sql("create temp table b as "+q)
pop=c.sql("select count(*) from b").fetchall()[0][0]; print('thread_miss',pop)
for r in c.sql("select * from b order by hash(id||'s3') limit 50").fetchall():
    rows.append(dict(id=r[0],tier='thread_miss',pop=pop,title=r[1],text=r[2]))
tot=c.sql("select count(*) from 'data/derived/cand.parquet'").fetchall()
rows.sort(key=lambda r:hash(str(r['id'])))
json.dump(rows,open('analysis/eval/sample.json','w'),indent=0)
open('analysis/eval/sample_for_label.jsonl','w').write("\n".join(json.dumps(dict(id=r['id'],thread_title=r['title'],comment=r['text'])) for r in rows))
print(len(rows),sum(len(r['text']) for r in rows)//4,'tok')
