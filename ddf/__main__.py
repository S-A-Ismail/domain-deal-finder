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
