# domain-deal-finder

An AI agent that finds cheap domain names usable in Pakistan and works out the cheapest way to hold one for
**1, 2, 3, 4 or 5 years**, in PKR.

Give it a keyword. Claude brainstorms name ideas (synonyms, Roman Urdu, city names, prefixes and suffixes), then plain
code checks which names are free, compares registrar prices, and calculates the total cost of each plan. The model never
guesses a price or whether a name is free: those numbers only come from the tools.

## Why multi-year totals matter

Registrars make their money on renewals. A `.store` domain is $2.57 for year one at Porkbun, then $43.77 **every year
after that**. The tool always compares the total cost of the whole period, and considers two strategies:

- **Stay:** register at one registrar and renew there.
- **Transfer:** take the cheap first year at one registrar, then after 60 days transfer to another with cheaper
  renewals. A transfer usually adds a year, so it doubles as your year-2 renewal.

`.pk` domains come from PKNIC at **Rs 2,100/year for Pakistan-based registrants, billed in 2-year blocks** (from
1 Aug 2026). A 1, 3 or 5-year `.pk` plan therefore really buys 2, 4 or 6 years, and the output says so.

## Setup (WSL)

```bash
cd "/mnt/f/Agentic AI/domain-deal-finder"
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

The `find` command (the AI agent) needs an Anthropic API key: `export ANTHROPIC_API_KEY=...`. Everything else works
without one.

## Usage

```bash
python -m ddf find "biryani" --years 3 --budget 6000     # AI agent: ideas -> availability -> cheapest plans
python -m ddf check biryani.pk getbiryani.store           # are these free?
python -m ddf plans getbiryani.store                      # cheapest 1-5 year plans for one domain
python -m ddf tlds --years 3                              # which TLDs are cheapest to hold for 3 years
```

Settings (environment variables):

| Variable | Default | Meaning |
|---|---|---|
| `DDF_CARD_MARKUP` | `0.05` | Extra cost of paying in USD with a Pakistani card (bank FX markup + advance tax). **Placeholder; set your bank's real rate.** |
| `DDF_USD_PKR` | live rate | Pin the exchange rate |
| `DDF_HAS_INTL_CARD` | `1` | Set `0` if you can only pay locally; USD-priced registrars are then excluded |
| `DDF_MODEL` | `claude-opus-5` | Claude model used by `find` |

## Data sources

| What | Source | Key needed |
|---|---|---|
| Prices for ~900 TLDs | Porkbun public pricing API | No |
| `.pk` prices | PKNIC, entered in `data/manual_prices.csv` | - |
| Availability (most TLDs) | RDAP, routed via the IANA bootstrap file | No |
| Availability (`.pk`) | PKNIC's lookup page | No |
| Real vs. alternative-root TLDs | IANA root zone list (drops Handshake TLDs that don't resolve in normal browsers) | No |
| USD to PKR | open.er-api.com | No |

Prices are cached for 24 hours and availability for 1 hour in `data/cache.sqlite`.

## Adding registrars

- **No API (Pakistani resellers, Cloudflare, etc.):** add a row to `data/manual_prices.csv`. Prices are per year;
  `block_years` is the minimum billing period; leave `transfer` empty if transfers in aren't possible. A second
  registrar for a TLD is what makes transfer strategies appear.
- **Has an API (NameSilo, Dynadot, Namecheap...):** add a module in `ddf/registrars/` exposing `NAME` and
  `fetch_offers(client) -> list[Offer]`, then list it in `LIVE_SOURCES` in `ddf/registrars/__init__.py`.

## Caveats

- "Available" means the registry has no record. Premium names and reserved words only show up at checkout.
- Some country TLDs (e.g. `.us`, `.ca`, `.eu`) restrict who may register them.
- Prices change. Confirm at checkout before paying.

## Tests

```bash
python -m pytest
```
