"""Finds the cheapest way to hold a domain for N years. Pure arithmetic, no network, no LLM."""

import math
from dataclasses import dataclass

from .models import Offer, Plan

# Most registrars refuse a transfer in the first 60 days after registration.
TRANSFER_LOCK_DAYS = 60


@dataclass(frozen=True)
class Money:
    usd_pkr: float              # market rate
    card_markup: float = 0.0    # bank FX markup + taxes on foreign card spend, e.g. 0.05 = 5%

    def pkr(self, amount: float, currency: str) -> float:
        if currency == "PKR":
            return amount
        if currency == "USD":
            return amount * self.usd_pkr * (1 + self.card_markup)
        raise ValueError(f"Unsupported currency: {currency}")

    def fmt(self, amount: float, currency: str) -> str:
        if currency == "PKR":
            return f"Rs {amount:,.0f}"
        return f"${amount:,.2f} (Rs {self.pkr(amount, currency):,.0f})"


def _years(start: int, end: int) -> str:
    return f"Year {start}" if start == end else f"Years {start}-{end}"


def stay_plan(offer: Offer, years: int, money: Money) -> Plan:
    """Register at one registrar and renew there for the whole period."""
    covered = math.ceil(years / offer.block_years) * offer.block_years
    total = money.pkr(offer.register, offer.currency) + (covered - 1) * money.pkr(offer.renew, offer.currency)
    steps = [f"Register at {offer.registrar}: year 1 {money.fmt(offer.register, offer.currency)}"]
    if covered > 1:
        steps.append(
            f"{_years(2, covered)} at {offer.registrar}: {covered - 1} x {money.fmt(offer.renew, offer.currency)}"
        )
    if offer.block_years > 1:
        steps.append(f"{offer.registrar} bills in {offer.block_years}-year blocks, so you pay for {covered} years")
    return Plan(years, covered, total, "stay", f"{offer.registrar} for all {covered} yr", steps)


def transfer_plan(first: Offer, second: Offer, years: int, money: Money) -> Plan | None:
    """Take the first-year price at one registrar, then transfer (which adds a year) and renew at another."""
    if years < 2 or first.registrar == second.registrar or second.transfer is None:
        return None
    if first.block_years != 1 or second.block_years != 1:
        return None
    total = (
        money.pkr(first.register, first.currency)
        + money.pkr(second.transfer, second.currency)
        + (years - 2) * money.pkr(second.renew, second.currency)
    )
    steps = [
        f"Register at {first.registrar} for 1 yr: {money.fmt(first.register, first.currency)}",
        f"After {TRANSFER_LOCK_DAYS} days, transfer to {second.registrar} "
        f"(adds year 2): {money.fmt(second.transfer, second.currency)}",
    ]
    if years > 2:
        steps.append(
            f"{_years(3, years)} at {second.registrar}: {years - 2} x {money.fmt(second.renew, second.currency)}"
        )
    summary = f"{first.registrar} year 1, then transfer to {second.registrar}"
    return Plan(years, years, total, "transfer", summary, steps)


def all_plans(offers: list[Offer], years: int, money: Money) -> list[Plan]:
    plans = [stay_plan(o, years, money) for o in offers]
    for first in offers:
        for second in offers:
            plan = transfer_plan(first, second, years, money)
            if plan:
                plans.append(plan)
    # Cheapest total first; on a tie prefer the simpler "stay" plan.
    return sorted(plans, key=lambda p: (round(p.total_pkr), p.strategy != "stay", p.summary))


def best_plans(offers: list[Offer], money: Money, years: range = range(1, 6), top: int = 3) -> dict[int, list[Plan]]:
    return {n: all_plans(offers, n, money)[:top] for n in years}


def cheapest_tlds(offers_by_tld: dict[str, list[Offer]], years: int, money: Money, limit: int = 25) -> list[tuple[str, Plan]]:
    ranked = []
    for tld, offers in offers_by_tld.items():
        plans = all_plans(offers, years, money)
        if plans:
            ranked.append((tld, plans[0]))
    return sorted(ranked, key=lambda item: item[1].total_pkr)[:limit]
