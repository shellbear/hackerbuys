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
    verdict: (p, view) => (view === 'recent' ? p.rw : p.w),
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
  // Only pages the script can rebuild itself; everything else stays a normal page load.
  const canSwap = (url, origin) => url.origin === origin && /^\/((p|c|t)\/[^/]+)?$/.test(url.pathname);
  function listTitle({ cat, tag, name }) {
    if (cat === 'other_physical') return 'Other products recommended on Hacker News | HackerBuys';
    if (cat) return `Best ${name.toLowerCase()} according to Hacker News | HackerBuys`;
    if (tag) return `${name}: products according to Hacker News | HackerBuys`;
    return 'HackerBuys: The stuff Hacker News actually recommends.';
  }
  const fold = t => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[øØ]/g, 'o').toLowerCase();
  const startsWord = (text, word) => text.startsWith(word) || text.includes(' ' + word) || text.includes('-' + word);
  const MAX_RESULTS = 8;
  const MIN_RANKED = 3;
  // Runs in the browser over the catalogue file: no server, and nothing typed leaves the page.
  function searchProducts(products, query, cats) {
    const words = fold(query).split(/\s+/).filter(Boolean);
    if (!words.length) return [];
    const scored = [];
    for (const p of products) {
      const name = fold(p.n), rest = fold([...(p.ty || []), cats[p.c] || ''].join(' '));
      if (!words.every(w => startsWord(name, w) || startsWord(rest, w))) continue;
      const inName = words.every(w => startsWord(name, w));
      scored.push({ p, rank: name.startsWith(words[0]) && inName ? 0 : inName ? 1 : 2 });
    }
    return scored.sort((a, b) => (a.p.own < MIN_RANKED) - (b.p.own < MIN_RANKED) || a.rank - b.rank || b.p.own - a.p.own).slice(0, MAX_RESULTS).map(x => x.p);
  }
  const api = { sortRows, defaultDir, canSwap, listTitle, searchProducts };
  if (typeof module !== 'undefined') module.exports = api; else root.TableSort = api;
})(this);
