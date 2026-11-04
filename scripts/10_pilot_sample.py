import duckdb,json
c=duckdb.connect()
CATS="chairs desks monitors keyboards mice_trackpads headphones laptops phones tablets_ereaders kitchen_coffee home_appliances tools_edc".split()
PER=150; seen=set(); rows=[]
for cat in CATS:
    q=f"""select id,"by",year(time) y,root_title,txt,f_thread,f_ten,f_mycat,nkids,sib_pct,sib_k from 'data/derived/funnel.parquet'
      where cat_{cat} and (f_thread or f_mycat or (f_ten and f_own) or (f_rec and f_own)) and n between 40 and 1500
      order by (case when f_thread then 0 when f_ten then 1 else 2 end), hash(id||'pilot') limit {PER*3}"""
    got=[r for r in c.sql(q).fetchall() if r[0] not in seen]
    # half highest-signal, half from general ownership language to avoid only Ask HN threads
    a=got[:PER//2]; b=sorted(got[PER//2:],key=lambda r:hash(str(r[0])))[:PER-len(a)]
    for r in a+b:
        seen.add(r[0]); rows.append(dict(id=r[0],by=r[1],y=r[2],title=r[3],text=r[4],sample_cat=cat,thread=r[5],nkids=r[8],sib_pct=r[9],sib_k=r[10]))
    print(cat,len(a)+len(b))
rows.sort(key=lambda r:hash(str(r['id'])))
json.dump(rows,open('analysis/pilot/sample.json','w'))
n=len(rows); k=n//3+1
for i in range(3):
    with open(f'analysis/pilot/in_{i}.jsonl','w') as o:
        for j,r in enumerate(rows[i*k:(i+1)*k]): o.write(json.dumps(dict(i=j,id=r['id'],thread=r['title'],text=r['text']),ensure_ascii=False)+"\n")
print(n,sum(len(r['text']) for r in rows)//4,'tok')
