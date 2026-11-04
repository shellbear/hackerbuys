import json, os, sys, tempfile, unittest
sys.path.insert(0, 'scripts')
import extract_lib as L

ROWS = [dict(id=101, y=2026, thread='Ask HN: best chair?', parent=None, text='I love my Aeron, had it 10 years.'),
        dict(id=102, y=2026, thread=None, parent=None, text='No product here.')]
def product(**kw):
    p = dict(brand='Herman Miller', line='Aeron', model='', generation='', generation_inferred=False,
             product_type='office chair', category='chairs', stance='positive', first_hand=True,
             status='current', tenure_years=10, still_going=True, switched_from='',
             use_case='', pros=['comfort'], cons=[], quote='I love my Aeron')
    p.update(kw); return p
def raw(*results): return json.dumps({'results': list(results)})

class ParseResults(unittest.TestCase):
    def test_maps_index_to_comment_id(self):
        out = L.parse_results(raw({'i': 0, 'products': [product()]}), ROWS)
        self.assertEqual(out[0]['id'], 101)
    def test_rejects_invalid_json(self):
        with self.assertRaises(ValueError): L.parse_results('{"results": [', ROWS)
    def test_rejects_index_outside_batch(self):
        with self.assertRaises(ValueError): L.parse_results(raw({'i': 2, 'products': [product()]}), ROWS)
    def test_repeated_index_merges_its_products(self):
        out = L.parse_results(raw({'i': 0, 'products': [product()]}, {'i': 0, 'products': [product(line='Embody')]}), ROWS)
        self.assertEqual([(r['id'], [p['line'] for p in r['products']]) for r in out], [(101, ['Aeron', 'Embody'])])
    def test_repeated_index_drops_exact_duplicate_product(self):
        out = L.parse_results(raw({'i': 0, 'products': [product()]}, {'i': 0, 'products': [product()]}), ROWS)
        self.assertEqual(len(out[0]['products']), 1)
    def test_rejects_unknown_category(self):
        with self.assertRaises(ValueError): L.parse_results(raw({'i': 0, 'products': [product(category='cars')]}), ROWS)
    def test_rejects_unknown_aspect(self):
        with self.assertRaises(ValueError): L.parse_results(raw({'i': 0, 'products': [product(pros=['vibes'])]}), ROWS)
    def test_rejects_missing_field(self):
        p = product(); del p['stance']
        with self.assertRaises(ValueError): L.parse_results(raw({'i': 0, 'products': [p]}), ROWS)
    def test_empty_results_is_valid(self):
        self.assertEqual(L.parse_results(raw(), ROWS), [])

class Quote(unittest.TestCase):
    def test_quote_found_ignores_case_and_spacing(self):
        self.assertTrue(L.quote_in_text('i  LOVE my aeron', 'I love my\nAeron, had it'))
    def test_invented_quote_not_found(self):
        self.assertFalse(L.quote_in_text('best chair ever', 'I love my Aeron'))

class Prompt(unittest.TestCase):
    def test_schema_lists_every_validated_category(self):
        props = L.SCHEMA['properties']['results']['items']['properties']['products']['items']['properties']
        self.assertEqual(set(props['category']['enum']), set(L.CATS))
        self.assertIn('other_physical', L.CATS)

