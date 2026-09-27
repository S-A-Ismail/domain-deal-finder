from dataclasses import asdict

import httpx

from ..cache import Cache
from ..config import Settings
from ..models import Offer
from . import manual, porkbun

# Registrars with a live price feed. Add new adapters here: each exposes NAME and fetch_offers(client).
LIVE_SOURCES = [porkbun]

# The official list of TLDs in the DNS root. Anything else (e.g. Handshake names some registrars sell)
# won't resolve in a normal browser, so it's useless for a real website.
IANA_TLDS_URL = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"


def root_tlds(client: httpx.Client, cache: Cache) -> set[str]:
    cached = cache.get("iana:tlds", 7 * 24 * 3600)
    if cached is None:
        resp = client.get(IANA_TLDS_URL, timeout=30)
        resp.raise_for_status()
        cached = [line.strip().lower() for line in resp.text.splitlines() if line.strip() and not line.startswith("#")]
        cache.put("iana:tlds", cached)
    return set(cached)


def load_offers(client: httpx.Client, cache: Cache, settings: Settings) -> tuple[list[Offer], list[str]]:
    """All known offers, plus warnings for sources that failed (so one broken registrar doesn't stop a search)."""
    offers, warnings = [], []
    for source in LIVE_SOURCES:
        key = f"offers:{source.NAME}"
        cached = cache.get(key, settings.price_ttl_seconds)
        if cached is None:
            try:
                fetched = source.fetch_offers(client)
            except (httpx.HTTPError, RuntimeError, ValueError) as e:
                warnings.append(f"{source.NAME} prices unavailable: {e}")
                continue
            cached = [asdict(o) for o in fetched]
            cache.put(key, cached)
        offers.extend(Offer(**{**o, "payment_methods": tuple(o["payment_methods"])}) for o in cached)
    offers.extend(manual.load_offers(settings.manual_prices_path))
    try:
        real = root_tlds(client, cache)
        offers = [o for o in offers if o.tld.rsplit(".", 1)[-1] in real]
    except httpx.HTTPError as e:
        warnings.append(f"Could not load the IANA TLD list, so non-standard TLDs may appear: {e}")
    if not settings.has_intl_card:
        offers = [o for o in offers if o.currency == "PKR"]
    return offers, warnings


def group_by_tld(offers: list[Offer]) -> dict[str, list[Offer]]:
    grouped: dict[str, list[Offer]] = {}
    for offer in offers:
        grouped.setdefault(offer.tld, []).append(offer)
    return grouped
