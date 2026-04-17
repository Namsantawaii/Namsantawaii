from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

ENCAR_BASE_URL = "https://www.encar.com"
EXCLUDED_KEYWORDS = ("리스", "장기렌트", "장기 렌트", "리스승계")


@dataclass
class CarListing:
    name: str
    price_manwon: int | None
    mileage_km: int | None
    year: int | None
    detail_link: str


def load_html_from_input(raw_input: str, timeout: int = 10) -> str:
    """Return HTML string from direct HTML input or a URL."""
    text = (raw_input or "").strip()
    if not text:
        raise ValueError("입력값이 비어 있습니다. 엔카 검색결과 URL 또는 HTML을 입력하세요.")

    if text.lower().startswith(("http://", "https://")):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(text, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text

    return text


def parse_encar_listings(html: str, base_url: str = ENCAR_BASE_URL) -> pd.DataFrame:
    """Parse Encar listings from HTML and return a normalized DataFrame."""
    soup = BeautifulSoup(html, "lxml")
    listings = [asdict(item) for item in _extract_listings(soup, base_url=base_url)]

    columns = ["name", "price_manwon", "mileage_km", "year", "detail_link"]
    if not listings:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(listings, columns=columns)


def _extract_listings(soup: BeautifulSoup, base_url: str) -> list[CarListing]:
    selectors = [
        ".srp-item",
        ".item-wrap",
        "li[data-testid='search-item']",
        ".car-item",
        ".list-item",
    ]

    containers: list[Tag] = []
    for selector in selectors:
        found = [node for node in soup.select(selector) if isinstance(node, Tag)]
        if found:
            containers = found
            break

    if not containers:
        # Fallback: use anchors that likely point to detail pages.
        candidates = soup.select("a[href*='/dc/dc_cardetailview.do']")
        containers = [anchor.parent for anchor in candidates if isinstance(anchor.parent, Tag)]

    results: list[CarListing] = []
    seen_links: set[str] = set()
    for container in containers:
        item = _parse_container(container, base_url=base_url)
        if not item:
            continue

        if item.detail_link in seen_links:
            continue
        seen_links.add(item.detail_link)
        results.append(item)

    return results


def _parse_container(container: Tag, base_url: str) -> CarListing | None:
    link_tag = container.select_one("a[href]")
    if not isinstance(link_tag, Tag):
        return None

    href = (link_tag.get("href") or "").strip()
    detail_link = urljoin(base_url, href)

    name = _extract_name(container, link_tag)
    if not name:
        return None

    text = " ".join(container.stripped_strings)
    if _should_exclude_listing(text):
        return None
    price = _extract_price(text)
    mileage = _extract_mileage(text)
    year = _extract_year(text)

    return CarListing(
        name=name,
        price_manwon=price,
        mileage_km=mileage,
        year=year,
        detail_link=detail_link,
    )


def _extract_name(container: Tag, link_tag: Tag) -> str:
    possible_nodes: Iterable[Tag] = [
        *container.select(".model, .tit, .title, .car-name, h2, h3, h4"),
        link_tag,
    ]
    for node in possible_nodes:
        value = node.get_text(" ", strip=True)
        if value:
            return value
    return ""


def _extract_price(text: str) -> int | None:
    m = re.search(r"([\d,]{2,})\s*만원", text)
    if m:
        return int(m.group(1).replace(",", ""))

    m = re.search(r"가격\s*[:：]?\s*([\d,]{2,})", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def _extract_mileage(text: str) -> int | None:
    m = re.search(r"([\d,]{2,})\s*km", text, flags=re.IGNORECASE)
    if not m:
        m = re.search(r"주행\s*[:：]?\s*([\d,]{2,})", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def _extract_year(text: str) -> int | None:
    m = re.search(r"((?:19|20)\d{2})", text)
    if m:
        return int(m.group(1))
    return None


def _should_exclude_listing(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "")).strip().lower()
    return any(keyword.lower() in normalized for keyword in EXCLUDED_KEYWORDS)
