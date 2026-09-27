"""The one object the CLI and the agent both talk to."""

import httpx

from . import registrars
from .availability import AvailabilityChecker, normalize
from .cache import Cache
from .config import Settings
from .fx import usd_to_pkr
from .models import Offer
from .optimizer import Money, best_plans, cheapest_tlds


class DomainService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.client = httpx.Client(headers={"User-Agent": "domain-deal-finder/0.1"})
        self.cache = Cache(self.settings.db_path)
        self.availability = AvailabilityChecker(self.client, self.cache, self.settings.availability_ttl_seconds)
        self._offers: dict[str, list[Offer]] | None = None
        self._money: Money | None = None
        self.warnings: list[str] = []

    def money(self) -> Money:
        if self._money is None:
            rate = self.settings.usd_pkr_override or usd_to_pkr(self.client, self.cache)
            self._money = Money(usd_pkr=rate, card_markup=self.settings.card_markup)
        return self._money

    def offers_by_tld(self) -> dict[str, list[Offer]]:
        if self._offers is None:
            offers, self.warnings = registrars.load_offers(self.client, self.cache, self.settings)
            self._offers = registrars.group_by_tld(offers)
        return self._offers

    def tld_of(self, domain: str) -> str | None:
        """Longest known suffix, so shop.com.pk prices as com.pk rather than pk."""
        labels = domain.split(".")
        offers = self.offers_by_tld()
        for i in range(1, len(labels)):
            suffix = ".".join(labels[i:])
            if suffix in offers:
                return suffix
        return None

    def check(self, domains: list[str]) -> list[dict]:
        return self.availability.check_many(domains)

    def plans(self, raw_domain: str, top: int = 3) -> dict:
        domain = normalize(raw_domain)
        if domain is None:
            return {"domain": raw_domain, "error": "not a valid domain name"}
        tld = self.tld_of(domain)
        if tld is None:
            return {"domain": domain, "error": "no registrar in the price list sells this TLD"}
        offers = self.offers_by_tld()[tld]
        plans = best_plans(offers, self.money(), top=top)
        return {
            "domain": domain,
            "tld": tld,
            "registrars_compared": sorted({o.registrar for o in offers}),
            "notes": sorted({f"{o.registrar}: {o.notes}" for o in offers if o.notes}),
            "plans_by_years": {n: [p.to_dict() for p in ps] for n, ps in plans.items()},
            **self.pricing_basis(),
        }

    def cheapest_tlds(self, years: int, limit: int = 25) -> dict:
        ranked = cheapest_tlds(self.offers_by_tld(), years, self.money(), limit)
        return {
            "years": years,
            "ranking": [{"tld": tld, **plan.to_dict()} for tld, plan in ranked],
            **self.pricing_basis(),
        }

    def pricing_basis(self) -> dict:
        m = self.money()
        return {
            "usd_pkr_rate": round(m.usd_pkr, 2),
            "card_markup_pct": round(m.card_markup * 100, 1),
            "warnings": self.warnings,
        }
