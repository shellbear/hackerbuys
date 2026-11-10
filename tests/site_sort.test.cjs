const test = require('node:test'); const assert = require('node:assert');
const { sortRows, defaultDir } = require('../site/sort.js');
const P = (n, own, pos, neg, ly, extra = {}) => ({ n, own, pos, neg, ly, rown: 0, rpos: 0, rneg: 0, lh: 0, maxt: null, ...extra });
const names = r => r.map(p => p.n);
const rows = [P('Beta', 10, 9, 1, 2024), P('alpha', 50, 25, 25, 2026), P('Gamma', 3, 3, 0, 2020)];

test('owners sorts largest first by default', () => {
  assert.equal(defaultDir('count'), 'desc');
  assert.deepEqual(names(sortRows(rows, 'count', 'desc', 'loved')), ['alpha', 'Beta', 'Gamma']);
});
test('reversing owners puts the smallest first', () => {
  assert.deepEqual(names(sortRows(rows, 'count', 'asc', 'loved')), ['Gamma', 'Beta', 'alpha']);
});
test('product name sorts A to Z by default, ignoring case', () => {
  assert.equal(defaultDir('name'), 'asc');
  assert.deepEqual(names(sortRows(rows, 'name', 'asc', 'loved')), ['alpha', 'Beta', 'Gamma']);
});
test('last mention sorts newest first', () => {
  assert.deepEqual(names(sortRows(rows, 'last', 'desc', 'loved')), ['alpha', 'Beta', 'Gamma']);
});
test('happy sorts by share of positive and negative verdicts', () => {
  assert.deepEqual(names(sortRows(rows, 'happy', 'desc', 'loved')), ['Gamma', 'Beta', 'alpha']);
});
test('happy ties go to the product with more owners in both directions', () => {
  const t = [P('small', 3, 3, 0, 2026), P('big', 40, 40, 0, 2026)];
  assert.deepEqual(names(sortRows(t, 'happy', 'desc', 'loved')), ['big', 'small']);
  assert.deepEqual(names(sortRows(t, 'happy', 'asc', 'loved')), ['big', 'small']);
});
test('products with no verdict stay last in both directions', () => {
  const t = [P('none', 9, 0, 0, 2026), P('bad', 5, 0, 5, 2026), P('good', 5, 5, 0, 2026)];
  assert.equal(names(sortRows(t, 'happy', 'desc', 'loved')).at(-1), 'none');
  assert.equal(names(sortRows(t, 'happy', 'asc', 'loved')).at(-1), 'none');
});
test('recent view uses counts and verdicts since 2024', () => {
  const t = [P('oldhit', 90, 90, 0, 2026, { rown: 1, rpos: 0, rneg: 1 }), P('newhit', 5, 5, 0, 2026, { rown: 4, rpos: 4, rneg: 0 })];
  assert.deepEqual(names(sortRows(t, 'count', 'desc', 'recent')), ['newhit', 'oldhit']);
  assert.deepEqual(names(sortRows(t, 'happy', 'desc', 'recent')), ['newhit', 'oldhit']);
});
test('long-haul view counts happy long-term owners', () => {
  const t = [P('a', 90, 9, 0, 2026, { lh: 1, maxt: 20 }), P('b', 5, 5, 0, 2026, { lh: 4, maxt: 6 })];
  assert.deepEqual(names(sortRows(t, 'count', 'desc', 'long')), ['b', 'a']);
  assert.deepEqual(names(sortRows(t, 'longest', 'desc', 'long')), ['a', 'b']);
});
test('sorting does not change the input order', () => {
  const before = names(rows); sortRows(rows, 'count', 'desc', 'loved');
  assert.deepEqual(names(rows), before);
});
test('verdict sorts by confidence score, best first by default', () => {
  assert.equal(defaultDir('verdict'), 'desc');
  const t = [P('mid', 50, 40, 10, 2026, { w: 0.7 }), P('top', 90, 88, 2, 2026, { w: 0.92 }), P('low', 40, 5, 35, 2026, { w: 0.08 })];
  assert.deepEqual(names(sortRows(t, 'verdict', 'desc', 'loved')), ['top', 'mid', 'low']);
  assert.deepEqual(names(sortRows(t, 'verdict', 'asc', 'loved')), ['low', 'mid', 'top']);
});
test('verdict uses the recent score in the recent view', () => {
  const t = [P('oldhit', 90, 90, 0, 2026, { w: 0.9, rw: 0.1, rown: 3 }), P('newhit', 9, 9, 0, 2026, { w: 0.5, rw: 0.8, rown: 3 })];
  assert.deepEqual(names(sortRows(t, 'verdict', 'desc', 'recent')), ['newhit', 'oldhit']);
});

