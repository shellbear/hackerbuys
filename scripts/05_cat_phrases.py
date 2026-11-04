import duckdb,re,collections
c=duckdb.connect()
cols=[r[0] for r in c.sql("describe select * from 'data/derived/funnel.parquet'").fetchall() if r[0].startswith('cat_')]
pat=re.compile(r"\b((?:[A-Z][\w&'+-]*)(?:[ -](?:[A-Z0-9][\w&'+.-]*)){0,3})")
STOP=set("i the this it my we they you if but and so for in on a an that there what when he she also not with have one at is as to of or just yes no how".split())
for k in cols:
    a=collections.defaultdict(set)
    for by,t in c.sql(f"select \"by\",txt from 'data/derived/funnel.parquet' where {k} and (f_mycat or f_thread or (f_own and f_rec) or f_ten)").fetchall():
        seen=set()
        for m in pat.finditer(t):
            p=m.group(1).lower().rstrip(".,'-")
            if p in STOP or p.split()[0] in STOP or len(p)<3: continue
            a[p].add(by)
    top=sorted(a.items(),key=lambda x:-len(x[1]))[:45]
    print(k[4:],':',', '.join(f"{p}({len(v)})" for p,v in top))
