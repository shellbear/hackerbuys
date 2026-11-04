import json,collections
S={json.loads(l)['id']:json.loads(l) for l in open('analysis/eval/labels_sonnet.jsonl')}
H={json.loads(l)['id']:json.loads(l) for l in open('analysis/eval/labels_haiku.jsonl')}
D=json.load(open('analysis/eval/sample.json'))
tiers=collections.defaultdict(lambda:[0,0,0,0,0])
dis=[]
for r in D:
    i=r['id'];s,h=S[i]['relevant'],H[i]['relevant']
    t=tiers[r['tier']];t[0]+=1;t[1]+=s;t[2]+=h;t[3]+=(s==h);t[4]=r['pop']
    if s!=h: dis.append(r)
print('tier n sonnet_rel haiku_rel agree pop')
for k,v in tiers.items(): print(k,v)
print('agreement',sum(S[r['id']]['relevant']==H[r['id']]['relevant'] for r in D)/len(D),'n disagreements',len(dis))
a=sum(S[r['id']]['relevant'] and H[r['id']]['relevant'] for r in D);print('both relevant',a)
# stance agreement on same comment when both relevant and one product each
st=[(S[r['id']]['products'][0]['stance'],H[r['id']]['products'][0]['stance']) for r in D if S[r['id']]['relevant'] and H[r['id']]['relevant']]
print('first-product stance agree',sum(x==y for x,y in st)/len(st),collections.Counter(st).most_common(8))
c=collections.Counter(p['stance'] for v in S.values() for p in v['products']);print('sonnet stances',c)
print('first_hand',collections.Counter(p['first_hand'] for v in S.values() for p in v['products']),'tenure',sum(p['tenure_years'] is not None for v in S.values() for p in v['products']))
print('cats',collections.Counter(p['category'] for v in S.values() for p in v['products']).most_common())
print('prods/comment',sum(len(v['products']) for v in S.values())/max(1,sum(v['relevant'] for v in S.values())))
json.dump([dict(id=r['id'],tier=r['tier'],title=r['title'],text=r['text'][:600],sonnet=S[r['id']]['products'],haiku=H[r['id']]['products']) for r in dis],open('analysis/eval/disagreements.json','w'))
for r in dis:
    print('\n#',r['id'],r['tier'],'S' if S[r['id']]['relevant'] else 'H',[p['name'] for p in (S[r['id']]['products'] or H[r['id']]['products'])][:3]);print((r['title'] or '')[:60],'|',r['text'][:320].replace('\n',' '))