const { canSwap, listTitle } = require('../site/sort.js');
const O = 'https://hn.shellbear.me';
test('site pages can swap without a reload', () => {
  for (const p of ['/', '/?view=owned', '/p/kinesis-advantage', '/c/mice-trackpads', '/t/bifl', '/c/keyboards?view=long'])
    assert.equal(canSwap(new URL(O + p), O), true, p);
});
test('other sites and files stay normal page loads', () => {
  assert.equal(canSwap(new URL('https://news.ycombinator.com/item?id=1'), O), false);
  for (const p of ['/sitemap.xml', '/robots.txt', '/data/index.json', '/app.js', '/nope', '/p/a/b', '/c/', '/404'])
    assert.equal(canSwap(new URL(O + p), O), false, p);
});
test('list titles match the generated pages', () => {
  assert.equal(listTitle({ cat: 'keyboards', name: 'Keyboards' }), 'Best keyboards according to Hacker News | HackerBuys');
  assert.equal(listTitle({ cat: 'other_physical', name: 'Everything else' }), 'Other products recommended on Hacker News | HackerBuys');
  assert.equal(listTitle({ tag: 'bifl', name: 'Buy it for life' }), 'Buy it for life: products according to Hacker News | HackerBuys');
  assert.equal(listTitle({}), 'HackerBuys: The stuff Hacker News actually recommends.');
});

const { searchProducts } = require('../site/sort.js');
const S = (n, own, ty = [], c = 'keyboards') => ({ n, own, ty, c, k: n.toLowerCase().replace(/\W+/g, '-') });
const CATS = { keyboards: 'Keyboards', desks: 'Desks' };
const found = (list, q) => names(searchProducts(list, q, CATS));
test('search ignores case and word order', () => {
  assert.deepEqual(found([S('Kinesis Advantage', 9)], 'advantage KINESIS'), ['Kinesis Advantage']);
});
test('search ignores accents in both directions', () => {
  assert.deepEqual(found([S('HÅG Capisco', 9)], 'hag cap'), ['HÅG Capisco']);
  assert.deepEqual(found([S('Hag Capisco', 9)], 'håg'), ['Hag Capisco']);
});
test('every word must match', () => {
  assert.deepEqual(found([S('Kinesis Advantage', 9)], 'kinesis freestyle'), []);
});
test('product type finds products that do not name it', () => {
  assert.deepEqual(found([S('Fully Jarvis', 9, ['standing desk'], 'desks')], 'standing desk'), ['Fully Jarvis']);
});
test('category name is searchable', () => {
  assert.deepEqual(found([S('Fully Jarvis', 9, [], 'desks')], 'desks'), ['Fully Jarvis']);
});
test('name matches rank above type matches, however many owners', () => {
  const list = [S('Logitech MX', 500, ['ergonomic mouse']), S('Ergotron Mouse Arm', 5)];
  assert.deepEqual(found(list, 'mouse'), ['Ergotron Mouse Arm', 'Logitech MX']);
});
test('a name starting with the query ranks first, then more owners', () => {
  const list = [S('Apple Kindle Case', 900), S('Kindle', 10), S('Amazon Kindle Paperwhite', 300)];
  assert.deepEqual(found(list, 'kindle'), ['Kindle', 'Apple Kindle Case', 'Amazon Kindle Paperwhite']);
});
test('words match at word starts, not inside words', () => {
  assert.deepEqual(found([S('Sharpie Pen', 5), S('Pen Plotter', 5)], 'harp'), []);
});
test('empty or space-only search returns nothing', () => {
  assert.deepEqual(found([S('Kindle', 10)], '   '), []);
});
test('results are capped', () => {
  const many = Array.from({ length: 30 }, (_, i) => S('Kindle ' + i, i));
  assert.equal(searchProducts(many, 'kindle', CATS).length, 8);
});

