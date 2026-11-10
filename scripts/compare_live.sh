#!/bin/bash
# Compares every sitemap URL, and the files around them, on the live site with the local site/ build.
cd "$(dirname "$0")/.."
paths=$( { echo /robots.txt; echo /llms.txt; echo /sitemap.xml; echo /data/index.json; echo /no-such-page; echo /app.js; echo /style.css; echo /sort.js;
  grep -o '<loc>[^<]*</loc>' site/sitemap.xml | sed -E 's#<loc>https://hn.shellbear.me##; s#</loc>##'; } )
check() {
  p="$1"; f="site${p}"; [ "$p" = "/" ] && f=site/index.html; [ -f "$f" ] || f="${f}.html"; [ "$p" = /no-such-page ] && f=site/404.html
  live=$(curl -s --compressed -A "hackerbuys-compare" "https://hn.shellbear.me${p}" | shasum | cut -c1-12)
  loc=$(shasum < "$f" | cut -c1-12)
  [ "$live" = "$loc" ] && echo same || echo "DIFF $p"
}
export -f check
echo "$paths" | xargs -P 8 -I{} bash -c 'check "$@"' _ {} | sort | uniq -c | sort -rn | head -12
