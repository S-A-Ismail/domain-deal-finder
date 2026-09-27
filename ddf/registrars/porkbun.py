"""Porkbun publishes prices for every TLD it sells through a public endpoint that needs no API key."""

import httpx

from ..models import Offer

PRICING_URL = "https://api.porkbun.com/api/json/v3/pricing/get"
NAME = "Porkbun"


def fetch_offers(client: httpx.Client) -> list[Offer]:
    resp = client.post(PRICING_URL, json={}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "SUCCESS":
        raise RuntimeError(f"Porkbun pricing error: {data.get('message', data)}")
    return parse(data["pricing"])


def parse(pricing: dict) -> list[Offer]:
    offers = []
    for tld, p in pricing.items():
        try:
            register, renew, transfer = float(p["registration"]), float(p["renewal"]), float(p["transfer"])
        except (KeyError, TypeError, ValueError):
            continue
        offers.append(
            Offer(
                registrar=NAME,
                tld=tld.lower(),
                currency="USD",
                register=register,
                renew=renew,
                transfer=transfer,
                payment_methods=("international card",),
                source=PRICING_URL,
            )
        )
    return offers