test('products under the ranking threshold come after better-supported ones', () => {
  const list = [S('standing desk', 2, [], 'desks'), S('IKEA Standing desk', 19, [], 'desks')];
  assert.deepEqual(found(list, 'standing desk'), ['IKEA Standing desk', 'standing desk']);
});

const { categorySummary } = require('../site/sort.js');
test('category summary lists most loved and most owned', () => {
  const rows = [{ n: 'A', k: 'a', own: 5, w: .9 }, { n: 'B', k: 'b', own: 50, w: .7 }, { n: 'C', k: 'c', own: 20, w: .8 }, { n: 'D', k: 'd', own: 9, w: .1 }];
  const s = categorySummary(rows);
  assert.deepEqual(s.loved.map(p => p.k), ['a', 'c', 'b']);
  assert.deepEqual(s.owned.map(p => p.k), ['b', 'c', 'd']);
});
test('too few products gives no category summary', () => {
  assert.equal(categorySummary([{ n: 'A', k: 'a', own: 5, w: .9 }]), null);
});
test('happy percentage is hidden under three verdicts and sorts last', () => {
  const t = [P('thin', 3, 2, 0, 2026), P('solid', 9, 3, 1, 2026)];
  assert.deepEqual(names(sortRows(t, 'happy', 'desc', 'loved')), ['solid', 'thin']);
});

const { monthLabel } = require('../site/sort.js');
test('last mention sorts by month, not just year', () => {
  const t = [P('jan', 5, 5, 0, 2026, { ld: '2026-01' }), P('oct', 5, 5, 0, 2026, { ld: '2026-10' }), P('old', 5, 5, 0, 2019, { ld: '2019-12' })];
  assert.deepEqual(names(sortRows(t, 'last', 'desc', 'loved')), ['oct', 'jan', 'old']);
  assert.deepEqual(names(sortRows(t, 'last', 'asc', 'loved')), ['old', 'jan', 'oct']);
});
test('month label is short and unambiguous', () => {
  assert.equal(monthLabel({ ld: '2026-10', ly: 2026 }), 'Oct 2026');
  assert.equal(monthLabel({ ly: 2026 }), '2026');
});

const { fewOwners } = require('../site/sort.js');
test('few owners lists two-owner products in thin categories only', () => {
  const rows = [{ c: 'a', own: 9, k: 'x' }, { c: 'a', own: 2, k: 'y', n: 'Y' }, { c: 'a', own: 2, k: 'z', n: 'Z', bo: true }, { c: 'a', own: 2, k: 'm', n: 'M', mx: true }, { c: 'a', own: 2, k: 'k', n: 'K', pk: 'x' }, { c: 'b', own: 2, k: 'w', n: 'W' }];
  assert.deepEqual(fewOwners(rows, 'a', 1).map(p => p.k), ['y']);
  assert.deepEqual(fewOwners(rows, 'a', 25), []);
});

const { dayLabel } = require('../site/sort.js');
test('day label matches the page: day, short month, year', () => {
  assert.equal(dayLabel('2026-11-07'), '7 Nov 2026');
  assert.equal(dayLabel('2026-01-30'), '30 Jan 2026');
});

const { tenureLabel } = require('../site/sort.js');
test('tenure reads in weeks, months or years, like the page', () => {
  assert.deepEqual([0.01, 0.06, 0.17, 0.5, 1, 2.5].map(tenureLabel), ['1 week', '3 weeks', '2 months', '6 months', '1 year', '2.5 years']);
});
