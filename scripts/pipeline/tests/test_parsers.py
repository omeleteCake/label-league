from pathlib import Path

import pytest

from parsers.strategies import (
    STRATEGIES,
    parse_inline_json,
    parse_json_ld,
    parse_meta_description,
    parse_next_data,
    try_parse,
)


STRATEGY_NAMES = {name for name, _ in STRATEGIES}


def test_try_parse_empty_html():
    assert try_parse("") is None
    assert try_parse("   ") is None


def test_try_parse_no_listener_info():
    html = """
    <!DOCTYPE html>
    <html>
      <head><title>Unrelated</title></head>
      <body><p>No numbers here.</p></body>
    </html>
    """
    assert try_parse(html) is None


def test_meta_description_integer():
    html = """
    <html><head>
      <meta name="description" content="Listen on Spotify. Artist · 1,234,567 monthly listeners.">
    </head></html>
    """
    assert try_parse(html) == (1_234_567, "meta_description")


def test_meta_description_suffix_millions():
    html = """
    <html><head>
      <meta property="og:description" content="Artist · 61.4M monthly listeners.">
    </head></html>
    """
    assert try_parse(html) == (61_400_000, "meta_description")


def test_meta_description_suffix_thousands():
    html = """
    <html><head>
      <meta property="og:description" content="Artist · 5K monthly listeners.">
    </head></html>
    """
    assert try_parse(html) == (5_000, "meta_description")


def test_next_data_only():
    html = """
    <html><head></head><body>
      <script id="__NEXT_DATA__" type="application/json">
        {"props":{"pageProps":{"artist":{"monthlyListeners":54321}}}}
      </script>
    </body></html>
    """
    result = try_parse(html)
    assert result == (54_321, "next_data")


def test_json_ld_structured_key():
    html = """
    <html><head>
      <script type="application/ld+json">
        {"@context":"http://schema.org","@type":"MusicGroup","name":"X","monthlyListeners":12345}
      </script>
    </head></html>
    """
    result = try_parse(html)
    assert result == (12_345, "json_ld")


def test_json_ld_description_string():
    html = """
    <html><head>
      <script type="application/ld+json">
        {"@context":"http://schema.org","@type":"MusicGroup","name":"X",
         "description":"Listen on Spotify. Artist · 8.2M monthly listeners."}
      </script>
    </head></html>
    """
    result = try_parse(html)
    assert result == (8_200_000, "json_ld")


def test_inline_json_only():
    html = """
    <html><head></head><body>
      <script>window.data = {"artist":{"monthlyListeners": 99999}};</script>
    </body></html>
    """
    result = try_parse(html)
    assert result == (99_999, "inline_json")


def test_inline_json_skips_application_json_type():
    html = """
    <html><head></head><body>
      <script type="application/json">{"monthlyListeners":99999}</script>
    </body></html>
    """
    assert try_parse(html) is None
    assert parse_inline_json(_soup(html)) is None


def test_per_strategy_isolation():
    meta_only = '<html><head><meta name="description" content="Artist · 1,000,000 monthly listeners."></head></html>'
    next_only = '<html><body><script id="__NEXT_DATA__" type="application/json">{"monthlyListeners":2000}</script></body></html>'
    ld_only = '<html><head><script type="application/ld+json">{"monthlyListeners":3000}</script></head></html>'
    inline_only = '<html><body><script>x={"monthlyListeners":4000}</script></body></html>'

    assert parse_meta_description(_soup(meta_only)) == 1_000_000
    assert parse_next_data(_soup(meta_only)) is None
    assert parse_json_ld(_soup(meta_only)) is None
    assert parse_inline_json(_soup(meta_only)) is None

    assert parse_next_data(_soup(next_only)) == 2_000
    assert parse_meta_description(_soup(next_only)) is None
    assert parse_json_ld(_soup(next_only)) is None
    assert parse_inline_json(_soup(next_only)) is None

    assert parse_json_ld(_soup(ld_only)) == 3_000
    assert parse_meta_description(_soup(ld_only)) is None
    assert parse_next_data(_soup(ld_only)) is None
    assert parse_inline_json(_soup(ld_only)) is None

    assert parse_inline_json(_soup(inline_only)) == 4_000
    assert parse_meta_description(_soup(inline_only)) is None
    assert parse_next_data(_soup(inline_only)) is None
    assert parse_json_ld(_soup(inline_only)) is None


def _soup(html: str):
    from parsers.strategies import _make_soup
    return _make_soup(html)


def _fixture_params(fixtures_dir: Path):
    paths = sorted(fixtures_dir.glob("*.html"))

    if not paths:
        return [pytest.param(None, marks=pytest.mark.skip(reason="no html fixtures present"))]

    return [pytest.param(path, id=path.name) for path in paths]


@pytest.fixture
def fixture_paths(fixtures_dir: Path) -> list[Path]:
    return sorted(fixtures_dir.glob("*.html"))


def test_fixtures(fixture_paths: list[Path]):
    if not fixture_paths:
        pytest.skip("no html fixtures present")

    for path in fixture_paths:
        html = path.read_text(encoding="utf-8")
        result = try_parse(html)

        assert result is not None, f"no strategy matched {path.name}"

        value, strategy = result
        assert 1_000 < value < 500_000_000, f"{path.name}: implausible count {value}"
        assert strategy in STRATEGY_NAMES, f"{path.name}: unknown strategy {strategy}"