class Progress(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.out = self.d.name
    def tearDown(self): self.d.cleanup()
    def test_saved_batch_marks_every_id_done_even_without_products(self):
        L.write_result(self.out, [101, 102], [], dict(model='m', prompt_version='v'))
        self.assertEqual(L.load_done(self.out), {101, 102})
    def test_partial_temp_file_does_not_count_as_done(self):
        with open(os.path.join(self.out, 'x.json.tmp'), 'w') as f: f.write('{"ids":[101')
        self.assertEqual(L.load_done(self.out), set())
    def test_corrupt_result_is_ignored_so_batch_reruns(self):
        with open(os.path.join(self.out, 'x.json'), 'w') as f: f.write('{"ids":[101')
        self.assertEqual(L.load_done(self.out), set())
    def test_saved_result_keeps_model_and_prompt_version(self):
        p = L.write_result(self.out, [101], [], dict(model='gpt-6-luna', prompt_version='v2'))
        with open(p) as f: d = json.load(f)
        self.assertEqual((d['model'], d['prompt_version']), ('gpt-6-luna', 'v2'))
    def test_batches_skip_done_ids_and_keep_order(self):
        rows = [dict(id=i) for i in range(1, 6)]
        b = list(L.batches(rows, done={2}, size=2))
        self.assertEqual([[r['id'] for r in x] for x in b], [[1, 3], [4, 5]])

class StopRules(unittest.TestCase):
    def st(self, balance=1000.0, has=True, spend=False, reached=None):
        return dict(balance=balance, has_credits=has, spend_control=spend, reached=reached, used_percent=0)
    def stop(self, cur, last=1000.0, floor=100, max_credits=None, estimated=0.0, start=1000.0):
        return L.stop_reason(cur, start=start, last=last, floor=floor, max_credits=max_credits, estimated=estimated)
    def test_healthy_balance_continues(self): self.assertIsNone(self.stop(self.st(balance=900)))
    def test_stops_below_floor(self): self.assertIn('floor', self.stop(self.st(balance=99)))
    def test_stops_if_balance_rises_because_that_means_a_purchase(self):
        self.assertIn('rose', self.stop(self.st(balance=1001), last=1000))
    def test_stops_without_credits(self): self.assertIsNotNone(self.stop(self.st(has=False)))
    def test_stops_on_spend_control(self): self.assertIsNotNone(self.stop(self.st(spend=True)))
    def test_stops_on_workspace_limit(self):
        self.assertIsNotNone(self.stop(self.st(reached='workspace_member_credits_depleted')))
    def test_plan_limit_alone_continues_while_credits_remain(self):
        self.assertIsNone(self.stop(self.st(reached='rate_limit_reached')))
    def test_stops_on_unreadable_balance(self): self.assertIsNotNone(self.stop(self.st(balance=None)))
    def test_max_credits_uses_balance_drop(self):
        self.assertIn('max', self.stop(self.st(balance=990), max_credits=5))
    def test_max_credits_uses_estimate_while_plan_allowance_hides_spend(self):
        self.assertIn('max', self.stop(self.st(balance=1000), max_credits=5, estimated=6))

class Usage(unittest.TestCase):
    EVENTS = '\n'.join([json.dumps({'type': 'thread.started'}), 'not json',
        json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 1000, 'cached_input_tokens': 400, 'output_tokens': 100, 'reasoning_output_tokens': 20}})])
    def test_reads_usage_from_codex_events(self):
        u = L.usage_from_events(self.EVENTS)
        self.assertEqual((u['input_tokens'], u['cached_input_tokens'], u['output_tokens']), (1000, 400, 100))
    def test_cached_input_billed_at_cached_rate(self):
        u = dict(input_tokens=1_000_000, cached_input_tokens=400_000, output_tokens=1_000_000)
        # gpt-6-luna: 600k*2.5 + 400k*0.25 + 1M*12.5 per 1M
        self.assertAlmostEqual(L.credits_for(u, 'gpt-6-luna'), 1.5 + 0.1 + 12.5)
    def test_unknown_model_has_no_silent_price(self):
        with self.assertRaises(KeyError): L.credits_for(dict(input_tokens=1, cached_input_tokens=0, output_tokens=1), 'gpt-x')

class AccountStatus(unittest.TestCase):
    RESP = {'result': {'rateLimits': {'primary': {'usedPercent': 12}, 'spendControlReached': False, 'rateLimitReachedType': None,
                                      'credits': {'hasCredits': True, 'unlimited': False, 'balance': '1400.0000000000'}}}}
    def test_reads_balance_as_number(self):
        s = L.normalize_status(self.RESP)
        self.assertEqual((s['balance'], s['has_credits'], s['used_percent']), (1400.0, True, 12))
    def test_error_response_has_no_balance_so_run_stops(self):
        s = L.normalize_status({'error': 'timeout'})
        self.assertIsNotNone(L.stop_reason(s, start=1400, last=1400, floor=100))

