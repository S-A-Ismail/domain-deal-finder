from dataclasses import dataclass, field


@dataclass(frozen=True)
class Offer:
    """One registrar's price for one TLD. Prices are per year, in `currency`."""

    registrar: str
    tld: str                    # no leading dot: "com", "com.pk"
    currency: str               # "USD" or "PKR"
    register: float             # first-year price (often a promo)
    renew: float                # every later year
    transfer: float | None      # transfer-in price, includes +1 year; None = can't transfer in
    block_years: int = 1        # minimum billing period (PKNIC bills 2 years at a time)
    payment_methods: tuple[str, ...] = ()
    notes: str = ""
    source: str = ""


@dataclass
class Plan:
    """The cost of holding one domain for a number of years."""

    years: int                  # years asked for
    years_covered: int          # can be more than asked when billing is in blocks
    total_pkr: float
    strategy: str               # "stay" or "transfer"
    summary: str
    steps: list[str] = field(default_factory=list)

    @property
    def per_year_pkr(self) -> float:
        return self.total_pkr / self.years_covered

    def to_dict(self) -> dict:
        return {
            "years_requested": self.years,
            "years_covered": self.years_covered,
            "total_pkr": round(self.total_pkr),
            "per_year_pkr": round(self.per_year_pkr),
            "strategy": self.strategy,
            "summary": self.summary,
            "steps": self.steps,
        }
