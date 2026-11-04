const CATS={chairs:'Chairs',desks:'Desks',monitors:'Monitors',keyboards:'Keyboards',mice_trackpads:'Mice and trackpads',headphones:'Headphones',laptops:'Laptops',desktops:'Desktops and mini PCs',phones:'Phones',tablets:'Tablets',ereaders:'E-readers and e-ink',audio_hifi:'Speakers and audio',webcams_mics:'Webcams and mics',tv_streaming:'TVs and streaming',cameras:'Cameras',networking:'Networking',storage:'NAS and storage',gpus_cpus:'GPUs and CPUs',pc_components:'Other PC parts and servers',sbc_maker:'Boards and maker kit',printers_3d:'3D printers',calculators:'Calculators',consoles:'Consoles and handhelds',vr_ar:'VR and AR headsets',gaming:'Other gaming',wearables_watches:'Watches and wearables',smart_home:'Smart home',cleaning:'Robot vacuums and cleaning',kitchen_coffee:'Kitchen and coffee',home_appliances:'Home appliances',power:'Chargers and power',bed_sleep:'Beds and sleep',bags_luggage:'Bags and luggage',clothing_shoes:'Clothing and shoes',tools_edc:'Tools and everyday carry',pens_paper:'Pens and paper',bikes_mobility:'Bikes and scooters',fitness:'Fitness',lighting_desk:'Lights and desk gear',other_physical:'Everything else'};
const TAGS={bifl:['Buy it for life','At least 3 owners happy after 5 or more years, and no more than 1 in 5 verdicts negative.'],switch:['People switch to this','At least 3 owners came from another product, and at least twice as many arrived as left.'],skipgen:['Skip some generations','At least one generation splits evenly or worse, while the others are at least 70% positive.'],divisive:['Divisive','At least 10 verdicts, with positive between 40% and 60%.'],rising:['Rising','Mentioned at least 1.5 times as often since 2024 as in 2019 to 2023, adjusted for how many comments were sampled. This measures attention, not quality.'],fading:['Fading','Mentioned at most 0.4 times as often since 2024 as in 2019 to 2023, adjusted for how many comments were sampled. Office gear can also fade because 2020 and 2021 drew unusually many work-from-home comments, and durable products because owners have little new to say.'],dated:['Mostly older mentions','At least 60% of mentions are from before 2019, and almost none are since 2024. It may be discontinued or replaced, or still on sale and simply not discussed, so check before buying.'],music_players:['Music players','Portable music players.'],printers_scanners:['Printers and scanners','Printers and document scanners.'],instruments:['Musical instruments','Instruments, MIDI controllers and synths.'],drawing_tablets:['Drawing tablets','Pen tablets and displays.'],security_trackers:['Security keys and trackers','Hardware keys, item trackers and pocket security tools.'],vintage:['Vintage computers','Older computers and terminals people still talk about.'],test_gear:['Test gear and soldering','Oscilloscopes, meters, calipers and soldering irons.'],bidets:['Bidets','Bidets and washlets.']};
const QUAL=['bifl','switch','skipgen','divisive','rising','fading','dated'];
const VIEWS={loved:{t:'Most loved',d:'Ranked by how lopsided the verdict is among owners, adjusted so a handful of fans can’t beat a large, happy crowd.'},owned:{t:'Most owned',d:'Ranked by how many commenters say they own or have used it, whatever they think of it.'},recent:{t:'Recommended lately',d:'The same verdict, using only owners who commented from 2024 on.'},long:{t:'Long-haul',d:'Owners still happy after 3 or more years, as stated in their own comment.'}};
const slug=k=>k.replace(/_/g,'-');const MIN=3;let DB;const $=s=>document.querySelector(s);
function el(t,a={},...k){const e=document.createElement(t);for(const[n,v]of Object.entries(a)){if(v==null)continue;if(n==='class')e.className=v;else if(n.startsWith('on'))e.addEventListener(n.slice(2),v);else e.setAttribute(n,v)}for(const c of k.flat())if(c!=null)e.append(c);return e}
function tally(p,neu,n,max=120){const t=p+neu+n,w=el('div',{class:'tally',role:'img','aria-label':`${p} positive, ${neu} neutral, ${n} negative`}),s=t>max?max/t:1;
 const add=(c,x)=>{for(let i=0;i<Math.round(x*s);i++)w.append(el('i',{class:c}))};add('p',p);add('',neu);add('n',n);if(s<1)w.append(el('b',{},'scaled to fit'));return w}
