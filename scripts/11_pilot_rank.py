import json,re,glob,collections,math
S={r['id']:r for r in json.load(open('analysis/pilot/sample.json'))}
ALIAS={'hp':'HP','ibm':'IBM','lg':'LG','apple':'Apple'}
def norm(p):
    b=p['brand'].strip();m=p['model'].strip()
    bl=b.lower();ml=m.lower()
    if ml.startswith(bl+' '): ml=ml[len(bl)+1:]
    ml=re.sub(r'\b(20\d\d|\d{2}[- ]?inch|\d{2}"|gen ?\d+|\d+(st|nd|rd|th) gen(eration)?|original|old|new)\b','',ml).strip(' ,()-')
    if bl in('lenovo','ibm') and 'thinkpad' in ml: bl='thinkpad'; ml=ml.replace('thinkpad','').strip()
    if bl=='thinkpad':
        if re.search(r'x1',ml): ml='x1 carbon'
        elif re.match(r't\d',ml): ml='t-series'
        elif re.match(r'x\d',ml): ml='x-series'
        elif re.match(r'[pwe]\d',ml): ml=ml[0]+'-series'
    if bl=='apple' or bl=='':
        for k,v in [('macbook pro','macbook pro'),('mbp','macbook pro'),('macbook air','macbook air'),('macbook','macbook'),('airpods pro','airpods pro'),('airpods max','airpods max'),('airpods','airpods'),('iphone se','iphone se'),('iphone','iphone'),('ipad pro','ipad pro'),('ipad','ipad'),('magic trackpad','magic trackpad'),('trackpad','magic trackpad'),('magic mouse','magic mouse'),('magic keyboard','magic keyboard'),('watch','watch')]:
            if k in ml: ml=v;break
    if bl=='herman miller':
        for k in ('aeron','embody','mirra','sayl'):
            if k in ml: ml=k
    if bl=='steelcase':
        for k in ('leap','gesture','amia','think'):
            if k in ml: ml=k
    if bl=='sony' and re.search(r'1000x?m|xm\d',ml): ml='wh-1000xm'
    if bl=='bose' and re.search(r'qc|quiet',ml): ml='quietcomfort'
    if bl in('logitech','logi') and 'mx master' in ml: ml='mx master'
    if bl=='google' and re.match(r'pixel',ml): ml='pixel'
    if bl=='google' and re.match(r'nexus',ml): ml='nexus'
    if bl=='amazon' and 'kindle' in ml: bl='kindle';ml='paperwhite' if 'paperwhite' in ml else ''
    if bl=='kindle' and 'paperwhite' in ml: ml='paperwhite'
    if bl=='kobo': ml=''
    if bl=='samsung' and re.search(r'galaxy s|\bs\d',ml): ml='galaxy s'
    if bl=='dell' and 'xps' in ml: ml='xps'
    if bl=='roomba' or (bl=='irobot'): bl='irobot';ml='roomba'
    return (b.strip() if bl==b.lower() else bl.title())+(' '+ml if ml else '')
ms=[]
for f in sorted(glob.glob('analysis/pilot/out_*.jsonl')):
    for l in open(f):
        d=json.loads(l)
        for p in d['products']:
            p=dict(p);p['id']=d['id'];p['by']=S[d['id']]['by'];p['y']=S[d['id']]['y'];p['name']=norm(p);ms.append(p)
print('comments labeled',len(S),'qualifying',len({m['id'] for m in ms}),'product mentions',len(ms),'distinct names',len({m['name'].lower() for m in ms}))
print('stance',collections.Counter(m['stance'] for m in ms),'first_hand',sum(m['first_hand'] for m in ms),'tenure',sum(m['tenure_years'] is not None for m in ms),'still_going',sum(m['still_going'] for m in ms))
P=collections.defaultdict(lambda:collections.defaultdict(dict))
for m in ms: P[m['name'].lower()][m['by']]=m if not P[m['name'].lower()].get(m['by']) or m['stance']!='neutral' else P[m['name'].lower()][m['by']]
disp={m['name'].lower():m['name'] for m in ms}
cats=collections.defaultdict(collections.Counter)
for m in ms: cats[m['name'].lower()][m['category']]+=1
def wilson(p,n,z=1.64):
    if n==0: return 0
    f=p/n;return (f+z*z/(2*n)-z*math.sqrt(f*(1-f)/n+z*z/(4*n*n)))/(1+z*z/n)
rows=[]
for k,au in P.items():
    v=list(au.values());pos=sum(a['stance'] in('recommend','positive') for a in v);neg=sum(a['stance']=='negative' for a in v)
    ten=[a['tenure_years'] for a in v if a['tenure_years'] is not None and a['stance']!='negative']
    rows.append(dict(name=disp[k],cat=cats[k].most_common(1)[0][0],n=len(v),pos=pos,neg=neg,neu=len(v)-pos-neg,fh=sum(a['first_hand'] for a in v),w=wilson(pos,pos+neg),lh=sum(1 for t in ten if t>=3),maxt=max(ten) if ten else None,sg=sum(a['still_going'] for a in v)))
json.dump(rows,open('analysis/pilot/ranking.json','w'),indent=0)
print('\n=== PER CATEGORY: score = positive - negative authors')
for c in "chairs desks monitors keyboards mice_trackpads headphones laptops phones tablets_ereaders kitchen_coffee home_appliances tools_edc".split():
    t=sorted([r for r in rows if r['cat']==c],key=lambda r:(-(r['pos']-r['neg']),-r['n']))[:6]
    print(f"{c} ({sum(r['n'] for r in rows if r['cat']==c)} author-mentions):")
    for r in t: print(f"   {r['name'][:32]:32} n={r['n']:<3} +{r['pos']} -{r['neg']} ={r['neu']} fh={r['fh']} 3y+={r['lh']} maxY={r['maxt']}")
print('\n=== LONG-HAUL (positive owners 3+ years)')
for r in sorted(rows,key=lambda r:-r['lh'])[:15]: print(f"  {r['name'][:32]:32} {r['cat'][:12]:12} 3y+={r['lh']} still={r['sg']} maxY={r['maxt']} +{r['pos']} -{r['neg']}")
print('\n=== MOST NEGATIVE (n>=5)')
for r in sorted([r for r in rows if r['n']>=5],key=lambda r:-(r['neg']/r['n']))[:10]: print(f"  {r['name'][:32]:32} n={r['n']} +{r['pos']} -{r['neg']}")
print('\n=== MOST LOVED (n>=5, by Wilson)')
for r in sorted([r for r in rows if r['n']>=5],key=lambda r:-r['w'])[:10]: print(f"  {r['name'][:32]:32} n={r['n']} +{r['pos']} -{r['neg']} wilson={r['w']:.2f}")
print('\nsingletons',sum(1 for r in rows if r['n']==1),'of',len(rows))
