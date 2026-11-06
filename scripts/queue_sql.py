"""SQL shared by the full queue (22_build_queue.py) and the one-day queues (30_daily_queue.py), so both select comments the same way."""
from lexicon import CATEGORIES, OWN, REC, RETAIL

CLEAN = r"""create macro clean(t) as regexp_replace(regexp_replace(replace(replace(replace(replace(replace(replace(t,'&#x27;',''''),'&quot;','"'),'&#x2F;','/'),'&gt;','>'),'&lt;','<'),'&amp;','&'),'<p>',' ','g'),'<[^>]+>',' ','g')"""


def daily_candidates(src):
    """Comments in daily files that pass the keyword filter, as id,parent,by,time,txt,n,fun. The archive filter in 01_funnel.py
    ends where the raw files end, so later days get the same regexes here. Needs the clean macro."""
    cat_any = "|".join(CATEGORIES.values())
    return rf"""select id,parent,"by",time,txt,length(txt) n,
       regexp_matches(lt,$${OWN}$$) or regexp_matches(lt,$${REC}$$) or regexp_matches(lt,$${RETAIL}$$) or regexp_matches(lt,$$\bmy (?:\w+ ){{0,3}}(?:{cat_any})s?\b$$) fun
      from (select *,lower(txt) lt from (select id,parent,"by",time,clean(text) txt from read_parquet({src})
            where type=2 and coalesce(deleted,0)=0 and coalesce(dead,0)=0 and text is not null and "by"<>'' and text<>'[delayed]'))
      where regexp_matches(lt,$$\b(?:{cat_any})s?\b|{RETAIL}$$)"""
