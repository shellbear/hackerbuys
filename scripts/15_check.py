import json,glob,collections,math,re,sys,random
meta={json.loads(l)['id']:json.loads(l) for l in open('analysis/run41k/meta.jsonl')}
T=json.load(open('analysis/run41k/tiers.json'))
ids=set();bad=dup=0;ps=[];hit=collections.Counter();fails=[]
for f in sorted(glob.glob('analysis/run41k/out/*.jsonl')):
    for l in open(f):
        try:d=json.loads(l)
        except: bad+=1;fails.append(f);continue
        if d['id'] not in meta: bad+=1;continue
        if d['id'] in ids: dup+=1;continue
        ids.add(d['id']);hit[meta[d['id']]['tier']]+=1
        for p in d['products']: p['_id']=d['id'];ps.append(p)
print('files',len(glob.glob('analysis/run41k/out/*.jsonl')),'bad',bad,'dup',dup,'comments',len(ids),'products',len(ps))
tot=collections.Counter(m['tier'] for m in meta.values())
print('tier,scanned,hits,rate,pop,est_real_opinions,ci')
E_=0
for t,c in tot.items():
    p=hit[t]/c;e=p*T[t]['pop'];ci=1.96*math.sqrt(p*(1-p)/c)*T[t]['pop'];print(t,c,hit[t],round(100*p,2),T[t]['pop'],round(e),round(ci));E_+=e
print('est total',round(E_))
n=len(ps)
print('stance',collections.Counter(p['stance'] for p in ps),'fh',round(sum(p['first_hand'] for p in ps)/n,3),'ten',round(sum(p['tenure_years'] is not None for p in ps)/n,3),'still',round(sum(p['still_going'] for p in ps)/n,3),'sw',round(sum(bool(p['switched_from']) for p in ps)/n,3),'gen',round(sum(bool(p['generation']) for p in ps)/n,3),'inferred',round(sum(bool(p['generation_inferred']) for p in ps)/n,3))
print('cats',collections.Counter(p['category'] for p in ps).most_common())
print('probe products:',[(p['brand'],p['line'],p['category']) for p in ps if meta[p['_id']]['tier']=='probe'][:60])
print('excl products:',collections.Counter(p['category'] for p in ps if meta[p['_id']]['tier']=='cand_excl').most_common(10))
print('tenure outliers',[(p['brand'],p['line'],p['tenure_years']) for p in ps if p['tenure_years'] is not None and (p['tenure_years']>40 or p['tenure_years']<0)][:15])