const scored=(view,cat,tag)=>{let r=DB.products.filter(p=>!p.bo&&(!cat||p.c===cat)&&(!tag||p.tags.includes(tag)));
 if(view==='recent')return r.filter(p=>p.rown>=Math.max(2,MIN-1)).sort((a,b)=>b.rw-a.rw||b.rown-a.rown);
 if(view==='owned')return r.filter(p=>p.own>=MIN).sort((a,b)=>b.own-a.own||b.w-a.w);
 if(view==='long')return r.filter(p=>p.lh>=1).sort((a,b)=>b.lh-a.lh||(b.maxt||0)-(a.maxt||0));
 return r.filter(p=>p.own>=MIN).sort((a,b)=>b.w-a.w||b.own-a.own)};
function nav(cur,curTag){const c=$('#cats'),live=DB.products.filter(p=>p.own>=MIN&&!p.bo);
 const tagLink=([k,n])=>el('a',{href:`/t/${slug(k)}`,'aria-current':curTag===k?'page':null},TAGS[k][0],el('span',{},String(n)));
 const tags=Object.keys(TAGS).map(k=>[k,live.filter(p=>p.tags.includes(k)).length]).filter(x=>x[1]>0);
 c.replaceChildren(el('a',{href:'/','aria-current':cur||curTag?null:'page'},'All categories',el('span',{},String(live.length))),
 ...Object.entries(CATS).map(([k,v])=>[k,v,live.filter(p=>p.c===k).length]).filter(x=>x[2]>0).sort((a,b)=>b[2]-a[2]).map(([k,v,n])=>el('a',{href:`/c/${slug(k)}`,'aria-current':cur===k?'page':null},v,el('span',{},String(n)))),
 el('p',{class:'navh'},'Verdict tags'),...tags.filter(x=>QUAL.includes(x[0])).map(tagLink),el('p',{class:'navh'},'Smaller groups'),...tags.filter(x=>!QUAL.includes(x[0])).map(tagLink))}
