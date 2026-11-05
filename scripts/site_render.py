"""Render real HTML pages for the site: content is in the page, and site/app.js adds sorting and filters on top."""
import collections
import html, json, re

ORIGIN = "https://hn.shellbear.me"
TAGLINE = "The stuff Hacker News actually recommends."
MIN_INDEX_OWNERS = 3
MIN_INDEX_VERDICTS = 5
MIN_PERCENT_VERDICTS = 3
MAX_DESCRIPTION = 200
ITEM_LIST_SIZE = 10
LIST_ROWS = 100
FONTS = "https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,400..800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap"
STANCE = {"recommend": "Recommends it", "positive": "Likes it", "neutral": "Neutral", "negative": "Doesn’t like it"}
VIEWS = [("loved", "Most loved"), ("owned", "Most owned"), ("recent", "Recommended lately"), ("long", "Long-haul")]
NOTE = "Ranked by how lopsided the verdict is among owners, adjusted so a handful of fans can’t beat a large, happy crowd."
QUAL = ("bifl", "switch", "skipgen", "divisive", "rising", "fading", "dated")
e = lambda s: html.escape(str(s), quote=True)


def slug(key):
    return key.replace("_", "-")


def cat_path(key):
    return f"/c/{slug(key)}"


def tag_path(key):
    return f"/t/{slug(key)}"


_VAGUE_MODEL = {"older", "old", "new", "newer", "newest", "latest", "original", "base", "unknown", "unspecified", "model unspecified", "standard", "regular", "first", "second", "various", "current", "previous", "previous version", "latest generation", "generic"}


