"""Build static site JSON from the run41k sample plus the extraction pipeline's results in extract/out.
Needs data/extract/queue.parquet for comment text. Counts cover scanned comments, not all of HN."""
import json,glob,re,math,collections,os,shutil,sys
sys.path.insert(0,'scripts')
import duckdb
import extract_lib as L
import site_render as SR
import datetime as dt
MAX_COMMENTS,MAX_TEXT,MIN_PAGE_OWNERS=30,1500,2
QUEUE,OUT='data/extract/queue.parquet','extract/out'
R='analysis/run41k'
text={};meta={}
for f in glob.glob(f'{R}/in/*.jsonl'):
    for l in open(f):
        d=json.loads(l);text[d['id']]=d
for l in open(f'{R}/meta.jsonl'):
    d=json.loads(l);meta[d['id']]=d
BRAND={'ibm':'lenovo','mac':'apple','hewlett packard':'hp','hewlett-packard':'hp','logi':'logitech','google/lg':'google','amazon kindle':'amazon','irobot roomba':'irobot','hag':'håg','hermanmiller':'herman miller','hm':'herman miller','microsoft surface':'microsoft'}
LINE_RULES=[ # (brand regex, line regex, canonical brand, canonical line)
 (r'.',r'^ergodox|^ergo dox','zsa','ErgoDox'),(r'ergodox',r'.*','zsa','ErgoDox'),(r'unicomp',r'.*','ibm/unicomp','Model M'),(r'.',r'^(hhkb|happy hacking)','pfu','HHKB'),(r'happy hacking|hhkb|^pfu',r'.*','pfu','HHKB'),
 (r'microsoft',r'^natural','microsoft','Natural Ergonomic Keyboard'),(r'microsoft',r'sculpt','microsoft','Sculpt Ergonomic'),(r'microsoft',r'^ergonomic keyboard','microsoft','Natural Ergonomic Keyboard'),(r'kinesis',r'freestyle','kinesis','Freestyle'),
 (r'sony',r'1000x','sony','WH-1000XM'),(r'sony',r'^mdr','sony','MDR'),(r'sennheiser',r'^hd ?6[05]0','sennheiser','HD 600/650'),(r'sennheiser',r'^hd ?25\b','sennheiser','HD 25'),(r'sennheiser',r'^hd ?280','sennheiser','HD 280'),(r'sennheiser',r'^momentum','sennheiser','Momentum'),(r'beyerdynamic',r'dt ?770','beyerdynamic','DT 770'),(r'beyerdynamic',r'dt ?990','beyerdynamic','DT 990'),(r'beyerdynamic',r'dt ?880','beyerdynamic','DT 880'),(r'audio.?technica',r'm50','audio-technica','ATH-M50'),(r'bose',r'noise cancel|^nc ?700|^700','bose','Noise Cancelling 700'),
 (r'.',r'^geek ?desk','geekdesk','GeekDesk'),(r'geek ?desk',r'.*','geekdesk','GeekDesk'),(r'jarvis|^fully',r'.*','fully','Jarvis'),(r'.',r'^jarvis','fully','Jarvis'),(r'uplift',r'.*','uplift','Desk'),(r'flexispot|autonomous',r'.*','flexispot/autonomous','Standing desk'),(r'ergotron',r'workfit|sit','ergotron','WorkFit'),(r'ergotron',r'.*','ergotron','Monitor arm'),(r'ikea',r'standing|crank|skarsta|bekant|idasen|mechanical','ikea','Standing desk'),
 (r'herman',r'^leap','steelcase','Leap'),(r'herman',r'^mira','herman miller','Mirra'),(r'h.g|varier|stokke',r'capisco','håg','Capisco'),(r'secretlab',r'.*','secretlab','Chair'),(r'ikea',r'markus','ikea','Markus'),(r'humanscale',r'freedom','humanscale','Freedom'),
 (r'lg',r'oled|^c\d|^cx','lg','OLED'),(r'lg',r'ultrafine','lg','UltraFine'),(r'lg',r'ultrawide','lg','UltraWide'),(r'apple',r'cinema|thunderbolt display','apple','Cinema / Thunderbolt Display'),(r'apple',r'pro display','apple','Pro Display XDR'),(r'samsung',r'odyssey','samsung','Odyssey'),(r'dell',r'^p24|^p27|^u24|^u27|^u30|^u32|^up\d','dell','UltraSharp'),
 (r'synology',r'.*','synology','NAS'),(r'ubiquiti|unifi',r'edge','ubiquiti','EdgeRouter'),(r'ubiquiti|unifi',r'.*','ubiquiti','UniFi'),(r'mikrotik',r'.*','mikrotik','Routers'),
 (r'remarkable',r'.*','remarkable','reMarkable'),(r'.',r'^remarkable','remarkable','reMarkable'),(r'oneplus',r'^oneplus$|^$','oneplus','OnePlus'),(r'fairphone',r'.*','fairphone','Fairphone'),(r'system76',r'.*','system76','System76'),(r'garmin',r'.*','garmin','Garmin'),(r'fitbit',r'.*','fitbit','Fitbit'),(r'sonos',r'.*','sonos','Sonos'),(r'das keyboard',r'.*','das keyboard','Das Keyboard'),(r'^meta$|oculus',r'quest','meta','Quest'),
 (r'.',r'^(macbook pro|mbp)\b','apple','MacBook Pro'),(r'.',r'^(macbook air|mba)\b','apple','MacBook Air'),(r'apple',r'^macbook\b','apple','MacBook'),
 (r'.',r'thinkpad.*\bx1\b|^x1 carbon|^x1\b','lenovo','ThinkPad X1'),(r'.',r'thinkpad ?\bt\d*|^t\d{2,3}s?$','lenovo','ThinkPad T-series'),(r'.',r'thinkpad ?\bx\d*','lenovo','ThinkPad X-series'),(r'.',r'thinkpad ?\bp\d*','lenovo','ThinkPad P-series'),(r'.',r'^thinkpad','lenovo','ThinkPad'),
 (r'.',r'^aeron','herman miller','Aeron'),(r'.',r'^embody','herman miller','Embody'),(r'herman',r'^mirra','herman miller','Mirra'),(r'steelcase',r'^leap','steelcase','Leap'),(r'steelcase',r'^gesture','steelcase','Gesture'),
 (r'apple',r'^airpods pro','apple','AirPods Pro'),(r'apple',r'^airpods max','apple','AirPods Max'),(r'apple',r'^airpods','apple','AirPods'),(r'apple',r'^iphone se','apple','iPhone SE'),(r'apple',r'^iphone','apple','iPhone'),(r'apple',r'^ipad pro','apple','iPad Pro'),(r'apple',r'^ipad air','apple','iPad Air'),(r'apple',r'^ipad mini','apple','iPad mini'),(r'apple',r'^ipad','apple','iPad'),(r'apple',r'^mac ?mini','apple','Mac mini'),(r'apple',r'^mac studio','apple','Mac Studio'),(r'apple',r'^(magic )?trackpad','apple','Magic Trackpad'),(r'apple',r'magic mouse','apple','Magic Mouse'),(r'apple',r'watch','apple','Watch'),
 (r'.',r'^(kindle )?paperwhite|kindle paperwhite','amazon','Kindle Paperwhite'),(r'.',r'^kindle','amazon','Kindle'),(r'kindle',r'^$','amazon','Kindle'),
 (r'dell',r'^xps ?13','dell','XPS 13'),(r'dell',r'^xps','dell','XPS'),(r'dell',r'ultrasharp','dell','UltraSharp'),
 (r'sony',r'1000x?m|^xm\d','sony','WH-1000XM'),(r'bose',r'^(qc|quiet ?comfort)','bose','QuietComfort'),(r'logitech',r'^mx master','logitech','MX Master'),(r'logitech',r'^mx ergo','logitech','MX Ergo'),(r'logitech',r'^mx keys','logitech','MX Keys'),
 (r'google',r'^pixel','google','Pixel'),(r'google',r'^nexus','google','Nexus'),(r'samsung',r'^galaxy s\d*','samsung','Galaxy S'),
 (r'kinesis',r'advantage|^$','kinesis','Advantage'),(r'.',r'^ergodox','zsa','ErgoDox'),(r'zsa',r'moonlander','zsa','Moonlander'),(r'ibm|unicomp|lenovo',r'^model m','ibm/unicomp','Model M'),(r'.',r'^(hhkb|happy hacking)','pfu','HHKB'),
 (r'.',r'^aeropress','aeropress','AeroPress'),(r'aeropress',r'^$','aeropress','AeroPress'),(r'.',r'^roomba','irobot','Roomba'),(r'irobot',r'^$','irobot','Roomba'),(r'raspberry',r'.','raspberry pi','Raspberry Pi'),(r'.',r'^raspberry pi','raspberry pi','Raspberry Pi'),(r'.',r'^instant ?pot','instant pot','Instant Pot'),(r'instant',r'^$','instant pot','Instant Pot'),(r'zojirushi',r'rice|neuro|induction','zojirushi','Rice cooker'),(r'philips',r'hue','philips','Hue'),
 (r'creality',r'^ender','creality','Ender'),(r'prusa',r'.*','prusa','Prusa'),(r'apple',r'^tv\b','apple','TV'),(r'qnap',r'.','qnap','NAS'),
 (r'.',r'^steam deck','valve','Steam Deck'),(r'framework',r'.','framework','Laptop'),(r'kobo',r'.*','kobo','Kobo'),(r'rakuten',r'kobo','kobo','Kobo'),(r'leatherman',r'.*','leatherman','Leatherman'),
]
LINE_RULES=[(re.compile(a),re.compile(b),c,d) for a,b,c,d in LINE_RULES]
BN={'geekdesk':'','fully':'Fully','uplift':'Uplift','flexispot/autonomous':'FlexiSpot / Autonomous','ergotron':'Ergotron','ikea':'IKEA','håg':'HÅG','humanscale':'Humanscale','secretlab':'Secretlab','remarkable':'','oneplus':'OnePlus','fairphone':'','system76':'','garmin':'','fitbit':'','sonos':'','das keyboard':'','microsoft':'Microsoft','sennheiser':'Sennheiser','beyerdynamic':'Beyerdynamic','audio-technica':'Audio-Technica','lg':'LG','synology':'Synology','ubiquiti':'Ubiquiti','mikrotik':'MikroTik','meta':'Meta','apple':'Apple','lenovo':'Lenovo','herman miller':'Herman Miller','steelcase':'Steelcase','amazon':'Amazon','dell':'Dell','sony':'Sony','bose':'Bose','logitech':'Logitech','google':'Google','samsung':'Samsung','kinesis':'Kinesis','zsa':'ZSA','ibm/unicomp':'IBM / Unicomp','pfu':'PFU','aeropress':'','irobot':'iRobot','raspberry pi':'','instant pot':'','zojirushi':'Zojirushi','philips':'Philips','valve':'Valve','framework':'Framework','kobo':'','leatherman':'','creality':'Creality','prusa':'','qnap':'QNAP'}
# Categories were fixed before extraction; these refine them from brand and line without another LLM pass.
RECAT=[(re.compile(r,re.I),c) for r,c in [
 (r'\bmac ?mini|\bimac\b|\bmac ?pro\b|mac studio|power ?mac|\bnuc\b|minisforum|beelink|lenovo tiny|thinkcentre|optiplex','desktops'),
 (r'radeon|geforce|\brtx\b|\bgtx\b|ryzen|threadripper|\bcore i\d|intel arc|nvidia gpu|phenom|\bxeon|\bepyc','gpus_cpus'),
 (r'synology|qnap|truenas|drobo|\bssd\b|seagate|samsung 8\d0|ocz vertex|x25-m|western digital|\bnas\b','storage'),
 (r'\bquest\b|oculus|\bvive\b|valve index|vision pro|hololens|xreal|viture|ray-ban meta','vr_ar'),
 (r'apple tv|\bapple tv\b|chromecast(?! audio)|\broku\b|fire tv|nvidia shield|lg oled|bravia|\bvizio\b|sceptre|plasma tv|samsung (smart )?tv|google tv','tv_streaming'),
 (r'\bnest\b|philips hue|\bhue\b|amazon echo|google home|homepod|ikea smart|ecobee|echo show|facebook portal|meta portal','smart_home'),
 (r'roomba|roborock|robovac|\bdyson\b|miele vacuum|numatic','cleaning'),
 (r'creality|\bprusa|bambu|\bender\b|makerbot|markforged|flashforge|zortrax|tevo|alfawise','printers_3d'),
 (r'blue (yeti|snowball)|samson (go|c01)|logitech (c9|brio|conference)|shure sm|\brode\b|elgato|focusrite|scarlett|atem mini|audient','webcams_mics'),
 (r'\banker\b|ecoflow|mophie|caldigit|magsafe|lightning|belkin|portapow|jackery|\bcharger','power'),
 (r'\bhp[- ]?(\d\d[a-z]{1,2}\b|41|48|35|28|16|prime)|\bti-(\d|nspire)|casio(?!.*watch).*(fx|calculator|prizm)|numworks|swissmicro','calculators'),
]]
TOPICS=[(re.compile(r,re.I),t) for r,t in [
 (r'\bipod|\bzune|\bfiio\b|\bsansa\b','music_players'),
 (r'laserjet|scansnap|\bbrother\b|\bepson\b|imageclass|canon inkjet|pixma','printers_scanners'),
 (r'arturia|\bkorg\b|yamaha (reface|np)|\bnovation\b|\bfender\b|kawai|qunexus|m-audio|peavey|marshall jcm|teenage engineering|\bmoog\b','instruments'),
 (r'wacom|huion|gaomon|xp-pen','drawing_tablets'),
 (r'yubikey|airtag|\btile\b|flipper|nitrokey|solokey','security_trackers'),
 (r'amiga|trs-80|\bdec (alpha|vt)|commodore|palm pilot','vintage'),
 (r'rigol|mitutoyo|hakko|pinecil|ts100|\bfluke\b|gw instek|siglent','test_gear'),
 (r'washlet|tushy|bidet','bidets'),
]]
EREADER=re.compile(r'kindle|kobo|remarkable|boox|digital paper|\bnook\b|supernote|e-?ink|pocketbook|sony reader|daylight computer',re.I)
CONSOLE=re.compile(r'steam deck|nintendo|xbox|playstation|rog ally|game boy|steam controller|steam link',re.I)
def recat(cat,brand,line):
    t=f"{brand or ''} {line or ''}"
    for r,c in RECAT:
        if r.search(t): return c
    if cat=='tablets_ereaders':
        return 'tablets' if re.search(r'kindle fire',t,re.I) or not EREADER.search(t) else 'ereaders'
    if CONSOLE.search(t): return 'consoles'
    return cat