function chips(tags,cur){return tags&&tags.length?el('span',{class:'chips'},tags.filter(t=>t!==cur&&TAGS[t]).map(t=>el('a',{href:`/t/${slug(t)}`,title:TAGS[t][1]},TAGS[t][0]))):null}
const PAGE=100,VERDICT_TIP='Sorts by how confidently positive owners are, adjusted for how many gave a verdict. Reverse it to see the most disliked.',HAPPY_TIP='Positive verdicts as a share of positive and negative. Neutral verdicts are not counted.';let SORT=null,SHOW=PAGE;
function list(cat,view='loved',tag,keep){if(!keep){SORT=null;SHOW=PAGE}nav(cat,tag);const base=cat?`/c/${slug(cat)}`:tag?`/t/${slug(tag)}`:'/',v=VIEWS[view],ranked=scored(view,cat,tag),all=SORT?TableSort.sortRows(ranked,SORT.key,SORT.dir,view):ranked,r=all.slice(0,SHOW);
 const again=()=>{const y=window.scrollY,k=SORT&&SORT.key;list(cat,view,tag,true);window.scrollTo(0,y);if(k){const b=document.querySelector(`th button[data-k="${k}"]`);if(b)b.focus()}};
 const sth=(label,key,cls,tip)=>{if(!key)return el('th',{class:cls,title:tip},label);const on=SORT&&SORT.key===key;
  return el('th',{class:cls,title:tip,'aria-sort':on?(SORT.dir==='asc'?'ascending':'descending'):'none'},el('button',{type:'button','data-k':key,class:on?'on':null,onclick(){SORT=on?{key,dir:SORT.dir==='asc'?'desc':'asc'}:{key,dir:TableSort.defaultDir(key)};again()}},label,on?(SORT.dir==='asc'?' ▲':' ▼'):''))};
 const head=view==='recent'?['Since 2024','Owners','Happy']:view==='long'?['Verdict','3+ years','Longest']:['Verdict','Owners','Happy'];
 const m=$('#main');m.replaceChildren(...[el('h1',{},cat?CATS[cat]:tag?TAGS[tag][0]:'Everything people here actually own'),tag?el('p',{class:'lede'},TAGS[tag][1]):null,
 el('div',{class:'views'},Object.entries(VIEWS).map(([k,x])=>el('a',{href:k==='loved'?base:`${base}?view=${k}`,'aria-current':k===view?'true':'false'},x.t))),
 el('p',{class:'note'},v.d),
 SORT&&SORT.key==='happy'?el('p',{class:'note'},'Products with only a few owners can reach 100%. ',el('a',{href:base},'Most loved'),' adjusts for that.'):null,
 el('div',{class:'key'},el('span',{class:'p'},'Positive'),el('span',{},'Neutral'),el('span',{class:'n'},'Negative')),
 r.length?el('table',{},el('thead',{},el('tr',{},sth('Product','name'),sth(head[0],'verdict',null,VERDICT_TIP),sth(head[1],'count'),sth(head[2],view==='long'?'longest':'happy',view==='long'?null:'hide-s',view==='long'?null:HAPPY_TIP),sth('Last mention','last','hide-s'))),
 el('tbody',{},r.map(p=>{const P=view==='recent'?[p.rpos,p.rown-p.rpos-p.rneg,p.rneg]:[p.pos,p.neu,p.neg],tot=P[0]+P[2];
  return el('tr',{},el('td',{class:'nm'},el('a',{href:`/p/${p.k}`},p.n),cat?null:el('small',{},CATS[p.c]||p.c),chips(p.tags,tag)),el('td',{class:'ty'},tally(...P,60)),
  el('td',{},String(view==='long'?p.lh:view==='recent'?p.rown:p.own)),view==='long'?el('td',{},p.maxt?`${p.maxt} yrs`:'–'):el('td',{class:'hide-s'},tot?`${Math.round(100*P[0]/tot)}%`:'–'),el('td',{class:'hide-s'},String(p.ly)))}))):el('p',{class:'empty'},'No products have enough owners here yet. Try another ranking or category.'),
 all.length>r.length?el('p',{class:'more'},el('button',{type:'button',onclick(){SHOW=all.length;const y=window.scrollY;list(cat,view,tag,true);window.scrollTo(0,y)}},`Show all ${all.length.toLocaleString()} products`)):null].filter(Boolean));
 if(!keep)window.scrollTo(0,0)}
function mark(terms,txt){const b=el('blockquote',{});const w=[...new Set(terms.map(x=>(x||'').trim()).filter(x=>x.length>1))].sort((x,y)=>y.length-x.length).map(x=>x.replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/\s+/g,'\\s+'));if(!w.length){b.textContent=txt;return b}
 const rx=new RegExp(`\\b(?:${w.join('|')})s?\\b`,'ig');let i=0,m;while((m=rx.exec(txt))){b.append(txt.slice(i,m.index),el('mark',{},m[0]));i=m.index+m[0].length}b.append(txt.slice(i));return b}
function comment(c,name){const cl=c.s==='negative'?'n':c.s==='neutral'?'':'p',lab={recommend:'Recommends it',positive:'Likes it',neutral:'Neutral',negative:'Doesn’t like it'}[c.s];
 const q=mark([name,c.m],c.t);if(c.t.length>460)q.classList.add('clip');
 const more=c.t.length>460?el('button',{type:'button','aria-expanded':'false',onclick(e){const o=q.classList.toggle('clip');e.target.textContent=o?'Show full comment':'Show less';e.target.setAttribute('aria-expanded',String(!o))}},'Show full comment'):null;
 return el('article',{class:`c ${cl}`},el('header',{},el('strong',{},lab),c.ten!=null?el('span',{class:'yrs'},`Owned ${c.ten} ${c.ten===1?'year':'years'}`):null,c.sg?el('span',{},'Still going'):null,!c.fh?el('span',{},'Hasn’t owned it'):null,c.m?el('span',{},c.m):null,c.g&&c.g!==c.m?el('span',{},c.g):null,c.sf?el('span',{},`Switched from ${c.sf}`):null),q,
 el('footer',{},more,el('a',{href:`https://news.ycombinator.com/item?id=${c.id}`,rel:'noopener'},`${c.by}, ${c.d}`),c.th&&c.root?el('a',{href:`https://news.ycombinator.com/item?id=${c.root}`,rel:'noopener'},`in “${c.th}”`):null))}
