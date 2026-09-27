from ddf.availability import AVAILABLE, TAKEN, UNKNOWN, normalize, parse_pknic, rdap_base
from ddf.registrars import manual, porkbun

BOOTSTRAP = {"services": [[["com", "net"], ["https://rdap.verisign.com/com/v1/"]], [["store"], ["https://rdap.centralnic.com/store/"]]]}


def test_normalize():
    assert normalize(" Biryani.PK ") == "biryani.pk"
    assert normalize("https://shop.com.pk/page") == "shop.com.pk"
    assert normalize("-bad.com") is None
    assert normalize("nodot") is None
    assert normalize("has space.com") is None


def test_rdap_base_uses_last_label():
    assert rdap_base(BOOTSTRAP, "x.com") == "https://rdap.verisign.com/com/v1/"
    assert rdap_base(BOOTSTRAP, "x.store") == "https://rdap.centralnic.com/store/"
    assert rdap_base(BOOTSTRAP, "x.pk") is None


def test_parse_pknic():
    taken = "Domain Name &nbsp; google.pk &nbsp; Domain is Registered ... Expire Date: &nbsp; Dec 1, 2026 &nbsp;"
    assert parse_pknic(taken) == (TAKEN, "expires Dec 1, 2026")
    assert parse_pknic("Domain not found: zz.pk This domain is not registered")[0] == AVAILABLE
    assert parse_pknic("<html>maintenance</html>")[0] == UNKNOWN


def test_porkbun_parse_skips_bad_rows():
    offers = porkbun.parse({
        "com": {"registration": "11.08", "renewal": "11.08", "transfer": "11.08", "coupons": []},
        "broken": {"registration": None},
    })
    assert [(o.tld, o.register) for o in offers] == [("com", 11.08)]


def test_manual_csv_has_pknic_in_two_year_blocks():
    from ddf.config import Settings

    offers = manual.load_offers(Settings().manual_prices_path)
    pk = next(o for o in offers if o.registrar == "PKNIC" and o.tld == "pk")
    assert (pk.currency, pk.block_years, pk.transfer) == ("PKR", 2, None)
    assert not any(o.registrar.startswith("#") for o in offers)