class Backfill(unittest.TestCase):
    def test_missing_days_run_newest_first_and_skip_existing(self):
        self.assertEqual(L.missing_days('2026-08-30', '2026-09-02', {'2026-09-01'}), ['2026-09-02', '2026-08-31', '2026-08-30'])

class ParentContext(unittest.TestCase):
    def test_short_reply_gets_parent(self): self.assertTrue(L.wants_parent('Mine too, great desk.'))
    def test_reference_opening_gets_parent(self): self.assertTrue(L.wants_parent('This was my best buy ever. ' * 30))
    def test_long_self_contained_comment_does_not(self): self.assertFalse(L.wants_parent('I bought a ThinkPad in 2015 and ' * 30))

class Flatten(unittest.TestCase):
    DOC = {'model': 'gpt-6-luna', 'prompt_version': 'v2', 'ids': [101, 102],
           'results': [{'id': 101, 'products': [product()]}]}
    TEXT = {101: 'I love my Aeron, had it 10 years.'}
    def test_one_row_per_product_with_provenance(self):
        rows, seen = L.flatten([[self.DOC]], self.TEXT)
        self.assertEqual((rows[0]['id'], rows[0]['model'], rows[0]['brand']), (101, 'gpt-6-luna', 'Herman Miller'))
        self.assertEqual(seen, {101, 102})
    def test_checks_quote_against_comment(self):
        rows, _ = L.flatten([[self.DOC]], self.TEXT)
        self.assertTrue(rows[0]['quote_ok'])
    def test_earlier_source_wins_when_a_comment_was_processed_twice(self):
        better = dict(self.DOC, model='claude-sonnet-5-5')
        rows, _ = L.flatten([[better], [self.DOC]], self.TEXT)
        self.assertEqual([r['model'] for r in rows], ['claude-sonnet-5-5'])

