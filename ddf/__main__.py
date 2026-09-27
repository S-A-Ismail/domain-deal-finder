import argparse
import json
import sys

from .service import DomainService

STATUS_ICON = {"available": "FREE ", "taken": "taken", "unknown": "  ?  ", "invalid": " bad "}


def cmd_check(service: DomainService, args) -> None:
    for r in service.check(args.domains):
        print(f"{STATUS_ICON[r['status']]}  {r['domain']:<40} {r.get('detail', '')}")


def cmd_plans(service: DomainService, args) -> None:
    result = service.plans(args.domain, top=args.top)
    if args.json:
        print(json.dumps(result, indent=2))
        return
    if "error" in result:
        sys.exit(f"{result['domain']}: {result['error']}")
    print(f"{result['domain']}  (.{result['tld']}; compared: {', '.join(result['registrars_compared'])})")
    for years, plans in result["plans_by_years"].items():
        print(f"\n{years} year{'s' if years > 1 else ''}:")
        for i, p in enumerate(plans, 1):
            covered = f" (covers {p['years_covered']} yrs)" if p["years_covered"] != p["years_requested"] else ""
            print(f"  {i}. Rs {p['total_pkr']:>8,}{covered}  {p['summary']}")
            if i == 1:
                for step in p["steps"]:
                    print(f"       - {step}")
    for note in result["notes"]:
        print(f"\nNote: {note}")
    print_basis(result)


def cmd_tlds(service: DomainService, args) -> None:
    result = service.cheapest_tlds(args.years, args.limit)
    print(f"Cheapest TLDs to hold for {args.years} year{'s' if args.years > 1 else ''}:\n")
    for row in result["ranking"]:
        print(f"  .{row['tld']:<14} Rs {row['total_pkr']:>8,}   {row['summary']}")
    print_basis(result)


def cmd_suggest(service: DomainService, args) -> None:
    from .suggest import generate

    tlds = args.tlds.split(",") if args.tlds else None
    extra = args.words.split(",") if args.words else None
    names = args.names or generate(args.keyword, tlds, extra, args.max_checks)
    if not names:
        sys.exit("Nothing to check: give a keyword with letters or digits, or --names.")
    print(f"Checking {len(names)} names...", file=sys.stderr)
    result = service.rank(names, args.years, args.budget)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\nFree names, cheapest to hold for {args.years} years first (total PKR):\n")
    print_rank_table(limit_per_tld(result["rows"], args.per_tld)[: args.top], args.years)
    if args.budget and result["over_budget"]:
        if not result["rows"]:
            print(f"  (nothing under Rs {args.budget:,} for {args.years} years)")
        print(f"\nClosest options over budget:\n")
        print_rank_table(result["over_budget"][:5], args.years)
    elif not result["rows"]:
        print("  (none)")
    print(f"\n{result['checked']} checked: {result['taken']} taken, {len(result['rows'])} free and priced", end="")
    if result["over_budget"]:
        print(f", {len(result['over_budget'])} free but over budget", end="")
    print(".  * = billed in 2-year blocks (covers more years)  ~ = DNS check only, confirm at registrar")
    if result["unknown"]:
        print(f"Couldn't check: {', '.join(result['unknown'])}")
    if result["unpriced"]:
        print(f"Free but no price data: {', '.join(result['unpriced'])}")
    print("Run `python -m ddf plans <domain>` for the step-by-step plan.")
    print_basis(result)


def limit_per_tld(rows: list[dict], per_tld: int) -> list[dict]:
    """Keep the list varied: otherwise ten identically priced .pk names crowd out every other TLD."""
    seen: dict[str, int] = {}
    kept = []
    for row in rows:
        tld = row["domain"].split(".", 1)[1]
        seen[tld] = seen.get(tld, 0) + 1
        if seen[tld] <= per_tld:
            kept.append(row)
    return kept


def print_rank_table(rows: list[dict], years: int) -> None:
    if not rows:
        return
    print(f"  {'domain':<32}" + "".join(f"{str(n) + ' yr':>10}" for n in range(1, 6)) + "   plan")
    for row in rows:
        cells = ""
        for n in range(1, 6):
            p = row["best"][n]
            mark = "*" if p["years_covered"] != p["years_requested"] else " "
            cells += f"{p['total_pkr']:>9,}{mark}"
        name = row["domain"] + (" ~" if row["via"] == "dns" else "")
        print(f"  {name:<32}{cells}   {row['best'][years]['summary']}")


NO_KEY_HELP = """The `find` command needs an Anthropic API key.
  1. Create one at https://console.anthropic.com/settings/keys
  2. Add it to your shell:  echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc && source ~/.bashrc
The check, plans and tlds commands work without a key."""


def cmd_find(service: DomainService, args) -> None:
    import anthropic

    from . import agent

    request = f"Keyword: {args.keyword}."
    if args.years:
        request += f" I care most about holding it for {args.years} years."
    if args.budget:
        request += f" Budget: Rs {args.budget:,} total."
    if args.tlds:
        request += f" Preferred TLDs: {args.tlds}."
    try:
        print(agent.run(request, service))
    except anthropic.AuthenticationError:
        sys.exit("Anthropic rejected the API key (401). Check ANTHROPIC_API_KEY.\n\n" + NO_KEY_HELP)
    except TypeError as e:
        # The SDK raises TypeError before sending anything when it finds no credentials at all.
        if "Could not resolve authentication method" not in str(e):
            raise
        sys.exit(NO_KEY_HELP)


def print_basis(result: dict) -> None:
    print(
        f"\nPrices in PKR at USD 1 = Rs {result['usd_pkr_rate']} plus {result['card_markup_pct']}% card markup "
        f"on USD prices (set DDF_CARD_MARKUP to your bank's real rate)."
    )
    for w in result["warnings"]:
        print(f"Warning: {w}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="ddf", description="Find cheap domains for Pakistan and the cheapest 1-5 year plans.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="check whether domains are free")
    p.add_argument("domains", nargs="+")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("plans", help="cheapest 1-5 year plans for one domain")
    p.add_argument("domain")
    p.add_argument("--top", type=int, default=3, help="plans to show per holding period")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_plans)

    p = sub.add_parser("tlds", help="rank TLDs by total cost over N years")
    p.add_argument("--years", type=int, default=3, choices=range(1, 6))
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_tlds)

    p = sub.add_parser("suggest", help="no-AI search: generate name variations, check them, rank by cost")
    p.add_argument("keyword", nargs="?", default="")
    p.add_argument("--names", nargs="+", help="skip generation and rank exactly these domains")
    p.add_argument("--years", type=int, default=3, choices=range(1, 6), help="holding period to sort by")
    p.add_argument("--budget", type=int, help="hide names costing more than this (PKR) for --years")
    p.add_argument("--tlds", help='TLDs to try, e.g. "com,pk,com.pk,store"')
    p.add_argument("--words", help='extra words to combine with the keyword, e.g. "data,lake"')
    p.add_argument("--max-checks", type=int, default=80, help="cap on names looked up")
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--per-tld", type=int, default=3, help="max names shown per TLD")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_suggest)

    p = sub.add_parser("find", help="AI agent: brainstorm names from a keyword, check them and price them")
    p.add_argument("keyword")
    p.add_argument("--years", type=int, choices=range(1, 6))
    p.add_argument("--budget", type=int, help="total budget in PKR")
    p.add_argument("--tlds", help='preferred TLDs, e.g. "pk,com.pk,com"')
    p.set_defaults(func=cmd_find)

    args = parser.parse_args()
    args.func(DomainService(), args)


if __name__ == "__main__":
    main()
