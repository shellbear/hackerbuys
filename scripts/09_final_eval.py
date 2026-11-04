import json,random,collections,math,sys
import duckdb,re
sys.path.insert(0,'scripts')
from lexicon import NEG
S={json.loads(l)['id']:json.loads(l) for l in open('analysis/eval/labels_sonnet.jsonl')}
H={json.loads(l)['id']:json.loads(l) for l in open('analysis/eval/labels_haiku.jsonl')}
D=json.load(open('analysis/eval/sample.json'))
add={6551881,16255721,47725745}; rem={6412614}
ref={r['id']:(S[r['id']]['relevant'] or r['id'] in add) and r['id'] not in rem for r in D}
c=duckdb.connect()
fid={r[0] for r in c.sql("select id from 'data/derived/funnel.parquet'").fetchall()}
pops={'thread':"f_thread",'mycat':"f_mycat and not f_thread",'tenure_own':"f_ten and f_own and not f_mycat and not f_thread",'rec_only':"f_rec and not f_own and not f_mycat and not f_thread",'own_only':"f_own and not f_rec and not f_mycat and not f_ten and not f_thread",'link':"f_link and not f_own and not f_rec and not f_mycat and not f_thread"}
tot=0;var=0;N=0
print('tier,n,rel,prec,pop,est_rel,ci95')
for t,w in pops.items():
    pop=c.sql(f"select count(*) from 'data/derived/funnel.parquet' where {w}").fetchall()[0][0]
    rs=[r for r in D if r['tier']==t and r['id'] in fid]; k=sum(ref[r['id']] for r in rs); p=k/len(rs)
    tot+=p*pop;var+=(pop**2)*p*(1-p)/len(rs);N+=pop
    print(t,len(rs),k,round(p,3),pop,round(p*pop),round(1.96*math.sqrt(p*(1-p)/len(rs)),3))
print('funnel total',N,'est relevant',round(tot),'+-',round(1.96*math.sqrt(var)),'precision',round(tot/N,3))
cp=c.sql("select count(*) from 'data/derived/cand.parquet'").fetchall()[0][0]-N
rs=[r for r in D if r['tier']=='cand_excl' and r['id'] not in fid];k=sum(ref[r['id']] for r in rs);p=k/len(rs)
print('excluded cand',cp,len(rs),k,round(p,3),'est',round(p*cp),'ci',round(1.96*math.sqrt(p*(1-p)/len(rs))*cp))
print(' recall of funnel within cand',round(tot/(tot+p*cp),3),' low/high',round(tot/(tot+(p+1.96*math.sqrt(p*(1-p)/len(rs)))*cp),3),round(tot/(tot+max(p-1.96*math.sqrt(p*(1-p)/len(rs)),0)*cp),3))
for r in D:
    if r['tier']=='cand_excl' and ref[r['id']]: print('  EXCL:',[x['name']+'/'+x['stance'] for x in S[r['id']]['products']],'|',r['text'][:150].replace('\n',' '))
for r in D:
    if r['tier']=='thread_miss' and ref[r['id']]: print('  TMISS:',[x['name'] for x in S[r['id']]['products']])
# accuracy vs reference
for nm,L in [('sonnet',S),('haiku',H)]:
    tp=sum(L[i]['relevant'] and ref[i] for i in ref);fp=sum(L[i]['relevant'] and not ref[i] for i in ref);fn=sum(not L[i]['relevant'] and ref[i] for i in ref)
    print(nm,'prec',round(tp/(tp+fp),3),'rec',round(tp/(tp+fn),3))
    # book-free haiku
books=lambda L,i:any('book' in x['name'].lower() for x in L[i]['products'])
print('haiku book-labelled in sample',sum(books(H,i) for i in H))
# regex neg vs llm neg
neg=re.compile(NEG)
rows=[(any(x['stance']=='negative' for x in S[r['id']]['products']),bool(neg.search(r['text'].lower()))) for r in D if ref[r['id']]]
tp=sum(a and b for a,b in rows);print('regex neg vs sonnet neg: n',len(rows),'tp',tp,'fp',sum(b and not a for a,b in rows),'fn',sum(a and not b for a,b in rows))
print('P1 comment score>0 all time',c.sql("select count(*),sum((score<>0)::int) from 'data/derived/graph.parquet' where type=2").fetchall())
print('cand tok',c.sql("select sum(n)/4/1e6,avg(n) from 'data/derived/cand.parquet'").fetchall())
random.seed(7)
both=[r for r in D if S[r['id']]['relevant'] and H[r['id']]['relevant']];nei=[r for r in D if not S[r['id']]['relevant'] and not H[r['id']]['relevant']]
print('=== AUDIT both relevant')
for r in random.sample(both,20): print(r['id'],[f"{x['name']}/{x['stance']}" for x in S[r['id']]['products']][:2],'|',r['text'][:210].replace('\n',' '))
print('=== AUDIT neither')
for r in random.sample(nei,20): print(r['id'],r['tier'],'|',r['text'][:210].replace('\n',' '))
