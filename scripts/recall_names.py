"""Product names for a second pass over comments the keyword filter rejected. Names come from the extraction results."""
import re

MIN_MULTI, MIN_SINGLE = 3, 5
_EXCLUDED = {
    # Out of scope for the catalogue
    "toyota", "honda", "subaru", "nissan", "hyundai", "volkswagen", "ford", "bmw", "audi", "tesla", "waymo", "chevrolet", "kia", "mazda", "volvo", "rivian",
    # Software and services
    "firefox", "mozilla", "safari", "chrome", "linux", "windows", "android", "ubuntu", "debian", "fedora", "vim", "emacs", "github", "netflix", "spotify", "docker", "macos", "osx", "icloud", "itunes", "photoshop", "gmail", "dropbox", "slack", "droid", "f-droid", "starlink", "verizon", "comcast",
    # Shops and companies too broad to signal a product
    "walmart", "costco", "amazon", "google", "microsoft", "apple", "facebook", "meta", "bluetooth", "qualcomm", "nvidia", "intel", "amd",
}
_GENERIC_END = re.compile(r"\b(laptops?|phones?|desktops?|keyboards?|mouse|mice|monitors?|tablets?|tv|headphones|routers?|cameras?|printers?|desks?|chairs?|model|series|machine|frame)$")
_ALLOWED = re.compile(r"[a-z0-9 .+\-']+")
# Forms seen in comments the filter missed. Word boundaries stop matches like "smbp".
NICKNAMES = r"\b(?:mbp(?:ro)?|mba|rpi|raspi|mac ?book(?: pro| air)?|[tpxw]\d{3}[spe]?|x1 carbon|xps ?\d{2})\b"


def _has_excluded(name):
    return any(w in _EXCLUDED for w in name.lower().split())


def clean_names(multi, single, english):
    """Return (lowercase multi-word names, case-sensitive single names), most-mentioned first."""
    multis = [t for t, n in multi.most_common() if n >= MIN_MULTI and _ALLOWED.fullmatch(t) and not _GENERIC_END.search(t) and not _has_excluded(t)]
    singles = [t for t, n in single.most_common() if n >= MIN_SINGLE and t[0].isupper() and re.fullmatch(r"[A-Za-z0-9+\-]+", t) and t.lower() not in english and t.lower() not in _EXCLUDED]
    return multis, singles


def collect(docs):
    """Count first-hand product names with a verdict from extraction results."""
    multi, single = {}, {}
    for d in docs:
        for r in d["results"]:
            for p in r["products"]:
                if not p.get("first_hand") or p.get("stance") == "neutral":
                    continue
                brand, line = (p.get("brand") or "").strip(), (p.get("line") or "").strip()
                full = line if line.lower().startswith(brand.lower()) else f"{brand} {line}".strip()
                for name in {full.lower(), line.lower()}:
                    if len(name.split()) >= 2:
                        multi[name] = multi.get(name, 0) + 1
                for name in {line, brand}:
                    if len(name.split()) == 1 and len(name) >= 4:
                        single[name] = single.get(name, 0) + 1
    return multi, single
