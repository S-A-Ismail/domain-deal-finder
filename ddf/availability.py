"""Is a domain free? RDAP for most TLDs, PKNIC's own lookup page for .pk (it has no RDAP)."""

import re
from concurrent.futures import ThreadPoolExecutor

import httpx

from .cache import Cache

BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
PKNIC_LOOKUP_URL = "https://pk6.pknic.net.pk/pk5/lookup.PK"
# Fallback for TLDs without RDAP (.co, .io, ...): DNS-over-HTTPS, answers in JSON.
DOH_URL = "https://cloudflare-dns.com/dns-query"

AVAILABLE, TAKEN, UNKNOWN, INVALID = "available", "taken", "unknown", "invalid"

_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


def normalize(domain: str) -> str | None:
    domain = domain.strip().lower().rstrip(".")
    domain = re.sub(r"^https?://", "", domain).split("/")[0]
    labels = domain.split(".")
    if len(labels) < 2 or len(domain) > 253 or not all(_LABEL.match(label) for label in labels):
        return None
    return domain


def rdap_base(bootstrap: dict, domain: str) -> str | None:
    tld = domain.rsplit(".", 1)[-1]
    for tlds, urls in bootstrap.get("services", []):
        if tld in tlds and urls:
            return next((u for u in urls if u.startswith("https://")), urls[0])
    return None


def parse_pknic(html: str) -> tuple[str, str]:
    if "Domain is Registered" in html:
        match = re.search(r"Expire Date:(?:\s|&nbsp;|<[^>]+>)*([A-Z][a-z]{2} \d{1,2}, \d{4})", html)
        return TAKEN, f"expires {match.group(1)}" if match else "registered"
    if "Domain not found" in html or "not registered" in html:
        return AVAILABLE, "not registered at PKNIC (reserved/blocked names are only rejected at registration)"
    return UNKNOWN, "unrecognised PKNIC response"


def parse_doh(answer: dict) -> tuple[str, str]:
    # DNS status 0 = the name exists, 3 = NXDOMAIN (no such name).
    if answer.get("Status") == 0:
        return TAKEN, "exists in DNS"
    if answer.get("Status") == 3:
        return AVAILABLE, "no DNS record (no RDAP for this TLD, so confirm at a registrar)"
    return UNKNOWN, f"DNS lookup returned status {answer.get('Status')}"


class AvailabilityChecker:
    def __init__(self, client: httpx.Client, cache: Cache, ttl_seconds: int = 3600):
        self.client = client
        self.cache = cache
        self.ttl = ttl_seconds
        self._bootstrap: dict | None = None

    def bootstrap(self) -> dict:
        if self._bootstrap is None:
            cached = self.cache.get("rdap:bootstrap", 7 * 24 * 3600)
            if cached is None:
                resp = self.client.get(BOOTSTRAP_URL, timeout=30)
                resp.raise_for_status()
                cached = resp.json()
                self.cache.put("rdap:bootstrap", cached)
            self._bootstrap = cached
        return self._bootstrap

    def check(self, raw: str) -> dict:
        domain = normalize(raw)
        if domain is None:
            return {"domain": raw, "status": INVALID, "detail": "not a valid domain name"}
        cached = self.cache.get(f"avail:{domain}", self.ttl)
        if cached:
            return cached
        try:
            status, via, detail = self._check_pknic(domain) if domain.endswith(".pk") else self._check_rdap(domain)
        except httpx.HTTPError as e:
            status, via, detail = UNKNOWN, "network", str(e)
        result = {"domain": domain, "status": status, "via": via, "detail": detail}
        if status in (AVAILABLE, TAKEN):
            self.cache.put(f"avail:{domain}", result)
        return result

    def check_many(self, domains: list[str]) -> list[dict]:
        with ThreadPoolExecutor(max_workers=8) as pool:
            return list(pool.map(self.check, domains))

    def _check_rdap(self, domain: str) -> tuple[str, str, str]:
        base = rdap_base(self.bootstrap(), domain)
        if base is None:
            return self._check_dns(domain)
        resp = self.client.get(f"{base.rstrip('/')}/domain/{domain}", timeout=20, follow_redirects=True)
        if resp.status_code == 200:
            return TAKEN, "rdap", "registered"
        if resp.status_code == 404:
            return AVAILABLE, "rdap", "not in registry; premium or reserved names only show at checkout"
        return UNKNOWN, "rdap", f"RDAP answered HTTP {resp.status_code}"

    def _check_dns(self, domain: str) -> tuple[str, str, str]:
        resp = self.client.get(
            DOH_URL, params={"name": domain, "type": "NS"}, headers={"accept": "application/dns-json"}, timeout=20
        )
        resp.raise_for_status()
        status, detail = parse_doh(resp.json())
        return status, "dns", detail

    def _check_pknic(self, domain: str) -> tuple[str, str, str]:
        resp = self.client.post(PKNIC_LOOKUP_URL, data={"name": domain}, timeout=30)
        resp.raise_for_status()
        status, detail = parse_pknic(resp.text)
        return status, "pknic", detail