def normalize_model(model, line):
    """Key for grouping a model under its product line, or None if it doesn't identify one."""
    t = (model or "").lower().strip()
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"\b\d+(?:\.\d+)?(?:[- ]?(?:inch|in)\b|\")", " ", t)
    t = re.sub(r"\b\d+ ?(?:gb|tb)\b", " ", t)
    t = re.sub(r"\b(?:gen|generation|mk|mark)\.? ?\d+\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" ,-/")
    head = (line or "").lower().strip()
    if head and t.startswith(head + " "):
        t = t[len(head) + 1:]
    last = head.split()[-1] if head else ""
    if last and t.endswith(" " + last):
        t = t[: -len(last) - 1]
    if not t or t in _VAGUE_MODEL or t == head or len(t) > 24 or len(t.split()) > 4:
        return None
    return t


def merges_across_lines(model):
    """T480 means one product whichever line it was filed under; M1 or 13 mean different things under different lines."""
    return len(model) >= 4 and bool(re.search(r"\d", model)) and not re.fullmatch(r"(?:19|20)\d\d", model)


def model_name(parent, label):
    """Page name for a model: "Lenovo ThinkPad X1" + "X1 Carbon" reads as "Lenovo ThinkPad X1 Carbon"."""
    last = parent.split()[-1].lower()
    return f"{' '.join(parent.split()[:-1])} {label}".strip() if label.lower().startswith(last) else f"{parent} {label}"


_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def month_label(ym):
    year, month = ym.split("-")
    return f"{_MONTHS[int(month) - 1]} {year}"


_LIGHT_TYPE = re.compile(r"\b(lamps?|bulbs?|light bars?|monitor lights?|desk lights?|smart lights?|smart lighting|lighting|led strips?|monitor arms?|desk mats?)\b", re.I)
_NOT_DESK_LIGHT = re.compile(r"\b(bike|bicycle|flashlight|headlamp|car|vehicle|torch)\b", re.I)
_LIGHT_NAME = re.compile(r"\b(philips hue|hue|lifx|nanoleaf|tradfri|screenbar|ergotron|monitor arm)\b", re.I)
_NOT_PAPER = re.compile(r"\b(3d|fdm|sla|resin|barcode|fingerprint|network|port|body|code|lidar)\b", re.I)
_PAPER_TYPE = re.compile(r"\b(laser|inkjet|ink tank|photo|label|thermal|receipt|dot matrix|multifunction)\b.*\bprinters?\b|\bscanners?\b", re.I)
_BARE_PRINTER = re.compile(r"(?:all-in-one )?printers?", re.I)
_PAPER_BRAND = re.compile(r"\b(brother|epson|hp|canon|kyocera|xerox|lexmark|oki)\b", re.I)
_PAPER_NAME = re.compile(r"\b(laserjet|officejet|deskjet|ecotank|pixma|imageclass|scansnap|coolscan|brother (hl|dcp|mfc))\b", re.I)
_TYPE_HOMES = [(re.compile(p, re.I), c) for p, c in [
    (r"\b(mouse|trackball)$", "mice_trackpads"),
    (r"^(desktop pc|desktop computer|home computer)$", "desktops"),
    (r"\bwebcams?$", "webcams_mics"),
    (r"\b(earbuds|headphones)$", "headphones"),
]]
# Not hardware someone owns as a product here: operating systems, browsers, models, cars and ride services.
NOT_PRODUCTS = re.compile(r"^(android|google-android|microsoft-windows|microsoft-windows-pc|microsoft-windows-laptop|windows|firefox|mozilla-firefox|google-chrome|apple-safari|google-gemma|openwrt|btrfs|linux|bluetooth|usb-c|waymo|tesla-model-.*)$")
# Spellings of one product that a rule can't see: the mention moves to the key on the right.
ALIASES = {
    "raspberry-pi-raspberry-pi": "raspberry-pi", "thinkpad": "lenovo-thinkpad", "roomba": "irobot-roomba", "esp32": "espressif-esp32",
    "moonlander": "zsa-moonlander", "pinecil": "pine64-pinecil", "ratta-supernote": "supernote", "glove80": "moergo-glove80",
    "meta-oculus": "oculus", "amazon-eero": "eero", "odroid": "hardkernel-odroid", "nest-thermostat": "google-nest-thermostat",
    "playdate": "panic-playdate", "planck": "olkb-planck", "atreus": "keyboardio-atreus", "soundcore": "anker-soundcore",
    "paperlike": "dasung-paperlike", "inkplate": "soldered-inkplate", "framework": "framework-laptop", "bambu": "bambu-lab",
    "flipper-devices-flipper-zero": "flipper-zero", "meta-ray-ban-meta": "ray-ban-meta", "ikea-tr-dfri": "ikea-tradfri", "signify-hue": "philips-hue",
}
ALIAS_PREFIXES = (("onyx-boox", "boox"), ("western-digital-wd-", "western-digital-"), ("hp-hp-", "hp-"))
GENERIC_PRODUCTS = frozenset("""chromebook laptop heat-pump heat-pump-water-heater fountain-pen e-bike ebike monitor dishwasher vertical-mouse
    standing-desk pc moka-pot 4k-monitor oled-monitor 3d-printer air-purifier air-fryer cargo-bike road-bike trackpad android-phone android-tablet crt tv phone
    mechanical-keyboard vr-headset cast-iron oled""".split())
THIN_CATEGORY = 20
FEW_OWNERS = 2
MIXED_MIN_TYPED = 3
MIXED_TOP_SHARE = 0.6
FOCUSED_MIN_TYPED = 5
CATCH_ALL = "other_physical"


def refile(category, product_type, brand, line):
    """Correct a category from the product type: printers, clear misfiles, and lights and desk gear.
    Names cover the earlier sample, which has no type."""
    kind = product_type or ""
    name = f"{brand or ''} {line or ''}"
    if not _NOT_PAPER.search(kind) and (_PAPER_TYPE.search(kind) or _PAPER_NAME.search(name) or (_BARE_PRINTER.fullmatch(kind.strip()) and _PAPER_BRAND.search(name))):
        return "printers"
    for pattern, home in _TYPE_HOMES:
        if pattern.search(kind):
            return home
    if _NOT_DESK_LIGHT.search(kind):
        return category
    if _LIGHT_TYPE.search(kind) or (not kind and _LIGHT_NAME.search(f"{brand} {line}")):
        return "lighting_desk"
    return category


def _product_kind(product_type):
    """The last word names the kind of thing: "drawing tablet" and "graphics tablets" are both tablets."""
    words = (product_type or "").strip().lower().split()
    if not words:
        return ""
    word = words[-1]
    return word[:-1] if word.endswith("s") and not word.endswith("ss") else word


def _spread(values):
    """True when there's enough evidence and no single value clearly leads."""
    if len(values) < MIXED_MIN_TYPED:
        return False
    top = max(values.count(v) for v in set(values))
    return top / len(values) < MIXED_TOP_SHARE


def mixed_brand(categories, product_types=()):
    """A brand-level entry spread across categories can't be ranked as one thing. Category labels are noisy, so a brand
    whose comments all describe one kind of product still counts as focused. Lodge and Wacom stay; Samsung doesn't."""
    if not _spread([c for c in categories if c]):
        return False
    kinds = [k for k in map(_product_kind, product_types) if k]
    return len(kinds) < FOCUSED_MIN_TYPED or _spread(kinds)


def home_category(categories):
    """A brand gets one category: the most common, preferring a real one to the catch-all unless it's only a stray."""
    counts = collections.Counter(c for c in categories if c)
    catch_all = counts.pop(CATCH_ALL, 0)
    if not counts:
        return CATCH_ALL if catch_all else None
    top, n = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return top if n * 2 >= catch_all else CATCH_ALL


def _alias(key):
    key = ALIASES.get(key, key)
    for old, new in ALIAS_PREFIXES:
        if key.startswith(old):
            return new + key[len(old):]
    return key


def clean_mentions(mentions):
    """Drop what isn't owned hardware and merge spellings of one product: known aliases, then keys differing only by punctuation."""
    kept = [m for m in mentions if not NOT_PRODUCTS.match(m["key"])]
    counts = collections.Counter(_alias(m["key"]) for m in kept)
    winners = {}
    for key, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        winners.setdefault(key.replace("-", ""), key)
    final = lambda m: winners[_alias(m["key"]).replace("-", "")]
    # Moved mentions take the name of those already under the winning key.
    names = collections.defaultdict(collections.Counter)
    for m in kept:
        if m["key"] == final(m):
            names[m["key"]][(m["cb"], m["cl"], m["disp"])] += 1
    out = []
    for m in kept:
        key = final(m)
        m = dict(m, key=key)
        if names[key]:
            m["cb"], m["cl"], m["disp"] = names[key].most_common(1)[0][0]
        out.append(m)
    return out


def generic_product(key):
    """A kind of thing rather than a product someone could buy by name."""
    return key in GENERIC_PRODUCTS or key.startswith(("unknown-", "generic-"))


def line_for(brand, line, category):
    """Comments often say just "BenQ" for its monitor light, which would otherwise file it with the brand's monitors."""
    if not (line or "").strip() and (brand or "").strip().lower() == "benq" and category == "lighting_desk":
        return "ScreenBar"
    return line


def indexable(p):
    """Fewer, stronger pages: a brand with no product line, or a page with a handful of verdicts, says too little to rank."""
    return p["own"] >= MIN_INDEX_OWNERS and not p["bo"] and not p.get("nl") and p["pos"] + p["neg"] >= MIN_INDEX_VERDICTS


def happy_pct(p):
    n = p["pos"] + p["neg"]
    return f"{round(100 * p['pos'] / n)}%" if n >= MIN_PERCENT_VERDICTS else "–"


def _aspects(items):
    words = [x.replace("_", " ") for x in items[:2]]
    return " and ".join(words)


def _reasons(p):
    bits = []
    if p.get("pr"):
        bits.append(f"Praised for {_aspects(p['pr'])}")
    praised = (p.get("pr") or [])[:2]
    criticized = [x for x in p.get("co") or [] if x not in praised]
    if criticized:
        bits.append(f"{'criticized' if bits else 'Criticized'} for {_aspects(criticized)}")
    return "; ".join(bits) + "." if bits else ""


def _description(p):
    n = p["pos"] + p["neg"]
    if n >= MIN_PERCENT_VERDICTS:
        lead = f"{happy_pct(p)} of {n} verdicts on the {p['n']} from Hacker News owners are positive."
    else:
        lead = f"What Hacker News owners say about the {p['n']}."
    parts = [lead]
    for extra in (_reasons(p), f"{p['lh']} still happy after 3+ years." if p.get("lh") else "", "Every opinion links to its comment."):
        if extra and len(" ".join(parts + [extra])) <= MAX_DESCRIPTION:
            parts.append(extra)
    return " ".join(parts)[:MAX_DESCRIPTION]


def embed_json(obj):
    """JSON safe inside a script tag: it cannot close the tag, whatever a comment says."""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def read_meta(path):
    """Category and tag names live in app.js; read them so the two can't drift apart."""
    with open(path) as f:
        src = f.read()
    cats = dict(re.findall(r"(\w+):'((?:[^'\\]|\\.)*)'", re.search(r"const CATS=\{(.*?)\};", src, re.S).group(1)))
    tags = {k: [a, b] for k, a, b in re.findall(r"(\w+):\['((?:[^'\\]|\\.)*)','((?:[^'\\]|\\.)*)'\]", re.search(r"const TAGS=\{(.*?)\};\n", src, re.S).group(1))}
    return cats, tags


def robots():
    return f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n"


def sitemap(paths, products, date):
    urls = list(paths) + [f"/p/{p['k']}" for p in products if indexable(p)]
    body = "".join(f"<url><loc>{e(ORIGIN + u)}</loc><lastmod>{date}</lastmod></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>\n'


def llms_txt(cats, count):
    """A plain guide for AI tools, following the llms.txt convention."""
    links = "\n".join(f"- [{name}]({ORIGIN}{cat_path(key)})" for key, name in cats.items())
    return f"""# HackerBuys

> {TAGLINE} {count} physical products ranked by the Hacker News commenters who own them, with every opinion linked to its comment.

Opinions and ownership were extracted by AI, so they can be wrong: check the linked comment before relying on one. Counts cover the comments scanned so far, not all of Hacker News.

## Data

- [Sitemap of all product and category pages]({ORIGIN}/sitemap.xml)
- [Full catalogue as JSON]({ORIGIN}/data/index.json): for each product, k is the page at /p/k, n the name, c the category, own the distinct owners, pos, neu and neg the verdicts, and ly the last year mentioned.
- [Source code and methods](https://github.com/shellbear/hackerbuys)

## Categories

{{links}}
""".replace("{links}", links)


class Site:
    def __init__(self, cats, tags, coverage, products=()):
        self.cats, self.tags, self.coverage = cats, tags, coverage
        self.live = [p for p in products if p["own"] >= MIN_INDEX_OWNERS and not p["bo"] and not p.get("pk") and not p.get("mx")]

    def _nav(self, cat=None, tag=None):
        count = lambda key: sum(p["c"] == key for p in self.live)
        link = lambda href, label, n, cur: f'<a href="{e(href)}"{" aria-current=\"page\"" if cur else ""}>{e(label)}<span>{n}</span></a>'
        out = [link("/", "All categories", len(self.live), not cat and not tag)]
        for k, v in sorted(((k, v) for k, v in self.cats.items() if count(k)), key=lambda kv: -count(kv[0])):
            out.append(link(cat_path(k), v, count(k), k == cat))
        tagged = [(k, sum(k in p["tags"] for p in self.live)) for k in self.tags]
        for title, keep in (("Verdict tags", lambda k: k in QUAL), ("Smaller groups", lambda k: k not in QUAL)):
            rows = [(k, n) for k, n in tagged if n and keep(k)]
            if rows:
                out.append(f'<p class="navh">{title}</p>')
                out += [link(tag_path(k), self.tags[k][0], n, k == tag) for k, n in rows]
        return "".join(out)

    def _page(self, title, desc, path, main, cat=None, tag=None, noindex=False, extra=""):
        robots_tag = '<meta name="robots" content="noindex,follow">' if noindex else ""
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">{robots_tag}
<link rel="canonical" href="{e(ORIGIN + path)}">
<meta property="og:site_name" content="HackerBuys"><meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(ORIGIN + path)}"><meta property="og:image" content="{ORIGIN}/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="HackerBuys: the stuff Hacker News actually recommends"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{ORIGIN}/og.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS}" rel="stylesheet">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="alternate icon" href="/favicon.ico" sizes="48x48"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="stylesheet" href="/style.css">{extra}</head>
<body><header class="top"><a class="logo" href="/">HackerBuys</a><p class="tag">{e(TAGLINE)}</p></header>
<div class="shell"><nav id="cats" aria-label="Categories">{self._nav(cat, tag)}</nav><main id="main" tabindex="-1">{main}</main></div>
<footer><p id="foot">{e(self.coverage)}</p><p>Comments from <a href="https://news.ycombinator.com">Hacker News</a> via <a href="https://huggingface.co/datasets/open-index/hacker-news">open-index/hacker-news</a> (ODC-BY). Not affiliated with Y Combinator.</p><p>Made by <a href="https://shellbear.me">shellbear</a> · <a href="https://github.com/shellbear/hackerbuys">Source on GitHub</a></p></footer>
<script src="/sort.js"></script><script src="/app.js"></script></body></html>
"""

    def _rows(self, rows, show_cat):
        out = []
        for p in rows:
            small = f"<small>{e(self.cats.get(p['c'], p['c']))}</small>" if show_cat else ""
            chips = "".join(f'<a href="{e(tag_path(t))}">{e(self.tags[t][0])}</a>' for t in p["tags"] if t in self.tags)
            chips = f'<span class="chips">{chips}</span>' if chips else ""
            out.append(f'<tr><td class="nm"><a href="/p/{e(p["k"])}">{e(p["n"])}</a>{small}{chips}</td><td class="ty">{p["pos"]} positive, {p["neu"]} neutral, {p["neg"]} negative</td><td>{p["own"]}</td><td class="hide-s">{happy_pct(p)}</td><td class="hide-s">{month_label(p["ld"]) if p.get("ld") else p["ly"]}</td></tr>')
        return "".join(out)

    def list_page(self, rows, cat=None, tag=None, few=()):
        base = cat_path(cat) if cat else tag_path(tag) if tag else "/"
        name = self.cats.get(cat, cat) if cat else self.tags[tag][0] if tag else None
        top = ", ".join(p["n"] for p in rows[:3])
        if cat and cat == "other_physical":
            title, heading = "Other products recommended on Hacker News | HackerBuys", name
        elif cat:
            title, heading = f"Best {name.lower()} according to Hacker News | HackerBuys", name
        elif tag:
            title, heading = f"{name}: products according to Hacker News | HackerBuys", name
        else:
            title, heading = f"HackerBuys: {TAGLINE}", "Everything people here actually own"
        scope = name.lower() if name else "physical products"
        desc = f"{len(rows)} {scope} ranked by the Hacker News commenters who own them, with every comment linked. Top: {top}."
        lede = f'<p class="lede">{e(self.tags[tag][1])}</p>' if tag else ""
        sep = lambda k: base if k == "loved" else f"{base}?view={k}"
        tabs = "".join(f'<a href="{e(sep(k))}" aria-current="{"true" if k == "loved" else "false"}">{e(t)}</a>' for k, t in VIEWS)
        table = (f'<table><thead><tr><th>Product</th><th>Verdict</th><th>Owners</th><th class="hide-s">Happy</th><th class="hide-s">Last mention</th></tr></thead><tbody>{self._rows(rows if cat or tag else rows[:LIST_ROWS], not cat)}</tbody></table>'
                 if rows else '<p class="empty">No products have enough owners here yet.</p>')
        summary, extra = "", ""
        if cat and len(rows) >= 3:
            link = lambda p: f'<a href="/p/{e(p["k"])}">{e(p["n"])}</a>'
            join = lambda ps: ", ".join(link(p) for p in ps)
            loved = sorted(rows, key=lambda p: -p["w"])[:3]
            owned = sorted(rows, key=lambda p: -p["own"])[:3]
            summary = f'<p class="note" id="summary">Most loved by owners: {join(loved)}. Most owned: {join(owned)}.</p>'
            items = [{"@type": "ListItem", "position": i + 1, "url": f"{ORIGIN}/p/{p['k']}", "name": p["n"]} for i, p in enumerate(rows[:ITEM_LIST_SIZE])]
            extra = f'<script type="application/ld+json">{embed_json({"@context": "https://schema.org", "@type": "ItemList", "name": heading, "itemListElement": items})}</script>'
        main = f'<h1>{e(heading)}</h1>{lede}{summary}<div class="views">{tabs}</div><p class="note">{e(NOTE)}</p>{table}{self._few(few)}'
        return self._page(title, desc, base, main, cat=cat, tag=tag, extra=extra)

    def _few(self, few):
        if not few:
            return ""
        items = "".join(f'<li><a href="/p/{e(p["k"])}">{e(p["n"])}</a><span>{p["own"]}</span></li>' for p in few)
        return f'<h2 id="few">Few owners so far</h2><ul class="moves">{items}</ul>'

    def _comment(self, c):
        cl = {"negative": "n", "neutral": ""}.get(c["s"], "p")
        bits = [f"<strong>{e(STANCE.get(c['s'], c['s']))}</strong>"]
        if c.get("ten") is not None:
            bits.append(f'<span class="yrs">Owned {e(c["ten"])} {"year" if c["ten"] == 1 else "years"}</span>')
        if c.get("sg"):
            bits.append("<span>Still going</span>")
        if not c.get("fh"):
            bits.append("<span>Doesn’t say they own it</span>")
        thread = f' <a href="https://news.ycombinator.com/item?id={e(c["root"])}" rel="noopener">in “{e(c["th"])}”</a>' if c.get("th") and c.get("root") else ""
        return f'<article class="c {cl}"><header>{"".join(bits)}</header><blockquote>{e(c["t"])}</blockquote><footer><a href="https://news.ycombinator.com/item?id={e(c["id"])}" rel="noopener">{e(c["by"])}, {e(c["d"])}</a>{thread}</footer></article>'

    def product_page(self, p):
        cat = self.cats.get(p["c"], p["c"])
        owners = "1 Hacker News owner thinks" if p["own"] == 1 else f"{p['own']} Hacker News owners think"
        title = f"{p['n']}: what {owners} | HackerBuys"
        desc = _description(p)
        whys = "".join(f'<li><a href="{e(tag_path(t))}">{e(self.tags[t][0])}</a><span>{e(p["why"].get(t, ""))}</span></li>' for t in p["tags"] if t in self.tags)
        whys = f'<ul class="whys">{whys}</ul>' if whys else ""
        stats = [(p["own"], "owners with an opinion"), (happy_pct(p), "of verdicts positive"), (f"{p['rpos']}/{p['rneg']}", "positive/negative since 2024")]
        if p["maxt"]:
            stats.append((f"{p['maxt']} yrs", "longest happy owner"))
        stats.append((p["lh"], "happy after 3+ years"))
        stats = "".join(f"<div><b>{e(a)}</b>{e(b)}</div>" for a, b in stats)
        moves = lambda rows: "".join(f'<li><a href="/p/{e(r[1])}">{e(r[0])}</a><span>{e(r[2])}</span></li>' for r in rows)
        to = f'<div><p class="note">Left this for</p><ul class="moves">{moves(p["to"])}</ul></div>' if p["to"] else ""
        fr = f'<div><p class="note">Came here from</p><ul class="moves">{moves(p["fr"])}</ul></div>' if p["fr"] else ""
        moved = f'<h2>Where people moved</h2><div class="two">{to}{fr}</div>' if to or fr else ""
        reasons = f'<p class="note">{e(_reasons(p))}</p>' if _reasons(p) else ""
        parent = f' · <a href="/p/{e(p["pk"])}">{e(p.get("pn") or "All models")}</a>' if p.get("pk") else ""
        models = "".join(f'<li><a href="/p/{e(k)}">{e(n)}</a><span>{e(c)}</span></li>' for n, k, c in p.get("models") or [])
        models = f'<h2>Models</h2><ul class="moves">{models}</ul>' if models else ""
        main = (f'<p class="crumb"><a href="{e(cat_path(p["c"]))}">{e(cat)}</a>{parent}</p><h1>{e(p["n"])}</h1>{whys}<div class="verdict">{stats}</div>{reasons}{models}{moved}'
                f'<h2>What people wrote</h2><div id="comments">{"".join(self._comment(c) for c in p["cs"])}</div>')
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": cat, "item": ORIGIN + cat_path(p["c"])},
            {"@type": "ListItem", "position": 2, "name": p["n"], "item": f"{ORIGIN}/p/{p['k']}"}]}
        extra = f'<script type="application/ld+json">{embed_json(crumbs)}</script><script type="application/json" id="product">{embed_json(p)}</script>'
        return self._page(title, desc, f"/p/{p['k']}", main, cat=p["c"], noindex=not indexable(p), extra=extra)

    def not_found(self):
        main = '<h1>Page not found</h1><p class="lede">That page isn’t in the catalogue. Products need at least two owners to get a page.</p><p><a href="/">Go to all categories</a></p>'
        return self._page("Page not found | HackerBuys", "This page isn’t in the HackerBuys catalogue.", "/404", main, noindex=True)