function product(p){const m=$('#main');let f='all',sort='ten';const wrap=el('div',{});
 const draw=()=>{let cs=p.cs.filter(c=>f==='all'||(f==='good'&&(c.s==='recommend'||c.s==='positive'))||(f==='bad'&&c.s==='negative')||(f==='long'&&(c.ten||0)>=3));
  cs=[...cs].sort(sort==='ten'?(a,b)=>(b.ten||0)-(a.ten||0)||b.d.localeCompare(a.d):sort==='new'?(a,b)=>b.d.localeCompare(a.d):(a,b)=>a.d.localeCompare(b.d));
  wrap.replaceChildren(...(cs.length?cs.map(c=>comment(c,p.n.replace(/^(Apple|Lenovo|Herman Miller|Amazon|Steelcase)\s/,''))):[el('p',{class:'empty'},'No comments match this filter.')]));
  fb.forEach(([key,b])=>b.setAttribute('aria-pressed',String(key===f)))};
 const opt=[['all',p.nc>p.cs.length?`${p.cs.length} of ${p.nc}`:`All ${p.cs.length}`],['good','Positive'],['bad','Negative'],['long','Owned 3+ years']];
 const fb=opt.map(([key,l])=>[key,el('button',{type:'button',onclick(){f=key;draw()}},l)]);
 const sel=el('select',{'aria-label':'Sort comments',onchange(e){sort=e.target.value;draw()}},el('option',{value:'ten'},'Longest owned first'),el('option',{value:'new'},'Newest first'),el('option',{value:'old'},'Oldest first'));
 m.replaceChildren(...[el('p',{class:'crumb'},el('a',{href:`/c/${slug(p.c)}`},CATS[p.c]||p.c)),el('h1',{},p.n),
 p.tags.length?el('ul',{class:'whys'},p.tags.filter(t=>TAGS[t]).map(t=>el('li',{},el('a',{href:`/t/${slug(t)}`},TAGS[t][0]),p.why[t]?el('span',{},p.why[t]):null))):null,el('div',{class:'big'},tally(p.pos,p.neu,p.neg,120)),
 el('div',{class:'verdict'},el('div',{},el('b',{},String(p.own)),'owners with an opinion'),el('div',{},el('b',{},p.pos+p.neg?`${Math.round(100*p.pos/(p.pos+p.neg))}%`:'–'),'of verdicts positive'),el('div',{},el('b',{},`${p.rpos}/${p.rneg}`),'positive/negative since 2024'),p.maxt?el('div',{},el('b',{},`${p.maxt} yrs`),'longest happy owner'):null,el('div',{},el('b',{},String(p.lh)),'happy after 3+ years')),
 p.gens.length?[el('h2',{},'By generation'),el('table',{},el('thead',{},el('tr',{},el('th',{},'Generation'),el('th',{},'Verdict'),el('th',{},'Owners'))),el('tbody',{},p.gens.map(([g,n,a,b])=>el('tr',{},el('td',{class:'nm'},g),el('td',{class:'ty'},tally(a,n-a-b,b,60)),el('td',{},String(n))))))]:null,
 p.to.length||p.fr.length?[el('h2',{},'Where people moved'),el('div',{class:'two'},p.to.length?el('div',{},el('p',{class:'note'},'Left this for'),el('ul',{class:'moves'},p.to.map(([n,k2,c])=>el('li',{},el('a',{href:`/p/${k2}`},n),el('span',{},String(c)))))):null,p.fr.length?el('div',{},el('p',{class:'note'},'Came here from'),el('ul',{class:'moves'},p.fr.map(([n,k2,c])=>el('li',{},el('a',{href:`/p/${k2}`},n),el('span',{},String(c)))))):null)]:null,
 el('h2',{},'What owners wrote'),el('div',{class:'filters'},fb.map(x=>x[1]),sel),wrap].flat().filter(Boolean));draw()}
