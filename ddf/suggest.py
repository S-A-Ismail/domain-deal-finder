"""Rule-based name ideas, for when there is no LLM to brainstorm. Pure string work, no network."""

import re

DEFAULT_TLDS = ["com", "pk", "com.pk", "net", "co", "online", "store", "shop", "site", "xyz"]
# Variations are only tried on the TLDs people recognise most, to keep the number of lookups polite.
VARIANT_TLDS = ["com", "pk", "com.pk"]
PREFIXES = ["get", "my", "try", "go", "the"]
SUFFIXES = ["pk", "hq", "hub", "app", "online", "now", "wala", "bazaar", "point", "zone"]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def generate(keyword: str, tlds: list[str] | None = None, extra_words: list[str] | None = None, limit: int = 80) -> list[str]:
    tlds = [t.lstrip(".") for t in tlds] if tlds else DEFAULT_TLDS
    words = [w for w in re.split(r"[\s,_-]+", keyword.lower()) if w]
    base = _slug(keyword)
    if not base:
        return []
    stems = [base]
    if len(words) > 1:
        stems.append("-".join(_slug(w) for w in words))
    stems += [p + base for p in PREFIXES] + [base + s for s in SUFFIXES]
    stems += [base + _slug(w) for w in extra_words or []] + [_slug(w) + base for w in extra_words or []]

    variant_tlds = [t for t in VARIANT_TLDS if t in tlds] or tlds[:3]
    candidates = [f"{base}.{t}" for t in tlds]
    for stem in stems[1:]:
        candidates += [f"{stem}.{t}" for t in variant_tlds]
    unique = list(dict.fromkeys(c for c in candidates if len(c.split(".")[0]) <= 63))
    return unique[:limit]
