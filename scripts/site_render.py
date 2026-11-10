"""Render real HTML pages for the site: content is in the page, and site/app.js adds sorting and filters on top."""
import collections, itertools
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


def _squash(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def model_name(parent, label):
    """Page name for a model, without repeating the line: "Logitech MX Master" + "MX Master 3" reads as "Logitech MX Master 3"."""
    words, parts = parent.split(), label.split()
    if _squash(label) in {_squash(w) for w in words}:
        return parent
    tails = [(i, _squash(" ".join(words[i:]))) for i in range(len(words))]
    # The model starts with the end of the name, whole words first: "MX Master 3", then "Galaxy S4".
    for i, tail in tails:
        for j in range(len(parts), 0, -1):
            if _squash(" ".join(parts[:j])) == tail:
                return " ".join(words + parts[j:])
        rest = _squash(label)[len(tail):]
        if _squash(label).startswith(tail) and (len(tail) >= 2 or rest[:1].isdigit()):
            return " ".join(words[:i] + parts)
    # The model ends with the end of the name: "M1 MacBook Air".
    for _, tail in tails:
        for j in range(1, len(parts)):
            if _squash(" ".join(parts[j:])) == tail:
                return " ".join(words + parts[:j])
    if len(parts) > 1 and parts[0].lower() == words[0].lower() and parts[1][0].isdigit():
        return " ".join(words + parts[1:])
    return f"{parent} {label}"


_FRAMEWORK_DESKTOP = re.compile(r"desktop|mini ?pc|mini.?itx", re.I)
_BAMBU_X1 = re.compile(r"^x1(?:c+\b|\b)", re.I)
_COMPUTER = re.compile(r"desktop|\bpc\b", re.I)
_MEMORY = re.compile(r"memory|\bram\b", re.I)


def refine_product(p):
    """Fix products the model files under the wrong line, where line, model and type have to be read together."""
    brand = (p.get("brand") or "").strip().lower()
    line, model, kind = p.get("line") or "", p.get("model") or "", p.get("product_type") or ""
    if brand.startswith("framework") and _FRAMEWORK_DESKTOP.search(f"{line} {model} {kind}"):
        return dict(p, line="Desktop", model=None if _FRAMEWORK_DESKTOP.search(model) else p.get("model"), category="desktops")
    if brand.startswith("bambu") and (_BAMBU_X1.search(line) or _BAMBU_X1.search(model)):
        return dict(p, line="X1 Carbon", model=None)
    if brand == "corsair" and line.lower() == "vengeance":
        if re.fullmatch(r"k\d+", model, re.I):
            return dict(p, line=model.upper(), model=None, category="keyboards")
        if _COMPUTER.search(kind):
            return dict(p, line=f"Vengeance {model}".strip(), model=None, category="desktops")
        if _MEMORY.search(kind):
            return dict(p, category="pc_components")
    return p


_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def month_label(ym):
    year, month = ym.split("-")
    return f"{_MONTHS[int(month) - 1]} {year}"


def day_label(ymd):
    year, month, day = ymd[:10].split("-")
    return f"{int(day)} {_MONTHS[int(month) - 1]} {year}"


def tenure_label(years):
    """How long someone owned it, in the unit people use: 3 weeks, 5 months, 2.5 years."""
    if years >= 1:
        return f"{years:g} {'year' if years == 1 else 'years'}"
    months = round(years * 12)
    if months >= 2:
        return f"{months} months"
    weeks = max(1, round(years * 52))
    return f"{weeks} {'week' if weeks == 1 else 'weeks'}"


def _time(ymd):
    return f'<time datetime="{e(ymd[:10])}">{day_label(ymd)}</time>'


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


MAX_VS_PAGES = 400
MIN_VS_EVIDENCE = 4
CROWDED_COMMENT = 6
SCORE = {"recommend": 1, "positive": 1, "neutral": 0, "negative": -1}


def vs_key(a, b):
    a, b = sorted((a, b))
    return f"{a}-vs-{b}"


def _family(a, b):
    """A line and its own models or sub-lines: MacBook and MacBook Pro are one family, not a choice between two products."""
    return a.startswith(b + "-") or b.startswith(a + "-")


def pick_pairs(mentions, parent, moved, category, limit=MAX_VS_PAGES, least=MIN_VS_EVIDENCE):
    """Pairs of pages that owners actually weigh against each other: comments naming both, and owners who switched between them.
    mentions maps a page key to its mentions, parent a model page to its line, category a page to its category. Both must be
    the same kind of thing, and named separately: one mention filed under a line and its model compares nothing. A comment
    that names many products is a list, not a comparison. Returns (a, b, comment ids, users a→b, users b→a)."""
    top = lambda k: parent.get(k) or k
    said = collections.defaultdict(lambda: collections.defaultdict(set))
    for k, xs in mentions.items():
        for x in xs:
            said[x["id"]][k].add(id(x))
    rival = lambda a, b: a != b and category.get(a) == category.get(b) and top(a) != b and top(b) != a and not _family(a, b)
    both = collections.defaultdict(set)
    for cid, by_page in said.items():
        if len(by_page) < 2 or len({top(k) for k in by_page}) > CROWDED_COMMENT:
            continue
        for a, b in itertools.combinations(sorted(by_page), 2):
            if rival(a, b) and by_page[a] != by_page[b]:
                both[(a, b)].add(cid)
    pairs = set(both)
    for f, tos in moved.items():
        for t in tos:
            if f in mentions and t in mentions and rival(f, t):
                pairs.add(tuple(sorted((f, t))))
    out = []
    for a, b in pairs:
        ab, ba = moved.get(a, {}).get(b, set()), moved.get(b, {}).get(a, set())
        if len(both[(a, b)]) + len(ab) + len(ba) >= least:
            out.append((a, b, both[(a, b)], ab, ba))
    out.sort(key=lambda r: (-(len(r[2]) + len(r[3]) + len(r[4])), r[0], r[1]))
    return out[:limit]


def lean(v):
    """Which side the evidence favors. Comments naming both, the direction people switched and overall owner verdicts each
    count once, so one loud signal can't decide it alone. Returns 0 for a, 1 for b or None, and the sentence to show."""
    a, b = v["a"]["n"], v["b"]["n"]
    votes = [0, 0]
    if v["fa"] >= 3 and v["fa"] >= 2 * v["fb"]:
        votes[0] += 1
    elif v["fb"] >= 3 and v["fb"] >= 2 * v["fa"]:
        votes[1] += 1
    if v["ba"] >= 3 and v["ba"] >= 2 * v["ab"]:
        votes[0] += 1
    elif v["ab"] >= 3 and v["ab"] >= 2 * v["ba"]:
        votes[1] += 1
    if v["a"]["w"] - v["b"]["w"] >= 0.05:
        votes[0] += 1
    elif v["b"]["w"] - v["a"]["w"] >= 0.05:
        votes[1] += 1
    if votes[0] and votes[1]:
        return None, "Owners are split: the signals below point different ways."
    for i, name in ((0, a), (1, b)):
        if votes[i] >= 2:
            return i, f"Hacker News owners lean toward the {name}."
        if votes[i] == 1:
            return i, f"Hacker News owners slightly favor the {name}."
    return None, "No clear winner: owners rate them about the same."


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


def sitemap(paths, products, date, changed=None):
    """lastmod is the day a page last said something different, from changed, so crawlers can trust it; date is the fallback."""
    urls = list(paths) + [f"/p/{p['k']}" for p in products if indexable(p)]
    body = "".join(f"<url><loc>{e(ORIGIN + u)}</loc><lastmod>{(changed or {}).get(u, date)}</lastmod></url>" for u in urls)
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
- Comparison pages at /vs/<a>-vs-<b>, for pairs owners weigh against each other: linked from each product page under "Compared with".
- [Source code and methods](https://github.com/shellbear/hackerbuys)

## Categories

{{links}}
""".replace("{links}", links)


class Site:
    def __init__(self, cats, tags, coverage, products=(), stamp=None, through=None):
        """stamp(path, content, seed) returns the day a page's content last changed; through is the newest comment scanned."""
        self.cats, self.tags, self.coverage = cats, tags, coverage
        self.stamp, self.through = stamp, through
        self.live = [p for p in products if p["own"] >= MIN_INDEX_OWNERS and not p["bo"] and not p.get("pk") and not p.get("mx")]
        # Counted once: every page draws the same nav, and recounting per page was nearly all of the render time.
        self.cat_counts = collections.Counter(p["c"] for p in self.live)
        self.tag_counts = collections.Counter(t for p in self.live for t in p["tags"])

    def _nav(self, cat=None, tag=None):
        count = lambda key: self.cat_counts[key]
        link = lambda href, label, n, cur: f'<a href="{e(href)}"{" aria-current=\"page\"" if cur else ""}>{e(label)} <span>{n}</span></a>'
        out = [link("/", "All categories", len(self.live), not cat and not tag)]
        for k, v in sorted(((k, v) for k, v in self.cats.items() if count(k)), key=lambda kv: -count(kv[0])):
            out.append(link(cat_path(k), v, count(k), k == cat))
        tagged = [(k, self.tag_counts[k]) for k in self.tags]
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
<div class="shell"><main id="main" tabindex="-1">{main}</main><nav id="cats" aria-label="Categories">{self._nav(cat, tag)}</nav></div>
<footer><p id="foot">{e(self.coverage)}</p><p>Comments from <a href="https://news.ycombinator.com">Hacker News</a> via <a href="https://huggingface.co/datasets/open-index/hacker-news">open-index/hacker-news</a> (ODC-BY). Not affiliated with Y Combinator.</p><p>Made by <a href="https://shellbear.me">shellbear</a> · <a href="https://github.com/shellbear/hackerbuys">Source on GitHub</a></p></footer>
<script src="/sort.js"></script><script src="/app.js"></script></body></html>
"""

    def _dates(self, path, core, seed, lead, kind):
        """The visible dates line and its structured data. The page is stamped without this line, so its updated date
        only moves when what the page says changes, not when the newest scanned comment does."""
        updated = self.stamp(path, core, seed) if self.stamp else None
        parts = [lead] if lead else []
        if updated:
            parts.append(f"{'updated' if parts else 'Updated'} {_time(updated)}")
        if not parts:
            return "", "", None
        line = f'<p class="note" id="dates">{" · ".join(parts)}</p>'
        page = {"@context": "https://schema.org", "@type": kind, "url": ORIGIN + path}
        if updated:
            page["dateModified"] = updated
        return line, f'<script type="application/ld+json">{embed_json(page)}</script>' if updated else "", updated

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
        lead = f"Comments through {_time(self.through)}" if self.through else ""
        dates, page, _ = self._dates(base, main, self.through, lead, "CollectionPage")
        return self._page(title, desc, base, main + dates, cat=cat, tag=tag, extra=extra + page)

    def _few(self, few):
        if not few:
            return ""
        items = "".join(f'<li><a href="/p/{e(p["k"])}">{e(p["n"])}</a> <span>{p["own"]}</span></li>' for p in few)
        return f'<h2 id="few">Few owners so far</h2><ul class="moves">{items}</ul>'

    def _comment(self, c):
        cl = {"negative": "n", "neutral": ""}.get(c["s"], "p")
        bits = [f"<strong>{e(STANCE.get(c['s'], c['s']))}</strong>"]
        if c.get("ten"):
            bits.append(f'<span class="yrs">Owned {tenure_label(c["ten"])}</span>')
        if c.get("sg"):
            bits.append("<span>Still going</span>")
        if not c.get("fh"):
            bits.append("<span>Doesn’t say they own it</span>")
        return self._article(c, cl, bits)

    def _article(self, c, cl, bits):
        thread = f' <a href="https://news.ycombinator.com/item?id={e(c["root"])}" rel="noopener">in “{e(c["th"])}”</a>' if c.get("th") and c.get("root") else ""
        return f'<article class="c {cl}"><header>{"".join(bits)}</header><blockquote>{e(c["t"])}</blockquote><footer><a href="https://news.ycombinator.com/item?id={e(c["id"])}" rel="noopener">{e(c["by"])}, {e(c["d"])}</a>{thread}</footer></article>'

    def _vs_comment(self, c, a, b):
        """A comment on a comparison page: the switch it describes, and its verdict on each product it names."""
        bits = []
        if "sw" in c:
            moved = (a, b) if c["sw"] == 0 else (b, a)
            bits.append(f"<strong>Switched from the {e(moved[0])} to the {e(moved[1])}</strong>")
        for key, name in (("sa", a), ("sb", b)):
            if key in c:
                bits.append(f"<span>{e(name)}: {e(STANCE.get(c[key], c[key]))}</span>")
        return self._article(c, "", bits)

    def vs_page(self, v):
        """Two products side by side, with the comments where owners weigh one against the other."""
        a, b = v["a"], v["b"]
        winner, verdict = lean(v)
        path = f"/vs/{v['k']}"
        title = f"{a['n']} vs {b['n']}: what Hacker News owners say | HackerBuys"
        facts = []
        if v["both"]:
            rest = v["both"] - v["fa"] - v["fb"]
            facts.append(f"{v['both']} {'comment names' if v['both'] == 1 else 'comments name'} both: {v['fa']} favor the {a['n']}, {v['fb']} the {b['n']}"
                         + (f", and {rest} rate them alike." if rest else "."))
        if v["ab"] or v["ba"]:
            facts.append(f"{v['ab']} {'owner' if v['ab'] == 1 else 'owners'} moved from the {a['n']} to the {b['n']}, {v['ba']} the other way.")
        verdicts = lambda p: f"{happy_pct(p)} of {p['pos'] + p['neg']}"
        facts.append(f"Overall, {verdicts(a)} verdicts on the {a['n']} are positive, against {verdicts(b)} on the {b['n']}.")
        desc = f"{a['n']} or {b['n']}? {verdict}"
        for extra in (facts[0], "Every opinion links to its Hacker News comment."):
            if len(f"{desc} {extra}") <= MAX_DESCRIPTION:
                desc = f"{desc} {extra}"
        aspects = lambda xs: e(_aspects(xs)) if xs else "–"
        rows = [("Owners with an opinion", lambda p: e(p["own"])), ("Positive verdicts", lambda p: e(verdicts(p))),
                ("Positive/negative since 2024", lambda p: e(f"{p['rpos']}/{p['rneg']}")), ("Happy after 3+ years", lambda p: e(p["lh"])),
                ("Longest happy owner", lambda p: e(f"{p['maxt']} yrs") if p.get("maxt") else "–"),
                ("Praised for", lambda p: aspects(p.get("pr"))), ("Criticized for", lambda p: aspects(p.get("co"))),
                ("Newest comment", lambda p: _time(p["lt"]) if p.get("lt") else "–")]
        name = lambda i, p: f'<th{" class=\"won\"" if winner == i else ""}><a href="/p/{e(p["k"])}">{e(p["n"])}</a></th>'
        table = (f'<table class="vs"><thead><tr><th></th>{name(0, a)}{name(1, b)}</tr></thead><tbody>'
                 + "".join(f"<tr><td>{label}</td><td>{f(a)}</td><td>{f(b)}</td></tr>" for label, f in rows) + "</tbody></table>")
        cats = [a["c"]] if a["c"] == b["c"] else [a["c"], b["c"]]
        crumb = " · ".join(f'<a href="{e(cat_path(c))}">{e(self.cats.get(c, c))}</a>' for c in cats)
        top = (f'<p class="crumb">{crumb}</p><h1>{e(a["n"])} vs {e(b["n"])}</h1><p class="lede">{e(verdict)}</p>'
               f'<ul class="facts">{"".join(f"<li>{e(x)}</li>" for x in facts)}</ul>{table}')
        rest = f'<h2>What owners wrote about both</h2><div id="comments">{"".join(self._vs_comment(c, a["n"], b["n"]) for c in v["cs"])}</div>' if v["cs"] else ""
        newest = max((c["d"] for c in v["cs"]), default=None)
        # Just the updated day: the table already gives each product's newest comment.
        dates, page, _ = self._dates(path, top + rest, newest, "", "WebPage")
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": self.cats.get(cats[0], cats[0]), "item": ORIGIN + cat_path(cats[0])},
            {"@type": "ListItem", "position": 2, "name": f"{a['n']} vs {b['n']}", "item": ORIGIN + path}]}
        extra = f'<script type="application/ld+json">{embed_json(crumbs)}</script>{page}'
        return self._page(title, desc, path, top + dates + rest, cat=cats[0] if len(cats) == 1 else None, extra=extra)

    def product_page(self, p):
        cat = self.cats.get(p["c"], p["c"])
        owners = "1 Hacker News owner thinks" if p["own"] == 1 else f"{p['own']} Hacker News owners think"
        title = f"{p['n']}: what {owners} | HackerBuys"
        desc = _description(p)
        whys = "".join(f'<li><a href="{e(tag_path(t))}">{e(self.tags[t][0])}</a> <span>{e(p["why"].get(t, ""))}</span></li>' for t in p["tags"] if t in self.tags)
        whys = f'<ul class="whys">{whys}</ul>' if whys else ""
        stats = [(p["own"], "owners with an opinion"), (happy_pct(p), "of verdicts positive"), (f"{p['rpos']}/{p['rneg']}", "positive/negative since 2024")]
        if p["maxt"]:
            stats.append((f"{p['maxt']} yrs", "longest happy owner"))
        stats.append((p["lh"], "happy after 3+ years"))
        stats = "".join(f"<div><b>{e(a)}</b> {e(b)}</div>" for a, b in stats)
        moves = lambda rows: "".join(f'<li><a href="/p/{e(r[1])}">{e(r[0])}</a> <span>{e(r[2])}</span></li>' for r in rows)
        to = f'<div><p class="note">Left this for</p><ul class="moves">{moves(p["to"])}</ul></div>' if p["to"] else ""
        fr = f'<div><p class="note">Came here from</p><ul class="moves">{moves(p["fr"])}</ul></div>' if p["fr"] else ""
        moved = f'<h2>Where people moved</h2><div class="two">{to}{fr}</div>' if to or fr else ""
        versus = "".join(f'<li><a href="/vs/{e(k)}">vs {e(n)}</a></li>' for n, k, _ in p.get("vs") or [])
        versus = f'<h2>Compared with</h2><ul class="moves">{versus}</ul>' if versus else ""
        reasons = f'<p class="note">{e(_reasons(p))}</p>' if _reasons(p) else ""
        parent = f' · <a href="/p/{e(p["pk"])}">{e(p.get("pn") or "All models")}</a>' if p.get("pk") else ""
        models = "".join(f'<li><a href="/p/{e(k)}">{e(n)}</a> <span>{e(c)}</span></li>' for n, k, c in p.get("models") or [])
        models = f'<h2>Models</h2><ul class="moves">{models}</ul>' if models else ""
        top = f'<p class="crumb"><a href="{e(cat_path(p["c"]))}">{e(cat)}</a>{parent}</p><h1>{e(p["n"])}</h1>{whys}<div class="verdict">{stats}</div>{reasons}'
        rest = f'{models}{moved}{versus}<h2>What people wrote</h2><div id="comments">{"".join(self._comment(c) for c in p["cs"])}</div>'
        path = f"/p/{p['k']}"
        dates, page, updated = self._dates(path, top + rest, p.get("lt"), f"Newest comment {_time(p['lt'])}" if p.get("lt") else "", "WebPage")
        crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": cat, "item": ORIGIN + cat_path(p["c"])},
            {"@type": "ListItem", "position": 2, "name": p["n"], "item": f"{ORIGIN}/p/{p['k']}"}]}
        data = dict(p, upd=updated) if updated else p
        extra = f'<script type="application/ld+json">{embed_json(crumbs)}</script>{page}<script type="application/json" id="product">{embed_json(data)}</script>'
        return self._page(title, desc, path, top + dates + rest, cat=p["c"], noindex=not indexable(p), extra=extra)

    def not_found(self):
        main = '<h1>Page not found</h1><p class="lede">That page isn’t in the catalogue. Products need at least two owners to get a page.</p><p><a href="/">Go to all categories</a></p>'
        return self._page("Page not found | HackerBuys", "This page isn’t in the HackerBuys catalogue.", "/404", main, noindex=True)
