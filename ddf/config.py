import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env_float(name: str, default: float | None) -> float | None:
    value = os.environ.get(name)
    return float(value) if value else default


@dataclass(frozen=True)
class Settings:
    # Extra cost of paying in USD with a Pakistani card: bank FX markup plus advance tax.
    # 5% is a placeholder. Check your bank's schedule of charges and set DDF_CARD_MARKUP.
    card_markup: float = _env_float("DDF_CARD_MARKUP", 0.05)
    # Set DDF_USD_PKR to pin the exchange rate instead of fetching it live.
    usd_pkr_override: float | None = _env_float("DDF_USD_PKR", None)
    # Set DDF_HAS_INTL_CARD=0 if you can only pay locally (JazzCash, Easypaisa, bank transfer).
    has_intl_card: bool = os.environ.get("DDF_HAS_INTL_CARD", "1") != "0"
    model: str = os.environ.get("DDF_MODEL", "claude-opus-5")
    db_path: Path = Path(os.environ.get("DDF_DB", ROOT / "data" / "cache.sqlite"))
    manual_prices_path: Path = ROOT / "data" / "manual_prices.csv"
    price_ttl_seconds: int = 24 * 3600
    availability_ttl_seconds: int = 3600
