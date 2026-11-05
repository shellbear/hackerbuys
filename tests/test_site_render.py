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

class Icons(unittest.TestCase):
    def test_pages_link_the_favicons(self):
        h = SITE.product_page(E)
        for tag in ('rel="icon" href="/favicon.svg"', 'rel="alternate icon" href="/favicon.ico"', 'rel="apple-touch-icon" href="/apple-touch-icon.png"'):
            self.assertIn(tag, h)

class Sharing(unittest.TestCase):
    def test_pages_have_a_large_share_image(self):
        h = SITE.product_page(E)
        for tag in ('property="og:image" content="https://hn.shellbear.me/og.png"', 'property="og:image:width" content="1200"', 'property="og:image:height" content="630"', 'property="og:image:alt"', 'name="twitter:card" content="summary_large_image"', 'name="twitter:image" content="https://hn.shellbear.me/og.png"'):
            self.assertIn(tag, h)
    def test_twitter_title_matches_page(self):
        self.assertIn('name="twitter:title" content="Kinesis Advantage: what 170 Hacker News owners think | HackerBuys"', SITE.product_page(E))

class ForAi(unittest.TestCase):
    TEXT = R.llms_txt(CATS, 42)
    def test_points_to_sitemap_and_catalogue(self):
        self.assertIn('https://hn.shellbear.me/sitemap.xml', self.TEXT)
        self.assertIn('https://hn.shellbear.me/data/index.json', self.TEXT)
    def test_lists_category_pages(self):
        self.assertIn('[Mice and trackpads](https://hn.shellbear.me/c/mice-trackpads)', self.TEXT)
    def test_explains_limits_for_quoting(self):
        self.assertIn('extracted by AI', self.TEXT)
    def test_starts_with_a_title(self):
        self.assertTrue(self.TEXT.startswith('# HackerBuys'))

class Meta(unittest.TestCase):
    def test_reads_categories_and_tags_from_app_js(self):
        cats, tags = R.read_meta('site/app.js')
        self.assertEqual(cats['mice_trackpads'], 'Mice and trackpads')
        self.assertEqual(tags['bifl'][0], 'Buy it for life')
        self.assertGreater(len(cats), 30)



class Models(unittest.TestCase):
    def test_line_name_is_removed(self):
        self.assertEqual(R.normalize_model('Quest 3', 'Quest'), '3')
    def test_case_is_merged(self):
        self.assertEqual(R.normalize_model('13 Mini', 'iPhone'), R.normalize_model('13 mini', 'iPhone'))
    def test_sizes_and_memory_are_removed(self):
        self.assertEqual(R.normalize_model('14-inch M3', 'MacBook Pro'), 'm3')
        self.assertEqual(R.normalize_model('M1 16GB', 'MacBook Air'), 'm1')
    def test_size_only_is_not_a_model(self):
        self.assertIsNone(R.normalize_model('16-inch', 'MacBook Pro'))
    def test_generation_suffix_is_removed(self):
        self.assertEqual(R.normalize_model('X1 Carbon Gen 9', 'ThinkPad X1'), 'x1 carbon')
    def test_vague_words_are_not_models(self):
        for bad in ('older', 'latest', 'model unspecified', 'original', ''):
            self.assertIsNone(R.normalize_model(bad, 'iPhone'), bad)
    def test_long_descriptions_are_not_models(self):
        self.assertIsNone(R.normalize_model('the one I bought from a friend last summer', 'iPhone'))
    def test_model_page_name_does_not_repeat_the_line(self):
        self.assertEqual(R.model_name('Lenovo ThinkPad', 'T480'), 'Lenovo ThinkPad T480')
        self.assertEqual(R.model_name('Lenovo ThinkPad X1', 'X1 Carbon'), 'Lenovo ThinkPad X1 Carbon')
    def test_model_extending_the_last_word_replaces_it(self):
        self.assertEqual(R.model_name('Sony WH-1000XM', 'WH-1000XM4'), 'Sony WH-1000XM4')
    def test_trailing_line_word_is_removed(self):
        self.assertEqual(R.normalize_model('M1 Air', 'MacBook Air'), 'm1')
    def test_distinctive_model_merges_across_lines_of_a_brand(self):
        self.assertTrue(R.merges_across_lines('t480'))
        self.assertTrue(R.merges_across_lines('x1 carbon'))
        self.assertTrue(R.merges_across_lines('4090'))
    def test_chip_names_and_years_stay_within_their_line(self):
        for mk in ('m1', '13', '2020', 'pro', '4a'):
            self.assertFalse(R.merges_across_lines(mk), mk)
    def test_child_links_to_parent_page(self):
        h = SITE.product_page(dict(E, k='kinesis-advantage-2', n='Kinesis Advantage 2', pk='kinesis-advantage', pn='Kinesis Advantage'))
        self.assertIn('href="/p/kinesis-advantage"', h)
    def test_parent_lists_its_models(self):
        h = SITE.product_page(dict(E, models=[['2', 'kinesis-advantage-2', 12]]))
        self.assertIn('href="/p/kinesis-advantage-2"', h)
    def test_child_is_not_counted_in_navigation_totals(self):
        s = R.Site(CATS, TAGS, 'x', [dict(E), dict(E, k='child', pk='kinesis-advantage')])
        self.assertEqual(len(s.live), 1)