def topic(brand,line):
    t=f"{brand or ''} {line or ''}"
    for r,x in TOPICS:
        if r.search(t): return x
    return None
def canon(b,l):
    b=(b or '').strip().lower();b=BRAND.get(b,b);l=(l or '').strip();ll=l.lower()
    if b and ll.startswith(b+' '): ll=ll[len(b)+1:];l=l[len(b)+1:]
    if ll==b: ll='';l=''
    for rb,rl,cb,cl in LINE_RULES:
        if rb.search(b) and rl.search(ll): return cb,cl
    return b,l
def norm_key(cb,cl): return re.sub(r'[^a-z0-9]+','-',f'{cb} {cl}'.lower()).strip('-')
def display(cb,cl,rawb):
    n=BN.get(cb,rawb or cb.title())
    if not cl: return n or rawb or cb.title()
    if n and cl.lower().startswith(n.lower()): return cl
    return (n+' '+cl).strip()
def parse_free(s):
    s=(s or '').strip()
    if not s: return None
    parts=s.split(' ',1)
    a=canon(parts[0],parts[1] if len(parts)>1 else '')
    b=canon('',s)
    return b if b[0] else a
ms=[];bad=0
def add_products(cid,products,M):
    for p in products:
        if not L.keep_mention(p): continue
        cb,cl=canon(p.get('brand'),p.get('line'))
        if not cl and p.get('model'): cb,cl=canon(p.get('brand'),p.get('model'))
        p=dict(p,category=recat(p.get('category'),p.get('brand'),p.get('line')),topic=topic(p.get('brand'),p.get('line')))
        ms.append(dict(p,id=cid,by=M['by'],time=M['time'][:10],y=int(M['time'][:4]),tier=M['tier'],root=M['root_id'],title=M['root_title'],cb=cb,cl=cl,key=norm_key(cb,cl),disp=display(cb,cl,(p.get('brand') or '').strip())))
