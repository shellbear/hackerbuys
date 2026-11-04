import duckdb,math
c=duckdb.connect('data/derived/work.duckdb',read_only=True)
SCORE="""select product,any_value(cat) cat,count(distinct a) authors,count(*) mentions,
 sum(pos) pos,sum(neg) neg,sum(w) score,min(y) first_y,max(y) last_y from (
  select product,cat,a,max(y) y,max(pol=1)::int pos,(max(pol=-1) and not max(pol=1))::int neg,
    (case when max(pol=1) then 1 when max(pol=-1) then -1 else .25 end)
     *case when max(pol=-1) and not max(pol=1) then 1 else
     (1+.5*max(own::int)+.5*max(ten::int)+.5*max(thread::int)+.5*max(top::int)+.25*ln(1+least(max(nkids),20))) end w,count(*) m
  from pm where {where} group by 1,2,3) group by 1"""
c.sql(f"create temp table s as select *,(pos+1.0)/(pos+neg+2) ratio from ({SCORE.format(where='true')})")
print(c.sql("select product,cat,authors,pos,neg,round(100*ratio) pos_pct,round(score) score,first_y,last_y from s order by score desc limit 40"))
print(c.sql("select cat,count(*) products,sum(authors) authors,round(100.0*sum(pos)/sum(pos+neg)) pos_pct from s group by 1 order by 3 desc"))
print(c.sql("select product,authors,pos,neg,round(100*ratio) pos_pct from s where authors>=40 order by ratio asc limit 12"))
print(c.sql("select product,authors,pos,neg,round(100*ratio) pos_pct from s where authors>=40 order by ratio desc limit 12"))
print(c.sql("""select cat,any_value(topp) from (select cat,string_agg(product||' ('||round(score)::int||')',', ' order by score desc) topp from s group by 1) group by 1 order by 1""").df().to_string(max_colwidth=170))
# backtest: train<=2021, test>=2022
import scipy.stats as st
tr=c.sql(SCORE.format(where='y<=2021')).df().set_index('product')
te=c.sql(SCORE.format(where='y>=2022')).df().set_index('product')
te['pos_new']=te['pos']
j=tr.join(te[['pos_new','authors']],rsuffix='_te',how='left').fillna(0)
j=j[j.authors>=5]; print('backtest n',len(j))
for f in ['mentions','authors','pos','score']:
    print('spearman train',f,'-> test positive authors',round(st.spearmanr(j[f],j.pos_new)[0],3),'top20 hit',len(set(j.nlargest(20,f).index)&set(j.nlargest(20,'pos_new').index)))
dec=c.sql(SCORE.format(where='y between 2019 and 2021')).df().set_index('product').score.reindex(j.index).fillna(0)
print('spearman recent score(2019-21)',round(st.spearmanr(dec,j.pos_new)[0],3),'top20',len(set(dec.nlargest(20).index)&set(j.nlargest(20,'pos_new').index)))
# rising, normalized by comment volume
print(c.sql("""with v as (select year(m) y,sum(n) n from 'data/derived/monthly.parquet' group by 1),
 a as (select product,cat,count(distinct case when y between 2021 and 2023 then a end)*1e6/(select sum(n) from v where y between 2021 and 2023) r1,
  count(distinct case when y between 2024 and 2026 then a end)*1e6/(select sum(n) from v where y between 2024 and 2026) r2,
  count(distinct case when y between 2024 and 2026 then a end) n2 from pm group by 1,2)
 select product,cat,n2,round(r1,1) per_M_2123,round(r2,1) per_M_2426,round(r2/nullif(r1,0),2) ratio from a where n2>=25 order by ratio desc limit 25"""))
print(c.sql("""with v as (select year(m) y,sum(n) n from 'data/derived/monthly.parquet' group by 1),
 a as (select product,count(distinct case when y between 2021 and 2023 then a end)*1e6/(select sum(n) from v where y between 2021 and 2023) r1,
  count(distinct case when y between 2024 and 2026 then a end)*1e6/(select sum(n) from v where y between 2024 and 2026) r2,count(distinct case when y between 2021 and 2023 then a end) n1 from pm group by 1)
 select product,n1,round(r1,1),round(r2,1),round(r2/nullif(r1,0),2) ratio from a where n1>=30 order by ratio asc limit 12"""))
print(c.sql("""select year(time) y,round(1e6*count(distinct case when f_mycat or f_own then id end)/any_value(v.n)) per_M from 'data/derived/funnel.parquet' f join (select year(m) yy,sum(n) n from 'data/derived/monthly.parquet' group by 1) v on v.yy=year(time) group by 1 order by 1"""))
