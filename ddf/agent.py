"""Claude brainstorms names and explains results. All availability and prices come from tools, never from the model."""

import json
import sys

import anthropic
from anthropic import beta_tool

from .service import DomainService

SYSTEM = """You help a buyer in Pakistan find cheap, usable domain names and the cheapest way to hold them for 1-5 years.

How to work:
1. From the user's keyword, brainstorm 30-60 candidate names: the keyword itself, synonyms, Roman Urdu equivalents,
   Pakistani city or regional flavour (lahore, karachi, desi...), short prefixes/suffixes (get, my, try, hq, online, pk),
   and sensible hyphen-free combinations. Keep names short, easy to spell and say aloud.
2. Pair names with a spread of TLDs: .pk and .com.pk (local trust), .com, and cheap alternatives. Call cheapest_tlds
   first if you need to know which TLDs are cheap over the user's time horizon.
3. Call check_domains in batches of up to 40. Only keep names whose status is "available".
4. Call get_price_plans for the best 8-15 available names.
5. Answer with a ranked table: domain, cheapest total in PKR for each of 1-5 years (or the years the user asked about),
   and the plan behind it. Then short notes on: transfer tricks you recommend (register at one registrar, transfer after
   60 days to one with cheaper renewals), .pk being billed in 2-year blocks, country TLDs that restrict who may
   register them (for example .us, .ca, .eu), and any names that might clash with a well-known brand or trademark.
   Prefer TLDs a Pakistani audience will recognise and trust over obscure ones, even if slightly dearer.

Rules: quote only prices and availability returned by tools; never estimate them yourself. If a tool reports warnings
or "unknown" availability, say so. Mention the exchange rate and card-markup assumption the prices are based on.
Prices exclude any premium-name surcharge that only appears at checkout."""


def run(request: str, service: DomainService, verbose: bool = True) -> str:
    @beta_tool
    def check_domains(domains: str) -> str:
        """Check whether domain names are unregistered, using RDAP (most TLDs) and PKNIC (.pk).

        Args:
            domains: Comma-separated full domain names, at most 40, e.g. "biryanihouse.pk,getbiryani.com".
        """
        names = [d.strip() for d in domains.split(",") if d.strip()][:40]
        return json.dumps(service.check(names))

    @beta_tool
    def get_price_plans(domain: str) -> str:
        """Cheapest ways to hold one domain for 1, 2, 3, 4 and 5 years, in PKR, across all known registrars.

        Includes plans that register at one registrar and transfer to another for cheaper renewals.

        Args:
            domain: One full domain name, e.g. "getbiryani.store".
        """
        return json.dumps(service.plans(domain))

    @beta_tool
    def cheapest_tlds(years: int, limit: int = 30) -> str:
        """Rank TLDs by the cheapest total cost in PKR to hold a domain for the given number of years.

        Args:
            years: Holding period, 1 to 5.
            limit: How many TLDs to return.
        """
        return json.dumps(service.cheapest_tlds(max(1, min(years, 5)), max(1, min(limit, 100))))

    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model=service.settings.model,
        max_tokens=16000,
        system=SYSTEM,
        tools=[check_domains, get_price_plans, cheapest_tlds],
        messages=[{"role": "user", "content": request}],
        # If a request is ever declined, the API retries it on a fallback model instead of stopping.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    final = None
    for message in runner:
        final = message
        if verbose:
            for block in message.content:
                if block.type == "tool_use":
                    print(f"  -> {block.name}({json.dumps(block.input)[:120]})", file=sys.stderr)
    if final is None:
        return "No response from Claude."
    if final.stop_reason == "refusal":
        return "Claude declined this request."
    return "".join(block.text for block in final.content if block.type == "text")
