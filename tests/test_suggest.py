from ddf.suggest import generate


def test_keyword_on_every_tld_first():
    names = generate("Mini Lake", tlds=["com", "pk", "store"])
    assert names[:3] == ["minilake.com", "minilake.pk", "minilake.store"]
    assert "mini-lake.com" in names
    assert "getminilake.pk" in names


def test_variants_fall_back_to_given_tlds():
    names = generate("lake", tlds=["io", "dev"])
    assert "getlake.io" in names
    assert not any(n.endswith(".com") for n in names)


def test_extra_words_limit_and_no_duplicates():
    names = generate("lake", extra_words=["data"], limit=500)
    assert "lakedata.com" in names and "datalake.pk" in names
    assert len(names) == len(set(names))
    assert len(generate("lake", limit=5)) == 5


def test_empty_keyword():
    assert generate("!!!") == []