for f in sorted(glob.glob(f'{R}/out/*.jsonl')):
    for l in open(f):
        try:d=json.loads(l)
        except: bad+=1;continue
        if d['id'] not in meta: bad+=1;continue
        add_products(d['id'],d['products'],meta[d['id']])
docs=list(L.iter_results(OUT))
done=L.load_done(OUT)
con=duckdb.connect();con.execute("set timezone='UTC'")
counts=collections.defaultdict(lambda:[0,0])
for i,by,t,y,tier,root,thread,txt in con.execute(f"""select id,"by",time,y,tier,root_id,thread,"text" from read_parquet('{QUEUE}')""").fetchall():
    counts[y][0]+=1
    if i in done:
        counts[y][1]+=1
        meta[i]=dict(by=by,time=str(t),tier=tier,root_id=root,root_title=thread)
        text[i]=dict(text=txt)
FULL=L.full_years({y:tuple(v) for y,v in counts.items()})
TRENDS=L.trends_ready(FULL)
for d in docs:
    for r in d['results']:
        if r['id'] in meta: add_products(r['id'],r['products'],meta[r['id']])
print('mentions',len(ms),'bad lines',bad,'comments',len({m['id'] for m in ms}))
G=collections.defaultdict(list)
for m in ms: G[m['key']].append(m)
names={k:collections.Counter(x['disp'] for x in v).most_common(1)[0][0] for k,v in G.items()}
brand_lines=collections.defaultdict(set)
for k,v in G.items():
    if v[0]['cl']: brand_lines[v[0]['cb']].add(k)
