import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


@dataclass
class SoldListing:
    title: str
    sold_price: Optional[float]
    sold_date: Optional[str]
    url: str
    card_number: Optional[str] = None


def build_search_url(query: str, limit: int = 50) -> str:
    params = {
        "_nkw": quote_plus(query),
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


_TITLE_JUNK = re.compile(
    r"^New Listing"             # leading badge
    r"|Opens in a new window or tab$"  # trailing link text
    r"|\$[\d,]+\.?\d*"         # embedded price
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b",  # embedded date
    re.IGNORECASE,
)


def _clean_title(raw: str) -> str:
    title = _TITLE_JUNK.sub("", raw)
    return " ".join(title.split())


def parse_listings(html: str) -> list[SoldListing]:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(".s-card")
    listings = []

    for item in items:
        title_el = item.select_one(".s-card__title")
        if not title_el:
            continue
        title = _clean_title(title_el.get_text(strip=True))
        if not title:
            continue

        url_el = item.select_one("a[href]")
        url = url_el["href"] if url_el else ""

        price_el = item.select_one(".s-card__price")
        raw_price = price_el.get_text(strip=True) if price_el else ""
        sold_price = parse_price(raw_price)

        date_el = item.select_one("[aria-label='Sold Item']")
        sold_date = None
        if date_el:
            m = re.search(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})", date_el.get_text(" ", strip=True))
            sold_date = m.group(1) if m else None

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

        # Click the "Sold Items" checkbox to filter naturally (URL params get stripped by eBay)
        try:
            sold_checkbox = page.locator("text=Sold Items").first
            sold_checkbox.click(timeout=8000)
            page.wait_for_selector(".s-card__title", timeout=15000)
        except Exception:
            pass  # Let debug mode reveal what loaded if selectors are wrong

        # Re-navigate with Best Match sort + explicit page size so results span the
        # full 90-day window instead of defaulting to most-recently-sold (today only)
        current_url = page.url
        if "LH_Sold" in current_url:
            sep = "&" if "?" in current_url else "?"
            if "_sop=" not in current_url:
                current_url += f"{sep}_sop=1"
                sep = "&"
            if "_ipg=" not in current_url:
                current_url += f"{sep}_ipg={min(limit, 240)}"
            page.goto(current_url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_selector(".s-card__title", timeout=15000)
            except Exception:
                pass

        html = page.content()
        browser.close()

    return parse_listings(html)[:limit], html
