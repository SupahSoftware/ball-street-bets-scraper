import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


@dataclass
class SoldListing:
    title: str
    sold_price: Optional[float]
    sold_date: Optional[str]
    url: str


def build_search_url(query: str, limit: int = 50) -> str:
    params = {
        "_nkw": query.replace(" ", "+"),
        "LH_Sold": "1",
        "LH_Complete": "1",
        "_ipg": str(min(limit, 240)),  # eBay max per page is 240
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://www.ebay.com/sch/i.html?{query_string}"


def parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
    if match:
        try:
            return float(match.group().replace(",", ""))
        except ValueError:
            return None
    return None


def parse_listings(html: str) -> list[SoldListing]:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(".s-card")
    listings = []

    for item in items:
        title_el = item.select_one(".s-card__title")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        url_el = item.select_one("a[href]")
        url = url_el["href"] if url_el else ""

        price_el = item.select_one(".s-card__price")
        raw_price = price_el.get_text(strip=True) if price_el else ""
        sold_price = parse_price(raw_price)

        date_el = item.select_one("[aria-label='Sold Item']")
        sold_date = date_el.get_text(strip=True).replace("Sold", "").strip() if date_el else None

        listings.append(
            SoldListing(
                title=title,
                sold_price=sold_price,
                sold_date=sold_date,
                url=url,
            )
        )

    return listings


def search(query: str, limit: int = 50) -> tuple[list[SoldListing], str]:
    url = build_search_url(query, limit)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Listings load dynamically — wait for cards to appear
        try:
            page.wait_for_selector(".s-card__title", timeout=15000)
        except Exception:
            pass  # Let debug mode reveal what loaded if selectors are wrong

        html = page.content()
        browser.close()

    return parse_listings(html)[:limit], html