class ModelNames(unittest.TestCase):
    def test_model_repeating_the_line_is_not_written_twice(self):
        for parent, label, want in (
            ('Logitech MX Master', 'MX Master 3', 'Logitech MX Master 3'),
            ('Raspberry Pi', 'Raspberry Pi 4', 'Raspberry Pi 4'),
            ('Microsoft Surface Pro', 'Surface Pro 3', 'Microsoft Surface Pro 3'),
            ('Samsung Galaxy S', 'Galaxy S4', 'Samsung Galaxy S4'),
            ('Framework Laptop', 'Framework 13', 'Framework Laptop 13'),
        ):
            self.assertEqual(R.model_name(parent, label), want)
    def test_model_ending_in_the_line_moves_the_rest_after_it(self):
        self.assertEqual(R.model_name('Apple MacBook Air', 'M1 MacBook Air'), 'Apple MacBook Air M1')
        self.assertEqual(R.model_name('Pebble', 'original Pebble'), 'Pebble original')
    def test_model_naming_only_the_line_gives_the_line(self):
        for parent, label in (
            ('IBM / Unicomp Model M', 'Model M'),
            ('Beelink mini PC', 'mini PC'),
            ('Zojirushi Rice cooker', 'rice cooker'),
            ('HP 15C', 'HP-15C'),
            ('AMD Radeon RX 7900 XTX', '7900'),
        ):
            self.assertEqual(R.model_name(parent, label), parent)
    def test_number_extending_a_short_last_word_replaces_it(self):
        self.assertEqual(R.model_name('Samsung Galaxy S', 'S5'), 'Samsung Galaxy S5')
        self.assertEqual(R.model_name('Leica Q', 'Q2'), 'Leica Q2')
        self.assertEqual(R.model_name('AMD Ryzen 7', '7800X3D'), 'AMD Ryzen 7800X3D')
    def test_short_last_word_does_not_swallow_a_longer_label(self):
        self.assertEqual(R.model_name('IBM Model M', 'SSK'), 'IBM Model M SSK')
        self.assertEqual(R.model_name('Acme M', 'Max'), 'Acme M Max')
    def test_unrelated_words_are_kept(self):
        self.assertEqual(R.model_name('Google Chromecast', 'with Google TV'), 'Google Chromecast with Google TV')

