import duckdb,re,sys,collections
sys.path.insert(0,'scripts')
from products import P
c=duckdb.connect('data/derived/work.duckdb',read_only=True)
EX="product not in ('ThinkPad (all)','Kindle (all)')"
print("=== share of category author-mentions by era (top 5, % of named products in that era)")
for cat in "chairs keyboards headphones laptops tablets_ereaders mice_trackpads monitors phones home_appliances kitchen_coffee".split():
    print(cat)
    for lo,hi in [(2010,2015),(2016,2020),(2021,2023),(2024,2026)]:
        r=c.sql(f"""select product,count(distinct a) n from pm where cat='{cat}' and {EX} and y between {lo} and {hi} group by 1 order by n desc""").fetchall()
        t=sum(x[1] for x in r) or 1
        print(f"  {lo}-{hi}: "+", ".join(f"{p} {100*n//t}%" for p,n in r[:5]))
print("\n=== last active: lifetime authors>=150, share of authors in 2024-26 vs lifetime")
print(c.sql(f"""select product,cat,count(distinct a) life,count(distinct case when y>=2024 then a end) recent,round(100.0*count(distinct case when y>=2024 then a end)/count(distinct a),1) pct,
 max(case when y>=2024 then 1 else 0 end) from pm where {EX} group by 1,2 having count(distinct a)>=150 order by pct asc limit 22""").df()[['product','cat','life','recent','pct']].to_string())
# from->to edges
rx={n:re.compile(v) for cat,ps in P.items() for n,v in ps.items() if n not in('ThinkPad (all)','Kindle (all)')}
cat_of={n:cat for cat,ps in P.items() for n in ps}
sw=re.compile(r"\b(?:switched|moved|upgraded|migrated|went|changed|came|replaced)\b[^.!?]{0,20}?\bfrom\b([^.!?]{1,70}?)\bto\b([^.!?]{1,70})|\breplaced (?:my |an? |the |our )([^.!?]{1,50}?) with ([^.!?]{1,50})")
rows=c.sql("""select "by",year(time),lower(txt) from 'data/derived/cand.parquet' where regexp_matches(lower(txt),'(switched|moved|upgraded|migrated|went|changed|came) [^.!?]{0,20}from|replaced (my|an?|the|our) ')""").fetchall()
print('comments w/ switch phrase',len(rows))
E_=collections.defaultdict(set);ok=0
for a,y,t in rows:
    for m in sw.finditer(t):
        fr,to=(m.group(1),m.group(2)) if m.group(1) else (m.group(3),m.group(4))
        fs=[n for n,r in rx.items() if r.search(fr)];ts=[n for n,r in rx.items() if r.search(to)]
        for f in fs:
            for g in ts:
                if f!=g and cat_of[f]==cat_of[g]: E_[(f,g)].add(a);ok+=1
print('edges',ok)
pairs=sorted(E_.items(),key=lambda x:-len(x[1]))
print("=== top from -> to (distinct authors) with reverse count")
for (f,g),s in pairs[:30]: print(f"  {f} -> {g}: {len(s)}  (reverse {len(E_.get((g,f),()))})")
net=collections.Counter()
for (f,g),s in E_.items(): net[g]+=len(s);net[f]-=len(s)
print('net gain',net.most_common(10));print('net loss',net.most_common()[-10:])
