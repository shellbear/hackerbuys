"""Usage: llm_run.py input.jsonl output.jsonl model batch_size concurrency budget_usd. Resumable; stops at budget."""
import asyncio,json,sys,os,time,anthropic
sys.path.insert(0,'scripts')
from llm_common import *
inp,out,model,bs,conc,budget=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5]),float(sys.argv[6])
rows=[json.loads(l) for l in open(inp)]
done=set()
if os.path.exists(out):
    for l in open(out):
        done.update(json.loads(l)['ids'])
rows=[r for r in rows if r['id'] not in done]
chunks=[rows[i:i+bs] for i in range(0,len(rows),bs)]
client=anthropic.AsyncAnthropic(max_retries=4,timeout=120)
pi,po=PRICE[model]; st=dict(i=0,o=0,cost=0.0,ok=0,err=0,trunc=0); sem=asyncio.Semaphore(conc); f=open(out,'a'); t0=time.time(); stop=asyncio.Event()
extra={"thinking":{"type":"disabled"}} if 'haiku' in model else {"thinking":{"type":"between_tools"}}
async def run(ch):
    if stop.is_set(): return
    async with sem:
        if stop.is_set(): return
        try:
            m=await client.messages.create(model=model,max_tokens=6000,system=SYSTEM,messages=[{"role":"user","content":payload(ch)}],output_config={"effort":"low","format":{"type":"json_schema","schema":SCHEMA}},**extra)
        except anthropic.APIStatusError as e:
            st['err']+=1; print('ERR',e.status_code,str(e.message)[:200],flush=True)
            if e.status_code in (400,401,403,404): stop.set()
            return
        except anthropic.APIConnectionError as e:
            st['err']+=1; print('ERR conn',flush=True); return
        st['i']+=m.usage.input_tokens; st['o']+=m.usage.output_tokens; st['cost']+=(m.usage.input_tokens*pi+m.usage.output_tokens*po)/1e6
        if st['cost']>budget: stop.set(); print('BUDGET STOP',flush=True)
        if m.stop_reason!='end_turn': st['trunc']+=1; print('stop_reason',m.stop_reason,flush=True); return
        txt=next(b.text for b in m.content if b.type=='text')
        res=json.loads(txt)['results']
        f.write(json.dumps({"ids":[r['id'] for r in ch],"results":[{"id":ch[x['i']]['id'],"products":x['products']} for x in res if 0<=x['i']<len(ch)]},ensure_ascii=False)+"\n"); f.flush()
        st['ok']+=1
        if st['ok']%50==0: print(f"{st['ok']}/{len(chunks)} {time.time()-t0:.0f}s ${st['cost']:.3f} err={st['err']}",flush=True)
async def main(): await asyncio.gather(*[run(c) for c in chunks])
asyncio.run(main())
print('FINISHED',st,f"{time.time()-t0:.0f}s",flush=True)
