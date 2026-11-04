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
