---
name: find-domains
description: Find cheap, available domain names for a keyword and the cheapest way to hold them for 1-5 years in PKR, using this repo's ddf tool. Use when the user asks to find, search, suggest, compare or price domain names, or asks what a domain would cost over several years. No Anthropic API key needed - Claude Code itself does the brainstorming.
---

# Find domains with the ddf tool

You are the brainstorming part of the agent. The `ddf` CLI in this repo is the source of truth for availability
and prices. Never state a price or say a name is free unless `ddf` output says so.

Run every command from the repo root with the virtualenv active (`. .venv/bin/activate`; create it per the README if
missing). If the user's machine setup says commands run inside WSL, wrap them accordingly.

## Steps

1. **Understand the ask.** Keyword(s), how many years they care about (default 3), budget in PKR if any, preferred
   TLDs, and what the site is for.

2. **Brainstorm 30-60 names** (without TLDs first): the keyword itself, synonyms, Roman Urdu equivalents, Pakistani
   city or regional flavour (lahori, karachi, desi, pak...), short prefixes/suffixes (get, my, try, hq, hub, wala,
   bazaar), and short two-word blends. Keep them short, easy to spell and say aloud. Avoid obvious brand names.

3. **Pick TLDs.** Usually `.pk` and `.com.pk` (local trust) and `.com`. If the user wants cheap alternatives, run
   `python -m ddf tlds --years <N> --limit 30` and pick well-known ones from that list (e.g. `.store`, `.online`,
   `.xyz`, `.site`). Prefer TLDs a Pakistani audience will recognise over obscure ones.

4. **Check and rank in one go.** Pass full domain names (at most ~80 per call to stay polite with the registries):
   ```
   python -m ddf suggest --names name1.pk name1.com name2.com.pk ... --years <N> [--budget <PKR>] --json
   ```
   The JSON has `rows` (free, within budget), `over_budget`, `unknown`, and each row's cheapest plan per year
   (`best["1"]` ... `best["5"]`). A `via` of `dns` means the check was DNS-only and must be confirmed at a registrar.
   Iterate: if too few good names are free, brainstorm more and run again.

5. **Explain the best 3-5 candidates** with `python -m ddf plans <domain>` to get the step-by-step plan.

6. **Answer** with a table: domain, total PKR for each year the user cares about, and the plan. Then short notes:
   - `.pk` / `.com.pk` are billed by PKNIC in 2-year blocks, so 1/3/5-year plans actually buy 2/4/6 years.
   - Cheap first-year TLDs often renew at many times the first-year price; point this out when it applies.
   - Transfer plans (register at one registrar, transfer after 60 days) only appear when a second registrar for that
     TLD is in `data/manual_prices.csv`.
   - The exchange rate and card-markup assumption printed by `ddf` (tell the user to set `DDF_CARD_MARKUP` to their
     bank's real rate).
   - Premium or reserved names only show their real price at checkout.
