import httpx

from .cache import Cache

FX_URL = "https://open.er-api.com/v6/latest/USD"


def usd_to_pkr(client: httpx.Client, cache: Cache, max_age_seconds: int = 12 * 3600) -> float:
    cached = cache.get("fx:usd_pkr", max_age_seconds)
    if cached:
        return cached
    resp = client.get(FX_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get("result") != "success":
        raise RuntimeError(f"Exchange-rate API error: {data.get('error-type', data)}")
    rate = float(data["rates"]["PKR"])
    cache.put("fx:usd_pkr", rate)
    return rate