class RefineProduct(unittest.TestCase):
    def refine(self, brand, line, model=None, kind=None):
        return R.refine_product(dict(brand=brand, line=line, model=model, product_type=kind, category='laptops'))
    def test_framework_desktop_is_not_the_laptop(self):
        for line, model, kind in (('Desktop', None, 'desktop computer'), ('', 'Desktop', 'desktop computer'), ('', None, 'mini ITX gaming PC')):
            p = self.refine('Framework', line, model, kind)
            self.assertEqual((p['line'], p['category']), ('Desktop', 'desktops'))
    def test_framework_laptop_is_untouched(self):
        p = self.refine('Framework', 'Laptop 13', None, 'laptop')
        self.assertEqual((p['line'], p['category']), ('Laptop 13', 'laptops'))
    def test_bambu_x1_spellings_are_one_printer(self):
        for line, model in (('X1', 'X1C'), ('', 'X1C'), ('X1', None), ('X1 Carbon', 'X1C'), ('X1C', None), ('', 'X1-Carbon'), ('X1 Carbon', 'Combo')):
            p = self.refine('Bambu Lab', line, model, '3D printer')
            self.assertEqual((p['line'], p['model']), ('X1 Carbon', None), (line, model))
    def test_other_bambu_printers_are_untouched(self):
        p = self.refine('Bambu Lab', 'X1E', None, '3D printer')
        self.assertEqual(p['line'], 'X1E')
        p = self.refine('Bambu Lab', 'P1', 'P1S', '3D printer')
        self.assertEqual((p['line'], p['model']), ('P1', 'P1S'))
    def test_corsair_vengeance_splits_by_what_it_is(self):
        p = self.refine('Corsair', 'Vengeance', 'K70')
        self.assertEqual((p['line'], p['model'], p['category']), ('K70', None, 'keyboards'))
        p = self.refine('Corsair', 'Vengeance', 'a7500 AIR', 'desktop PC')
        self.assertEqual((p['line'], p['model'], p['category']), ('Vengeance a7500 AIR', None, 'desktops'))
        p = self.refine('Corsair', 'Vengeance', 'CMK64GX4M4A2400C14', 'memory kit')
        self.assertEqual((p['line'], p['category']), ('Vengeance', 'pc_components'))

class VerdictWording(unittest.TestCase):
    def test_singular_verdict(self):
        h = SITE.product_page(dict(E, own=3, pos=1, neg=0))
        self.assertNotIn('1 verdicts', h)
    def test_too_few_verdicts_show_no_percentage(self):
        self.assertEqual(R.happy_pct(dict(E, pos=2, neg=0)), '–')
        self.assertNotIn('100% of', SITE.product_page(dict(E, own=3, pos=2, neg=0)))
    def test_enough_verdicts_show_percentage(self):
        self.assertEqual(R.happy_pct(dict(E, pos=3, neg=1)), '75%')

class StrongerIndexing(unittest.TestCase):
    def test_few_verdicts_are_noindex(self):
        self.assertFalse(R.indexable(dict(E, own=9, pos=3, neg=1)))
        self.assertIn('noindex', SITE.product_page(dict(E, own=9, pos=3, neg=1)))
    def test_brand_without_a_product_line_is_noindex(self):
        self.assertFalse(R.indexable(dict(E, nl=True)))
    def test_noindex_page_is_left_out_of_sitemap(self):
        self.assertNotIn('/p/rheem', R.sitemap([], [dict(E, k='rheem', pos=1, neg=0)], '2026-11-05'))
    def test_strong_page_stays_indexable(self):
        self.assertTrue(R.indexable(E))

class Descriptions(unittest.TestCase):
    P = dict(E, pr=['ergonomics', 'build_quality'], co=['value'], lh=46)
    def desc(self, p):
        return re.search(r'<meta name="description" content="([^"]*)"', SITE.product_page(p)).group(1)
    def test_names_the_product_and_verdict(self):
        self.assertIn('93% of 170 verdicts on the Kinesis Advantage', self.desc(self.P))
    def test_uses_praise_and_criticism(self):
        d = self.desc(self.P)
        self.assertIn('Praised for ergonomics and build quality', d)
        self.assertIn('criticized for value', d)
    def test_an_aspect_is_not_both_praised_and_criticized(self):
        d = self.desc(dict(self.P, pr=['ergonomics', 'comfort'], co=['ergonomics', 'portability']))
        self.assertIn('criticized for portability', d)
        self.assertNotIn('criticized for ergonomics', d)
    def test_mentions_long_term_owners(self):
        self.assertIn('46 still happy after 3+ years', self.desc(self.P))
    def test_stays_short_enough_for_results(self):
        self.assertLessEqual(len(self.desc(dict(self.P, n='A very long product name ' * 3, pr=['ergonomics', 'build_quality', 'durability'], co=['value', 'software', 'support']))), 200)
    def test_praise_is_shown_on_the_page(self):
        self.assertIn('Praised for', re.sub(r'<head>.*</head>', '', SITE.product_page(self.P), flags=re.S))
    def test_no_reasons_still_gives_a_description(self):
        self.assertIn('Kinesis Advantage', self.desc(dict(E, pr=[], co=[])))