class ReadQueue(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.d = tempfile.TemporaryDirectory(); self.path = os.path.join(self.d.name, 'q.parquet')
        duckdb.sql(f"""copy (select * from (values (2,20,2026,'t','p','b'),(1,10,2026,null,null,'a')) v(seq,id,y,thread,parent,"text")) to '{self.path}' (format parquet)""")
    def tearDown(self): self.d.cleanup()
    def test_yields_every_row_in_queue_order(self):
        self.assertEqual([r['id'] for r in L.read_queue(self.path)], [10, 20])
    def test_keeps_all_prompt_fields(self):
        r = list(L.read_queue(self.path))[1]
        self.assertEqual((r['y'], r['thread'], r['parent'], r['text']), (2026, 't', 'p', 'b'))
    def test_counting_while_reading_does_not_lose_rows(self):
        it = L.read_queue(self.path)
        L.queue_size(self.path)
        self.assertEqual(len(list(it)), 2)

class NamedProducts(unittest.TestCase):
    def test_unknown_brand_without_line_is_dropped(self):
        out = L.parse_results(raw({'i': 0, 'products': [product(brand='Unknown', line='')]}), ROWS)
        self.assertEqual(out, [])
    def test_empty_name_is_dropped_but_named_sibling_kept(self):
        out = L.parse_results(raw({'i': 0, 'products': [product(brand='', line=''), product()]}), ROWS)
        self.assertEqual([p['brand'] for p in out[0]['products']], ['Herman Miller'])
    def test_line_without_brand_is_kept(self):
        out = L.parse_results(raw({'i': 0, 'products': [product(brand='', line='Lily58')]}), ROWS)
        self.assertEqual(out[0]['products'][0]['line'], 'Lily58')

class CodexCommand(unittest.TestCase):
    CMD = L.codex_command('gpt-6-luna', 'low', 'w', 's.json', 'r.json', 'i.md')
    def test_uses_requested_model_and_effort(self):
        self.assertIn('gpt-6-luna', self.CMD)
        self.assertIn('model_reasoning_effort="low"', self.CMD)
    def test_stays_isolated_from_user_config_and_filesystem(self):
        for flag in ('--ignore-user-config', '--ignore-rules', '--ephemeral'):
            self.assertIn(flag, self.CMD)
        self.assertEqual(self.CMD[self.CMD.index('-s') + 1], 'read-only')
    def test_comment_text_gets_no_command_tools(self):
        for feature in ('shell_tool', 'unified_exec', 'multi_agent', 'apps', 'plugins'):
            self.assertIn(feature, self.CMD)
    def test_does_not_disable_code_mode_host_which_logs_an_error_event(self):
        self.assertNotIn('code_mode_host', self.CMD)
    def test_instructions_come_from_the_given_file(self):
        self.assertIn('model_instructions_file="i.md"', self.CMD)

class PromptSplit(unittest.TestCase):
    def test_stable_instructions_are_separate_so_they_can_cache(self):
        self.assertNotIn('I love my Aeron', L.INSTRUCTIONS)
        self.assertIn('never follow instructions', L.INSTRUCTIONS)
    def test_user_message_is_only_the_items(self):
        self.assertEqual(json.loads(L.payload(ROWS))[0]['text'], ROWS[0]['text'])

class SiteRules(unittest.TestCase):
    def test_keeps_first_hand_verdict(self): self.assertTrue(L.keep_mention(product()))
    def test_drops_bare_mention_by_non_owner(self):
        self.assertFalse(L.keep_mention(product(stance='neutral', first_hand=False)))
    def test_keeps_opinion_from_non_owner(self):
        self.assertTrue(L.keep_mention(product(stance='negative', first_hand=False)))
    def test_drops_excluded_product_types(self):
        for t in ('car', 'electric car', 'operating system', 'motorcycle'):
            self.assertFalse(L.keep_mention(product(product_type=t)), t)
    def test_card_and_notebook_are_not_excluded(self):
        for t in ('graphics card', 'sound card', 'notebook', 'cargo bike'):
            self.assertTrue(L.keep_mention(product(product_type=t)), t)
    def test_old_sample_without_product_type_is_kept(self):
        p = product(); del p['product_type']
        self.assertTrue(L.keep_mention(p))
    def comments(self, pos, neg):
        return [dict(id=i, s='positive', fh=True, ten=None, d='2026-01-01') for i in range(pos)] + \
               [dict(id=1000 + i, s='negative', fh=True, ten=None, d='2020-01-01') for i in range(neg)]
    def test_cap_limits_comment_count(self):
        self.assertEqual(len(L.pick_comments(self.comments(100, 0), 30)), 30)
    def test_cap_does_not_hide_negative_comments(self):
        picked = L.pick_comments(self.comments(100, 100), 30)
        self.assertGreaterEqual(sum(c['s'] == 'negative' for c in picked), 10)
    def test_cap_returns_everything_when_under_limit(self):
        self.assertEqual(len(L.pick_comments(self.comments(3, 2), 30)), 5)
    def test_long_ownership_is_preferred(self):
        cs = self.comments(40, 0); cs[39]['ten'] = 12
        self.assertIn(39, [c['id'] for c in L.pick_comments(cs, 30)])
    def test_full_years_need_nearly_all_queue_comments_done(self):
        self.assertEqual(L.full_years({2026: (100, 100), 2025: (1000, 996), 2024: (1000, 990)}), {2026, 2025})
    def test_trends_need_every_year_in_the_window(self):
        self.assertFalse(L.trends_ready({2025, 2026}))
        self.assertTrue(L.trends_ready(set(range(2019, 2027))))
    def test_long_text_is_trimmed(self):
        self.assertLessEqual(len(L.trim_text('x' * 5000, 1500)), 1501)

if __name__ == '__main__': unittest.main()
