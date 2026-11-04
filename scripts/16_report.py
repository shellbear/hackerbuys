import json,collections,re,random,glob
d=json.load(open('site/data/index.json'))['products']
print('own>=3',sum(p['own']>=3 for p in d),'>=10',sum(p['own']>=10 for p in d),'>=25',sum(p['own']>=25 for p in d),'single',sum(p['nc']==1 for p in d),'of',len(d),'blank',sum(not p['n'] for p in d))
R=[p for p in d if not p['bo']]
for c in "chairs desks monitors keyboards mice_trackpads headphones laptops phones tablets_ereaders kitchen_coffee home_appliances".split():
    t=sorted([p for p in R if p['c']==c and p['own']>=5],key=lambda p:-p['w'])[:6]
    print(c,'|',', '.join(f"{p['n']} {p['own']} (+{p['pos']}/-{p['neg']})" for p in t))
print('LONG',', '.join(f"{p['n']} {p['lh']} (max {p['maxt']}y)" for p in sorted(R,key=lambda p:-p['lh'])[:16]))
print('RECENT',', '.join(f"{p['n']} {p['rown']} (+{p['rpos']}/-{p['rneg']})" for p in sorted([p for p in R if p['rown']>=8],key=lambda p:-p['rw'])[:14]))
print('WORST',', '.join(f"{p['n']} {p['own']} (+{p['pos']}/-{p['neg']})" for p in sorted([p for p in R if p['own']>=15],key=lambda p:p['w'])[:10]))
for k in ['apple-macbook-pro','apple-macbook-air','dell-xps-13','google-pixel','apple-iphone']:
    x=json.load(open(f'site/data/p/{k}.json'));print(k,x['gens'][:14]);print('  to',[(a[0],a[2],a[3]) for a in x['to'][:5]],'from',[(a[0],a[2],a[3]) for a in x['fr'][:5]])
mv=collections.Counter()
for f in glob.glob('site/data/p/*.json'):
    x=json.load(open(f))
    for a in x['to']:
        if a[2]>=4: mv[(x['n'],a[0],a[2],a[3])]=a[2]-a[3]
print('MOVES',[k for k,_ in mv.most_common(22)])
x=json.load(open('site/data/p/apple-macbook-pro.json'))
for yrs,lab in (({'2016','2017','2018','2019'},'2016-19'),({'M1 era','M2 era','M3 era','M4 era'},'M-series')):
    cs=[c for c in x['cs'] if c['g'] in yrs and c['s']=='negative'];print(lab,'neg',len(cs),'keyboard mention',sum(bool(re.search(r'keyboard|butterfly',c['t'].lower())) for c in cs),'touch bar',sum('touch bar' in c['t'].lower() or 'touchbar' in c['t'].lower() for c in cs))
# audit
meta={json.loads(l)['id']:json.loads(l) for l in open('analysis/run41k/meta.jsonl')}
T={}
for f in glob.glob('analysis/run41k/in/*.jsonl'):
    for l in open(f):
        j=json.loads(l);T[j['id']]=j['text']
O=[json.loads(l) for f in glob.glob('analysis/run41k/out/*.jsonl') for l in open(f)]
random.seed(11)
for o in random.sample(O,28):
    print('-',meta[o['id']]['tier'],[f"{p['brand']} {p['line']}|{p['model']}|{p['stance']}|fh={int(p['first_hand'])}|t={p['tenure_years']}" for p in o['products']][:3],'\n    ',T[o['id']][:240].replace('\n',' '))