class CategoryContent(unittest.TestCase):
    ROWS = [dict(E, k=f'p{i}', n=f'Product {i}', own=100 - i * 30, w=.5 + i * .1) for i in range(3)]
    def test_summary_links_most_loved_and_most_owned(self):
        h = SITE.list_page(self.ROWS, cat='keyboards')
        self.assertIn('id="summary"', h)
        self.assertIn('Most loved', h)
        self.assertIn('<a href="/p/p2">Product 2</a>', h)
    def test_item_list_has_positions_and_absolute_urls(self):
        h = SITE.list_page(self.ROWS, cat='keyboards')
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', h, re.S).group(1))
        self.assertEqual(data['@type'], 'ItemList')
        self.assertEqual(data['itemListElement'][0]['position'], 1)
        self.assertEqual(data['itemListElement'][0]['url'], 'https://hn.shellbear.me/p/p0')
    def test_home_has_no_category_summary(self):
        self.assertNotIn('id="summary"', SITE.list_page(self.ROWS))



class LastMention(unittest.TestCase):
    def test_month_and_year_are_formatted(self):
        self.assertEqual(R.month_label('2026-10'), 'Oct 2026')
    def test_rows_show_month_and_year(self):
        self.assertIn('Oct 2026', SITE.list_page([dict(E, ld='2026-10')], cat='keyboards'))
    def test_rows_fall_back_to_year(self):
        self.assertIn('>2026<', SITE.list_page([E], cat='keyboards'))



class Refiling(unittest.TestCase):
    def test_lights_move_by_product_type(self):
        for t in ('smart bulb', 'desk lamp', 'monitor light bar', 'LED bulb', 'smart lighting system'):
            self.assertEqual(R.refile('smart_home', t, 'Acme', ''), 'lighting_desk', t)
    def test_desk_gear_moves_by_product_type(self):
        self.assertEqual(R.refile('desks', 'monitor arm', 'Ergotron', 'LX'), 'lighting_desk')
    def test_portable_and_vehicle_lights_stay_put(self):
        for t in ('bicycle light', 'bike light', 'flashlight', 'headlamp', 'bicycle radar light'):
            self.assertEqual(R.refile('bikes_mobility', t, 'Garmin', 'Varia'), 'bikes_mobility', t)
    def test_lightning_cables_and_light_phone_are_not_lights(self):
        self.assertEqual(R.refile('power', 'lightning cable', 'Apple', 'Lightning'), 'power')
        self.assertEqual(R.refile('phones', 'minimalist phone', 'Light', 'Phone'), 'phones')
    def test_known_names_move_when_the_earlier_sample_has_no_type(self):
        for brand, line in (('Philips', 'Hue'), ('Ergotron', 'Monitor arm'), ('BenQ', 'ScreenBar'), ('LIFX', '')):
            self.assertEqual(R.refile('smart_home', '', brand, line), 'lighting_desk', brand)
    def test_other_products_are_unchanged(self):
        self.assertEqual(R.refile('keyboards', 'mechanical keyboard', 'Keychron', 'Q1'), 'keyboards')

