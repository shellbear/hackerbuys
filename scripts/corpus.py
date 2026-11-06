"""The comment text and details the site needs, kept in git so a scheduled run can build the site from a plain checkout.
  corpus/archive/<YYYY-MM>.parquet  processed comments from the full local queue and the second pass, refreshed by refresh_archive
  corpus/totals.json                candidates per year in the full local queue, and the last day it covers
  corpus/daily/<day>.parquet        the whole queue for one later day, built by 30_daily_queue.py
The full queue (data/extract/queue.parquet) stays local: it is large and only needed to process older years."""
import datetime as dt, filecmp, glob, json, os, shutil, tempfile

DIR = "corpus"
ARCHIVE, DAILY, TOTALS = f"{DIR}/archive", f"{DIR}/daily", f"{DIR}/totals.json"
COLS = 'id,"by",time,y,tier,root_id,thread,"text"'


def refresh_archive(queue, recall_queue, done, recall_done, out=ARCHIVE, totals=TOTALS):
    """Write the processed comments of the full queue (and of the second pass) by month, and the full queue's yearly totals.
    Month files whose content did not change are left untouched, so git only sees real changes."""
    import duckdb
    con = duckdb.connect()
    try:
        con.execute("set timezone='UTC'")
        for name, ids in (("d", done), ("rd", recall_done)):
            con.execute(f"create table {name}(id uinteger primary key)")
            if ids:
                con.executemany(f"insert into {name} values (?)", [[i] for i in sorted(ids)])
        con.execute(f"create table a as select {COLS} from read_parquet('{queue}') where id in (select id from d)")
        if recall_queue and os.path.exists(recall_queue):
            con.execute(f"""insert into a select id,"by",time,year(time),'recall',root_id,thread,"text" from read_parquet('{recall_queue}')
                            where id in (select id from rd) and id not in (select id from a)""")
        os.makedirs(out, exist_ok=True)
        months = [m for (m,) in con.execute("select distinct strftime(time,'%Y-%m') m from a order by m").fetchall()]
        changed = 0
        with tempfile.TemporaryDirectory() as tmp:
            for m in months:
                t, dest = os.path.join(tmp, f"{m}.parquet"), os.path.join(out, f"{m}.parquet")
                con.execute(f"copy (select * from a where strftime(time,'%Y-%m')='{m}' order by id) to '{t}' (format parquet,compression zstd)")
                if not (os.path.exists(dest) and filecmp.cmp(t, dest, shallow=False)):
                    shutil.move(t, dest)
                    changed += 1
        for f in glob.glob(f"{out}/*.parquet"):
            if os.path.basename(f)[:-8] not in months:
                os.remove(f)
                changed += 1
        years, through = con.execute(f"select map_from_entries(list((y,n))),max(d) from (select y,count(*) n,max(time)::date d from read_parquet('{queue}') group by y)").fetchone()
        write_totals({"through": str(through), "years": {str(y): n for y, n in sorted(years.items())}}, totals)
        return len(months), changed
    finally:
        con.close()


def write_totals(d, path=TOTALS):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(d, f, indent=1, sort_keys=True)
        f.write("\n")


def read_totals(path=TOTALS):
    with open(path) as f:
        return json.load(f)


def last_day(totals_path=TOTALS, daily=DAILY):
    """The last day covered by the full queue or a daily queue."""
    days = [os.path.basename(f)[:-8] for f in glob.glob(f"{daily}/*.parquet")]
    return max(days + [read_totals(totals_path)["through"]])


def days_after(last, until):
    """Days after last, up to and including until, oldest first."""
    a, b = dt.date.fromisoformat(last), dt.date.fromisoformat(until)
    return [str(a + dt.timedelta(days=k)) for k in range(1, (b - a).days + 1)]