def wilson(p,n,z=1.64):
    if n==0: return 0.0
    f=p/n;return (f+z*z/(2*n)-z*math.sqrt(f*(1-f)/n+z*z/(4*n*n)))/(1+z*z/n)
def gen_label(m):
    g=(m.get('generation') or '').strip()
    if g:
        x=re.search(r'\bM[1-5]\b',g)
        if x: return x.group(0)+' era'
        x=re.search(r'\b(19|20)\d\d\b',g)
        if x: return x.group(0)
        return g[:28]
    return ''
moved=collections.defaultdict(lambda:collections.defaultdict(set))
for m in ms:
    pf=parse_free(m.get('switched_from'))
    if pf:
        k=norm_key(*pf)
        if k in G and k!=m['key']: moved[k][m['key']].add(m['by']) 
LAST=2026
YEARS=collections.Counter(int(x['time'][:4]) for x in meta.values())
def rate(v,a,b):
    n=sum(a<=x['y']<=b for x in v);d=sum(c for y,c in YEARS.items() if a<=y<=b)
    return n,(n/d if d else 0)
def same_line(a,b):
    return a==b or a.startswith(b+'-') or b.startswith(a+'-')
def calc_tags(e,v,k,by_ten,gl):
    """Each tag comes with the reason shown on the product page."""
    T={};pos,neg=e['pos'],e['neg'];nv=pos+neg
    n5=sum(t>=5 for t in by_ten.values())
    if n5>=3 and nv>=5 and neg/nv<=.2: T['bifl']=f"{n5} owners happy after 5+ years, {neg} of {nv} verdicts negative"
    if nv>=10 and .4<=pos/nv<=.6: T['divisive']=f"{pos} positive and {neg} negative"
    rn,rr=rate(v,2024,LAST);pn,pr=rate(v,2019,2023);old=sum(x['y']<2019 for x in v);nc=len(v)
    # Rates compare years, which is only fair once every year in the window is fully scanned.
    if TRENDS:
        if rn>=5 and rr>=1.5*max(pr,1e-9) and pn>0: T['rising']=f"{rn} mentions since 2024, {rr/pr:.1f}× the 2019–23 rate for the same sampled volume"
        elif rn>=5 and pn==0: T['rising']=f"{rn} mentions since 2024, none in 2019–23"
        if nc>=8 and pn>=5 and rr<=.4*pr: T['fading']=f"{rn} mention{'s' if rn!=1 else ''} since 2024 against {pn} in 2019–23, after adjusting for sampled volume"
        if nc>=8 and rn<=max(1,.1*nc) and old>=.6*nc: T['dated']=f"{old} of {nc} mentions are from before 2019, {rn} since 2024"
        if 'dated' in T: T.pop('fading',None)
    inn={f for f in moved if k in moved[f] and not same_line(f,k)}
    i=sum(len(moved[f][k]) for f in inn);o=sum(len(s) for t,s in moved[k].items() if not same_line(t,k))
    if i>=3 and i>=2*max(o,1): T['switch']=f"{i} owners came from other products, {o} left for one"
    bad=[g for g in gl if g[2]+g[3]>=8 and g[2]/(g[2]+g[3])<=.5]
    good=[g for g in gl if g not in bad];gp=sum(g[2] for g in good);gn=sum(g[3] for g in good)
    if bad and gp+gn>=8 and gp/(gp+gn)>=.7: T['skipgen']='Weak: '+', '.join(f"{g[0]} (+{g[2]}/−{g[3]})" for g in bad)+f". Others combined +{gp}/−{gn}"
    tc=collections.Counter(x.get('topic') for x in v).most_common(1)[0]
    if tc[0] and tc[1]>=.5*nc: T[tc[0]]=''
    return T