class MixedBrands(unittest.TestCase):
    def test_brand_across_categories_is_mixed(self):
        self.assertTrue(R.mixed_brand(['phones', 'tv_streaming', 'home_appliances', 'monitors']))
    def test_brand_in_one_category_is_not_mixed(self):
        self.assertFalse(R.mixed_brand(['kitchen_coffee'] * 4))
    def test_mostly_one_category_is_not_mixed(self):
        self.assertFalse(R.mixed_brand(['pc_components'] * 4 + ['desktops']))
    def test_too_little_evidence_is_not_mixed(self):
        self.assertFalse(R.mixed_brand(['tv_streaming', 'phones']))
    def test_one_kind_of_product_filed_under_several_categories_is_not_mixed(self):
        cats = ['other_physical'] * 4 + ['tablets'] * 3 + ['pc_components'] * 3
        self.assertFalse(R.mixed_brand(cats, ['drawing tablet'] * 5 + ['graphics tablet'] * 5))
    def test_plural_product_types_count_as_the_same_kind(self):
        self.assertFalse(R.mixed_brand(['smart_home', 'cameras', 'webcams_mics'], ['security camera', 'security cameras', 'ip camera', 'security camera', 'security cameras']))
    def test_many_kinds_of_product_stay_mixed(self):
        cats = ['phones', 'tv_streaming', 'home_appliances', 'monitors']
        self.assertTrue(R.mixed_brand(cats, ['smartphone', 'television', 'refrigerator', 'ssd']))
    def test_too_few_types_fall_back_to_categories(self):
        self.assertTrue(R.mixed_brand(['keyboards', 'pc_components', 'storage'], ['computer case', 'computer case', 'keyboard']))

class HomeCategory(unittest.TestCase):
    def test_most_common_category_wins(self):
        self.assertEqual(R.home_category(['keyboards'] * 3 + ['desktops']), 'keyboards')
    def test_named_category_beats_the_catch_all(self):
        self.assertEqual(R.home_category(['other_physical'] * 11 + ['tablets'] * 8 + ['pc_components'] * 7), 'tablets')
    def test_catch_all_stays_when_the_named_category_is_a_stray(self):
        self.assertEqual(R.home_category(['other_physical'] * 5 + ['keyboards']), 'other_physical')
    def test_ties_do_not_depend_on_comment_order(self):
        self.assertEqual(R.home_category(['tablets', 'ereaders']), 'ereaders')
        self.assertEqual(R.home_category(['ereaders', 'tablets']), 'ereaders')
    def test_mixed_brand_is_left_out_of_rankings_and_totals(self):
        s = R.Site(CATS, TAGS, 'x', [dict(E), dict(E, k='philips', mx=True)])
        self.assertEqual(len(s.live), 1)

class PrintersAndTypes(unittest.TestCase):
    def test_paper_printers_get_their_own_category(self):
        for t in ('laser printer', 'color laser printer', 'inkjet printer', 'document scanner', 'film scanner'):
            self.assertEqual(R.refile('printers_3d', t, 'Acme', ''), 'printers', t)
    def test_bare_printer_type_uses_the_brand(self):
        self.assertEqual(R.refile('printers_3d', 'printer', 'Brother', ''), 'printers')
        self.assertEqual(R.refile('printers_3d', 'printer', 'Prusa', 'MK4'), 'printers_3d')
    def test_3d_printers_and_other_scanners_stay(self):
        self.assertEqual(R.refile('printers_3d', '3d printer', 'Bambu Lab', 'A1'), 'printers_3d')
        self.assertEqual(R.refile('printers_3d', 'resin printer', 'Elegoo', ''), 'printers_3d')
        self.assertEqual(R.refile('tools_edc', 'barcode scanner', 'Zebra', ''), 'tools_edc')
        self.assertEqual(R.refile('printers_3d', '3d scanner', 'Revopoint', ''), 'printers_3d')
    def test_printer_names_work_without_a_type(self):
        self.assertEqual(R.refile('other_physical', '', 'HP', 'LaserJet'), 'printers')
    def test_product_type_corrects_clear_misfiles(self):
        self.assertEqual(R.refile('keyboards', 'ergonomic mouse', 'Logitech', 'Ergo'), 'mice_trackpads')
        self.assertEqual(R.refile('keyboards', 'desktop pc', 'Corsair', 'Vengeance'), 'desktops')
        self.assertEqual(R.refile('calculators', 'home computer', 'Texas Instruments', 'TI-99'), 'desktops')
        self.assertEqual(R.refile('cameras', 'webcam', 'Logitech', ''), 'webcams_mics')
        self.assertEqual(R.refile('power', 'wireless earbuds', 'Anker', 'Soundcore'), 'headphones')

