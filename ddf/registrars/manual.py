"""Prices typed in by hand from registrars that have no API (PKNIC, Pakistani resellers, Cloudflare...)."""

import csv
from pathlib import Path

from ..models import Offer


def load_offers(path: Path) -> list[Offer]:
    if not path.exists():
        return []
    offers = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row.get("registrar") or row["registrar"].startswith("#"):
                continue
            transfer = row.get("transfer", "").strip()
            offers.append(
                Offer(
                    registrar=row["registrar"].strip(),
                    tld=row["tld"].strip().lstrip(".").lower(),
                    currency=row["currency"].strip().upper(),
                    register=float(row["register"]),
                    renew=float(row["renew"]),
                    transfer=float(transfer) if transfer else None,
                    block_years=int(row.get("block_years") or 1),
                    payment_methods=tuple(m.strip() for m in row.get("payment_methods", "").split(";") if m.strip()),
                    notes=row.get("notes", "").strip(),
                    source=f"{row.get('source_url', '').strip()} (checked {row.get('checked_on', '?').strip()})",
                )
            )
    return offers