GENERIC=set('apple dell lenovo asus hp acer sony samsung logitech microsoft google bose nokia ikea steelcase herman miller sennheiser beyerdynamic motorola htc amazon lg toshiba huawei xiaomi intel amd nvidia canon nikon anker'.split())|{'herman miller'}
index=[]
PUB={k for k,v in G.items() if len({x['by'] for x in v if x['first_hand']})>=MIN_PAGE_OWNERS}
pages=[]
for k,v in G.items():
    if k not in PUB: continue
    v=sorted(v,key=lambda x:x['time'])
    cat=collections.Counter(x['category'] for x in v).most_common(1)[0][0]
    latest={}
    for x in v:
        if x['first_hand']: latest[x['by']]=x
    own=list(latest.values())
    pos=sum(a['stance'] in('recommend','positive') for a in own);neg=sum(a['stance']=='negative' for a in own);neu=len(own)-pos-neg
    rec=[a for a in own if a['y']>=LAST-2];rp=sum(a['stance'] in('recommend','positive') for a in rec);rn=sum(a['stance']=='negative' for a in rec)
    by_ten={}
    for x in v:
        if x['first_hand'] and x['tenure_years'] is not None and x['stance']!='negative': by_ten[x['by']]=max(by_ten.get(x['by'],0),x['tenure_years'])
    lh=sum(t>=3 for t in by_ten.values())
    still=len({x['by'] for x in v if x['still_going']})
    gens=collections.defaultdict(lambda:[set(),set(),set()])
    for x in v:
        if not x['first_hand']: continue
        g=gen_label(x)
        if g:
            gens[g][0].add(x['by'])
            if x['stance'] in('recommend','positive'): gens[g][1].add(x['by'])
            if x['stance']=='negative': gens[g][2].add(x['by'])
    gl=sorted(sorted(([g,len(a),len(b),len(c)] for g,(a,b,c) in gens.items()),key=lambda r:-r[1])[:12],key=lambda r:(0 if re.fullmatch(r'(19|20)\d\d',r[0]) else 1 if re.match(r'M\d',r[0]) else 2,r[0]))
    brand_only=(not v[0]['cl']) and (v[0]['cb'] in GENERIC or not v[0]['cb'])
    to=sorted(((names[t],t,len(s),len(moved[t].get(k,()))) for t,s in moved[k].items() if t in PUB),key=lambda r:-r[2])[:8]
    fr=sorted(((names[f],f,len(moved[f][k]),len(moved[k].get(f,()))) for f in moved if k in moved[f] and f in PUB),key=lambda r:-r[2])[:8]
    e=dict(k=k,n=names[k],c=cat,own=len(own),pos=pos,neg=neg,neu=neu,w=round(wilson(pos,pos+neg),4),rown=len(rec),rpos=rp,rneg=rn,rw=round(wilson(rp,rp+rn),4),lh=lh,maxt=max(by_ten.values()) if by_ten else None,still=still,fy=v[0]['y'],ly=v[-1]['y'],nc=len({x['id'] for x in v}),bo=brand_only)
    e['ty']=[t for t,_ in collections.Counter((x.get('product_type') or '').strip().lower() for x in v if x.get('product_type')).most_common(2)]
    why={} if brand_only else calc_tags(e,v,k,by_ten,gl)
    e['tags']=list(why)
    index.append(e)
    seen=set();cs=[]
    for x in sorted(v,key=lambda x:(-(x['tenure_years'] or 0),x['time'])):
        if x['id'] in seen: continue
        seen.add(x['id']);src=text[x['id']]
        cs.append(dict(id=x['id'],by=x['by'],d=x['time'],s=x['stance'],fh=x['first_hand'],ten=x['tenure_years'],sg=x['still_going'],m=x.get('model') or '',g=gen_label(x),sf=x.get('switched_from') or '',t=L.trim_text(src['text'],MAX_TEXT),th=x['title'] or '',root=x['root']))
    cs=L.pick_comments(cs,MAX_COMMENTS)
    pages.append(dict(e,gens=gl,to=to,fr=fr,cs=cs,why=why))