class CleanMentions(unittest.TestCase):
    def m(self, key, disp=None, cb='', cl=''):
        return dict(key=key, disp=disp or key, cb=cb, cl=cl)
    def keys(self, ms):
        return [x['key'] for x in R.clean_mentions(ms)]
    def test_things_that_are_not_owned_hardware_are_dropped(self):
        for k in ('android', 'google-android', 'microsoft-windows', 'mozilla-firefox', 'google-chrome', 'waymo', 'tesla-model-3'):
            self.assertEqual(self.keys([self.m(k)]), [], k)
    def test_hardware_with_similar_names_stays(self):
        for k in ('microsoft-windows-phone', 'tesla-powerwall', 'openwrt-one', 'starlink', 'google-chromecast', 'sony-android-tv'):
            self.assertEqual(self.keys([self.m(k)]), [k])
    def test_known_aliases_merge_and_take_the_target_name(self):
        ms = R.clean_mentions([self.m('raspberry-pi', 'Raspberry Pi', 'raspberry pi', ''), self.m('raspberry-pi-raspberry-pi', 'Raspberry Pi', 'raspberry pi', 'Raspberry Pi')])
        self.assertEqual({x['key'] for x in ms}, {'raspberry-pi'})
        self.assertEqual({(x['cb'], x['cl']) for x in ms}, {('raspberry pi', '')})
    def test_brand_prefixes_merge(self):
        ms = R.clean_mentions([self.m('boox-palma', 'Boox Palma'), self.m('boox-palma', 'Boox Palma'), self.m('onyx-boox-palma', 'Onyx Boox Palma')])
        self.assertEqual([(x['key'], x['disp']) for x in ms], [('boox-palma', 'Boox Palma')] * 3)
    def test_spelling_variants_merge_into_the_more_common(self):
        ms = [self.m('casio-f-91w', 'Casio F-91W')] * 3 + [self.m('casio-f91w', 'Casio F91W')]
        self.assertEqual({x['disp'] for x in R.clean_mentions(ms)}, {'Casio F-91W'})
    def test_different_products_stay_apart(self):
        self.assertEqual(sorted(set(self.keys([self.m('boox-note'), self.m('samsung-note')]))), ['boox-note', 'samsung-note'])
    def test_input_is_not_changed(self):
        one = self.m('onyx-boox-palma')
        R.clean_mentions([one])
        self.assertEqual(one['key'], 'onyx-boox-palma')

class GenericProducts(unittest.TestCase):
    def test_nouns_and_unknown_brands_are_generic(self):
        for k in ('laptop', 'phone', 'heat-pump', 'android-tablet', 'unknown-chromebook', 'generic-fountain-pen'):
            self.assertTrue(R.generic_product(k), k)
    def test_real_products_are_not(self):
        for k in ('framework-laptop', 'redox', 'dactyl-manuform', 'ikea-standing-desk', 'bialetti-moka-pot'):
            self.assertFalse(R.generic_product(k), k)

class CommentLabels(unittest.TestCase):
    def test_non_owner_label_does_not_overclaim(self):
        s = R.Site(CATS, TAGS, 'x', [dict(E)])
        out = s._comment(dict(s='positive', fh=False, t='x', i=1, id=1, by='a', d='2026-01-01', th='', root=None))
        self.assertIn('Doesn’t say they own it', out)
        self.assertNotIn('Hasn’t owned it', out)

class BrandAsProduct(unittest.TestCase):
    def test_benq_light_is_a_screenbar(self):
        self.assertEqual(R.line_for('BenQ', '', 'lighting_desk'), 'ScreenBar')
    def test_named_line_is_kept(self):
        self.assertEqual(R.line_for('BenQ', 'WiT', 'lighting_desk'), 'WiT')
    def test_benq_monitor_is_unchanged(self):
        self.assertEqual(R.line_for('BenQ', '', 'monitors'), '')

class FewOwners(unittest.TestCase):
    THIN = dict(E, k='thin', n='Thin Product', own=2, pos=2, neg=0)
    def test_thin_category_lists_products_with_two_owners(self):
        h = SITE.list_page([E], cat='keyboards', few=[self.THIN])
        self.assertIn('Few owners so far', h)
        self.assertIn('href="/p/thin"', h)
    def test_no_section_without_products(self):
        self.assertNotIn('Few owners so far', SITE.list_page([E], cat='keyboards', few=[]))


if __name__ == '__main__': unittest.main()
