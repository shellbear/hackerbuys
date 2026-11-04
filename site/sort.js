// Sorting for the product table. Loaded by the page and by tests/site_sort.test.cjs.
(function (root) {
  function happy(p, view) {
    const pos = view === 'recent' ? p.rpos : p.pos, neg = view === 'recent' ? p.rneg : p.neg;
    return pos + neg ? pos / (pos + neg) : null;
  }
  const count = (p, view) => (view === 'recent' ? p.rown : view === 'long' ? p.lh : p.own);
  const value = {
    count,
    happy,
    longest: p => p.maxt,
    last: p => p.ly,
  };
  const defaultDir = key => (key === 'name' ? 'asc' : 'desc');

  function sortRows(rows, key, dir, view) {
    const sign = dir === 'asc' ? 1 : -1;
    const cmp = key === 'name'
      ? (a, b) => sign * a.n.localeCompare(b.n, undefined, { sensitivity: 'base' })
      : (a, b) => {
          const x = value[key](a, view), y = value[key](b, view);
          if (x === null || x === undefined) return y === null || y === undefined ? count(b, view) - count(a, view) : 1;
          if (y === null || y === undefined) return -1;
          // Ties always favour more owners, so 100% from 40 owners stays above 100% from 3.
          return sign * (x - y) || count(b, view) - count(a, view);
        };
    return [...rows].sort(cmp);
  }
  const api = { sortRows, defaultDir };
  if (typeof module !== 'undefined') module.exports = api; else root.TableSort = api;
})(this);