// Old links used #/ routes; send them to the real URL.
function oldHash(){const h=location.hash;if(!h.startsWith('#/'))return null;const s=h.slice(2).split('/').filter(Boolean);
 if(s[0]==='p'&&s[1])return`/p/${s[1]}`;if((s[0]==='c'||s[0]==='t')&&s[1])return`/${s[0]}/${slug(s[1])}${s[2]?`?view=${s[2]}`:''}`;if(s[0]==='v'&&s[1])return`/?view=${s[1]}`;return'/'}
// Links swap the main content without a reload. Real pages remain for search, new tabs and any failure.
const pages=new Map();let dbLoad=null,navToken=0;
const loadDB=()=>dbLoad||(dbLoad=fetch('/data/index.json').then(r=>{if(!r.ok)throw 0;return r.json()}).then(d=>DB=d).catch(e=>{dbLoad=null;throw e}));
const loadPage=u=>{if(!pages.has(u))pages.set(u,fetch(u).then(r=>{if(!r.ok)throw 0;return r.text()}).catch(e=>{pages.delete(u);throw e}));return pages.get(u)};
function setCanonical(path){const c=document.querySelector('link[rel=canonical]');if(c)c.href=location.origin+path}
async function show(url,top){const s=url.pathname.split('/').filter(Boolean),t=++navToken;
 if(s[0]==='p'){const doc=new DOMParser().parseFromString(await loadPage(url.pathname),'text/html'),data=doc.querySelector('#product');if(!data)throw 0;if(t!==navToken)return;
  document.title=doc.title;$('#cats').innerHTML=doc.querySelector('#cats').innerHTML;product(JSON.parse(data.textContent))}
 else{await loadDB();if(t!==navToken)return;const q=url.searchParams.get('view'),view=VIEWS[q]?q:'loved',find=(keys,x)=>Object.keys(keys).find(k=>slug(k)===x);
  const cat=s[0]==='c'?find(CATS,s[1]):null,tag=s[0]==='t'?find(TAGS,s[1]):null;if(s[0]&&!cat&&!tag)throw 0;
  document.title=TableSort.listTitle({cat,tag,name:cat?CATS[cat]:tag?TAGS[tag][0]:''});list(cat,view,tag)}
 setCanonical(url.pathname);window.scrollTo(0,top||0)}
async function go(url){history.replaceState({y:window.scrollY},'');try{await show(url,0);history.pushState({},'',url);$('#main').focus({preventScroll:true})}catch{location.href=url}}
document.addEventListener('click',e=>{const a=e.target.closest&&e.target.closest('a[href]');if(!a||e.defaultPrevented||e.button||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||a.target||a.hasAttribute('download'))return;
 const url=new URL(a.href);if(!TableSort.canSwap(url,location.origin))return;e.preventDefault();go(url)});
// Start downloading a product page when the pointer reaches its link, so the click feels immediate.
document.addEventListener('pointerover',e=>{const a=e.target.closest&&e.target.closest('a[href^="/p/"]');if(a)loadPage(new URL(a.href).pathname).catch(()=>{})},{passive:true});
addEventListener('popstate',e=>{const url=new URL(location.href);show(url,e.state&&e.state.y).catch(()=>location.reload())});
function start(){const old=oldHash();if(old)return location.replace(old);if('scrollRestoration'in history)history.scrollRestoration='manual';history.replaceState({y:0},'');
 const embedded=$('#product');if(embedded)return product(JSON.parse(embedded.textContent));
 const url=new URL(location.href);if(!TableSort.canSwap(url,location.origin))return;
 // The page is already readable without this; it adds sorting and the other views.
 show(url,0).catch(()=>{})}
start();
