import json, re, sys, unittest
sys.path.insert(0, 'scripts')
import site_render as R

E = dict(k='kinesis-advantage', n='Kinesis Advantage', c='keyboards', own=170, pos=158, neg=12, neu=0, w=.89, rown=10, rpos=10, rneg=0, rw=.7, lh=40, maxt=25, still=3, fy=2008, ly=2026, nc=200, bo=False, tags=['bifl'],
         gens=[['2003', 1, 1, 0]], to=[['MoErgo Glove80', 'moergo-glove80', 3, 0]], fr=[], why={'bifl': '36 owners happy'},
         cs=[dict(id=1, by='alice', d='2026-01-01', s='positive', fh=True, ten=5, sg=False, m='', g='', sf='', t='Great <script>alert(1)</script> & comfy', th='Ask HN: keyboards?', root=9)])
CATS, TAGS = {'keyboards': 'Keyboards', 'mice_trackpads': 'Mice and trackpads', 'other_physical': 'Everything else'}, {'bifl': ['Buy it for life', 'Lasts.'], 'music_players': ['Music players', 'Players.']}
SITE = R.Site(CATS, TAGS, 'Based on 10 comments.')

class Escaping(unittest.TestCase):
    def test_comment_html_is_escaped(self):
        h = SITE.product_page(E)
        self.assertNotIn('<script>alert(1)', h)
        self.assertIn('&lt;script&gt;alert(1)', h)
    def test_embedded_json_cannot_close_its_script_tag(self):
        h = SITE.product_page(dict(E, n='</script><img src=x>'))
        self.assertNotIn('</script><img', h)
    def test_embedded_json_round_trips(self):
        h = SITE.product_page(E)
        data = re.search(r'<script type="application/json" id="product">(.*?)</script>', h, re.S).group(1)
        self.assertEqual(json.loads(data)['cs'][0]['t'], E['cs'][0]['t'])
    def test_product_name_is_escaped_in_title_and_meta(self):
        h = SITE.product_page(dict(E, n='A "quoted" <b>'))
        self.assertIn('A &quot;quoted&quot; &lt;b&gt;', h)

class Urls(unittest.TestCase):
    def test_category_urls_use_hyphens(self):
        self.assertEqual(R.cat_path('mice_trackpads'), '/c/mice-trackpads')
    def test_tag_urls_use_hyphens(self):
        self.assertEqual(R.tag_path('music_players'), '/t/music-players')
    def test_product_links_are_real_urls(self):
        h = SITE.list_page([E], cat='keyboards')
        self.assertIn('href="/p/kinesis-advantage"', h)
        self.assertNotIn('#/', h)
    def test_moves_link_to_real_urls(self):
        self.assertIn('href="/p/moergo-glove80"', SITE.product_page(E))

class Seo(unittest.TestCase):
    def test_product_title_says_what_owners_think(self):
        self.assertIn('<title>Kinesis Advantage: what 170 Hacker News owners think | HackerBuys</title>', SITE.product_page(E))
    def test_single_owner_wording(self):
        self.assertIn('what 1 Hacker News owner thinks', SITE.product_page(dict(E, own=1)))
    def test_description_includes_verdict(self):
        self.assertRegex(SITE.product_page(E), r'<meta name="description" content="93% of 170 verdicts')
    def test_canonical_is_absolute_and_ignores_view_params(self):
        self.assertIn('<link rel="canonical" href="https://hn.shellbear.me/p/kinesis-advantage">', SITE.product_page(E))
    def test_category_title_targets_best_of_search(self):
        self.assertIn('<title>Best keyboards according to Hacker News | HackerBuys</title>', SITE.list_page([E], cat='keyboards'))
    def test_everything_else_is_not_called_best(self):
        self.assertNotIn('Best everything else', SITE.list_page([E], cat='other_physical'))
    def test_prerendered_rows_contain_verdict_text_without_javascript(self):
        h = SITE.list_page([E], cat='keyboards')
        self.assertIn('Kinesis Advantage', h)
        self.assertIn('93%', h)
    def test_comment_text_is_prerendered(self):
        self.assertIn('comfy', re.sub(r'<script.*?</script>', '', SITE.product_page(E), flags=re.S))

class Indexing(unittest.TestCase):
    def test_three_owner_product_is_indexable(self):
        self.assertTrue(R.indexable(E))
        self.assertNotIn('noindex', SITE.product_page(E))
    def test_thin_product_is_noindex(self):
        self.assertFalse(R.indexable(dict(E, own=2)))
        self.assertIn('content="noindex,follow"', SITE.product_page(dict(E, own=2)))
    def test_brand_only_is_noindex(self):
        self.assertFalse(R.indexable(dict(E, bo=True)))
    def test_sitemap_lists_only_indexable_pages(self):
        x = R.sitemap(['/', '/c/keyboards'], [E, dict(E, k='thin', own=2)], '2026-11-04')
        self.assertIn('https://hn.shellbear.me/p/kinesis-advantage', x)
        self.assertIn('https://hn.shellbear.me/c/keyboards', x)
        self.assertNotIn('/p/thin', x)
    def test_robots_points_to_sitemap(self):
        self.assertIn('Sitemap: https://hn.shellbear.me/sitemap.xml', R.robots())

class Meta(unittest.TestCase):
    def test_reads_categories_and_tags_from_app_js(self):
        cats, tags = R.read_meta('site/app.js')
        self.assertEqual(cats['mice_trackpads'], 'Mice and trackpads')
        self.assertEqual(tags['bifl'][0], 'Buy it for life')
        self.assertGreater(len(cats), 30)

if __name__ == '__main__': unittest.main()
