from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any, Callable, Iterable, Optional

from bs4 import BeautifulSoup


ParseResult = tuple[int, str]

_SUFFIX_MULTIPLIER = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

_LISTENER_RE = re.compile(
    r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([KMB])?\s+monthly\s+listeners",
    re.IGNORECASE,
)
_INLINE_RE = re.compile(r'"monthlyListeners"\s*:\s*(\d+)')
_KEY_ALIASES = ("monthlyListeners", "monthly_listeners")


def _coerce_listener_string(text: str) -> Optional[int]:
    match = _LISTENER_RE.search(text)

    if not match:
        return None

    number_str = match.group(1)
    suffix = (match.group(2) or "").upper()
    number = Decimal(number_str.replace(",", ""))

    return int(number * _SUFFIX_MULTIPLIER[suffix])


def _walk_json(obj: Any) -> Iterable[tuple[Optional[str], Any]]:
    stack: list[tuple[Optional[str], Any]] = [(None, obj)]

    while stack:
        key, node = stack.pop()
        yield key, node

        if isinstance(node, dict):
            for child_key, child in node.items():
                stack.append((child_key, child))
        elif isinstance(node, list):
            for item in node:
                stack.append((None, item))


def _search_json_for_listener(obj: Any) -> Optional[int]:
    for key, node in _walk_json(obj):
        if key in _KEY_ALIASES and isinstance(node, int) and not isinstance(node, bool):
            return node

        if isinstance(node, str):
            value = _coerce_listener_string(node)

            if value is not None:
                return value

    return None


def _script_text(tag: Any) -> str:
    return tag.string if tag.string else tag.get_text() or ""


def parse_meta_description(soup: BeautifulSoup) -> Optional[int]:
    for attrs in ({"property": "og:description"}, {"name": "description"}):
        tag = soup.find("meta", attrs=attrs)
        content = tag.get("content") if tag else None

        if content:
            value = _coerce_listener_string(content)

            if value is not None:
                return value

    return None


def parse_next_data(soup: BeautifulSoup) -> Optional[int]:
    tag = soup.find("script", id="__NEXT_DATA__", type="application/json")

    if not tag:
        return None

    payload = _script_text(tag)

    if not payload:
        return None

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    for key, node in _walk_json(data):
        if key in _KEY_ALIASES and isinstance(node, int) and not isinstance(node, bool):
            return node

    return None


def parse_json_ld(soup: BeautifulSoup) -> Optional[int]:
    for tag in soup.find_all("script", type="application/ld+json"):
        payload = _script_text(tag)

        if not payload:
            continue

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue

        value = _search_json_for_listener(data)

        if value is not None:
            return value

    return None


def parse_inline_json(soup: BeautifulSoup) -> Optional[int]:
    for tag in soup.find_all("script"):
        script_type = tag.get("type")

        if script_type not in (None, "text/javascript"):
            continue

        text = _script_text(tag)

        if not text:
            continue

        match = _INLINE_RE.search(text)

        if match:
            return int(match.group(1))

    return None


def parse_body_text(soup: BeautifulSoup) -> Optional[int]:
    return _coerce_listener_string(soup.get_text(" ", strip=True))


STRATEGIES: list[tuple[str, Callable[[BeautifulSoup], Optional[int]]]] = [
    ("meta_description", parse_meta_description),
    ("next_data", parse_next_data),
    ("json_ld", parse_json_ld),
    ("inline_json", parse_inline_json),
    ("body_text", parse_body_text),
]


def _make_soup(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def try_parse(html: str) -> Optional[ParseResult]:
    soup = _make_soup(html)

    for name, strategy in STRATEGIES:
        value = strategy(soup)

        if value is not None:
            return (value, name)

    return None
