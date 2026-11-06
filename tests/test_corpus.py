import json, os, sys, tempfile, unittest
sys.path.insert(0, 'scripts')
import duckdb
import corpus as C


class Days(unittest.TestCase):
    def test_days_after_are_oldest_first_and_exclude_last(self):
        self.assertEqual(C.days_after('2026-11-03', '2026-11-05'), ['2026-11-04', '2026-11-05'])
    def test_nothing_to_add_when_up_to_date(self):
        self.assertEqual(C.days_after('2026-11-05', '2026-11-04'), [])
    def test_last_day_is_the_newest_daily_queue_or_the_full_queue_end(self):
        with tempfile.TemporaryDirectory() as d:
            totals, daily = os.path.join(d, 't.json'), os.path.join(d, 'daily')
            C.write_totals({'through': '2026-11-03', 'years': {}}, totals)
            os.makedirs(daily)
            self.assertEqual(C.last_day(totals, daily), '2026-11-03')
            open(os.path.join(daily, '2026-11-05.parquet'), 'w').close()
            self.assertEqual(C.last_day(totals, daily), '2026-11-05')


class Archive(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.q, self.rq = os.path.join(self.d.name, 'q.parquet'), os.path.join(self.d.name, 'rq.parquet')
        self.out, self.totals = os.path.join(self.d.name, 'archive'), os.path.join(self.d.name, 'totals.json')
        rows = """(1,10,'a','2026-10-31 23:00:00+00',2026,'funnel',5,'T','p','one',3),(2,20,'b','2026-11-01 01:00:00+00',2026,'rest',5,'T',null,'two',3),
                  (3,30,'c','2025-01-02 00:00:00+00',2025,'funnel',6,'U',null,'three',5)"""
        cols = 'seq,id,"by",time,y,tier,root_id,thread,parent,"text",n'
        con = duckdb.connect(); con.execute("set timezone='UTC'")
        con.execute(f"copy (select seq,id,\"by\",time::timestamptz time,y,tier,root_id,thread,parent,\"text\",n from (values {rows}) v({cols})) to '{self.q}' (format parquet)")
        con.execute(f"copy (select seq,id,\"by\",time::timestamptz time,y,'recall' tier,root_id,thread,parent,\"text\",n from (values (1,40,'d','2026-10-02 00:00:00+00',2026,'x',7,'V',null,'four',4)) v({cols})) to '{self.rq}' (format parquet)")
    def tearDown(self): self.d.cleanup()
    def refresh(self, done, recall_done=()):
        return C.refresh_archive(self.q, self.rq, set(done), set(recall_done), self.out, self.totals)
    def rows(self):
        return duckdb.sql(f"select id,tier from read_parquet('{self.out}/*.parquet') order by id").fetchall()
    def test_keeps_only_processed_comments_split_by_utc_month(self):
        self.refresh({10, 20}, {40})
        self.assertEqual(sorted(os.listdir(self.out)), ['2026-10.parquet', '2026-11.parquet'])
        self.assertEqual(self.rows(), [(10, 'funnel'), (20, 'rest'), (40, 'recall')])
    def test_totals_count_every_queued_comment_per_year(self):
        self.refresh({10})
        self.assertEqual(json.load(open(self.totals)), {'through': '2026-11-01', 'years': {'2025': 1, '2026': 2}})
    def test_unchanged_months_are_not_rewritten(self):
        self.refresh({10, 20})
        self.assertEqual(self.refresh({10, 20, 30}), (3, 1))
    def test_month_with_no_processed_comments_left_is_removed(self):
        self.refresh({10, 20})
        self.refresh({20})
        self.assertEqual(sorted(os.listdir(self.out)), ['2026-11.parquet'])


if __name__ == '__main__':
    unittest.main()
