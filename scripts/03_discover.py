"""Data-driven product discovery: capitalized noun phrases after first-person ownership verbs -> distinct authors."""
import duckdb,re,collections,sys
c=duckdb.connect()
rows=c.sql("select \"by\",txt from 'data/derived/funnel.parquet'").fetchall()
pat=re.compile(r"\b(?:[Mm]y|bought|purchased|recommend|love|using|use|got|own|swear by|switched to|upgraded to|Get|get)\s+(?:a |an |the |some |old |new |current |trusty |beloved |ancient |first |second )*((?:[A-Z][\w&'+.-]*|\d+[A-Za-z]+)(?:[ -](?:[A-Z0-9][\w&'+.-]*)){0,3})")
auth=collections.defaultdict(set)
for by,t in rows:
    for m in pat.finditer(t):
        k=m.group(1).strip(" .,'-").lower()
        if 2<len(k)<40: auth[k].add(by)
out=sorted(((len(v),k) for k,v in auth.items()),reverse=True)
open('analysis/discovered_phrases.tsv','w').write("\n".join(f"{n}\t{k}" for n,k in out if n>=5))
print(len(auth),sum(1 for n,_ in out if n>=2),sum(1 for n,_ in out if n>=5),sum(1 for n,_ in out if n>=20))
print(out[:150])