json.dump(dict(products=index,sample=dict(mentions=len(ms),comments=len({m['id'] for m in ms}),scanned=len(meta),full=sorted(FULL))),open('site/data/index.json','w'),ensure_ascii=False)
# Real HTML pages: the content is in the file, and app.js adds sorting and filters on top.
def write(path,body):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,'w') as f: f.write(body)
for d in ('site/data/p','site/p','site/c','site/t'): shutil.rmtree(d,ignore_errors=True)
span=None if not FULL else str(min(FULL)) if len(FULL)==1 else f"{min(FULL)} to {max(FULL)}"
cover=f"Based on {len(meta):,} of about 41 million comments"+(f": every comment matching our product filter from {span}, plus a sample of earlier years chosen to favor likely product opinions" if span else "")+". Counts are not totals for all of Hacker News. Opinions and ownership were extracted by AI and can be wrong, so every comment links to its source."
cats,tags=SR.read_meta('site/app.js')
site=SR.Site(cats,tags,cover,index)
ranked=sorted((p for p in index if p['own']>=3 and not p['bo']),key=lambda p:(-p['w'],-p['own']))
paths=['/']
write('site/index.html',site.list_page(ranked))
write('site/404.html',site.not_found())
for k in cats:
    r=[p for p in ranked if p['c']==k]
    if r: write(f'site/c/{SR.slug(k)}.html',site.list_page(r,cat=k));paths.append(SR.cat_path(k))
for k in tags:
    r=[p for p in ranked if k in p['tags']]
    if r: write(f'site/t/{SR.slug(k)}.html',site.list_page(r,tag=k));paths.append(SR.tag_path(k))
for p in pages: write(f"site/p/{p['k']}.html",site.product_page(p))
write('site/sitemap.xml',SR.sitemap(paths,index,dt.date.today().isoformat()))
write('site/robots.txt',SR.robots())
print('pages',len(pages),'categories and tags',len(paths)-1,'in sitemap',len(paths)+sum(SR.indexable(p) for p in index))
print('products',len(index),'with 3+ owners',sum(e['own']>=3 for e in index))

cc=collections.Counter(e['c'] for e in index if e['own']>=3 and not e['bo']);tc=collections.Counter(t for e in index if e['own']>=3 for t in e['tags'])
print('categories (3+ owners):',cc.most_common());print('tags (3+ owners):',tc.most_common())
