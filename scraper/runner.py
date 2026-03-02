import logging
import re
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from scraper import ebay
from scraper.db import create_tables, get_engine, upsert_listing
from scraper.filters import apply_filters
from scraper.models import Listing, build_unique_id
from scraper.queries import QUERIES

logger = logging.getLogger(__name__)


def parse_query_meta(query: str) -> tuple[int | None, str | None]:
    """Extract year and set name from a query string like '2025 Bowman #CPA-'."""
    year_match = re.search(r'\b(20\d{2})\b', query)
    year = int(year_match.group(1)) if year_match else None
    set_match = re.search(r'(Bowman|Topps Chrome|Topps|Donruss|Prizm)', query, re.IGNORECASE)
    set_name = set_match.group(1).title() if set_match else None
    return year, set_name


def run_queries(delay: float = 5.0) -> int:
    """
    Run all queries from QUERIES, apply filters, and upsert results to the DB.
    Returns the total number of records written.
    """
    engine = get_engine()
    create_tables(engine)

    total_written = 0

    for i, query in enumerate(QUERIES, start=1):
        logger.info("[%d/%d] %s", i, len(QUERIES), query)
        year, set_name = parse_query_meta(query)

        try:
            listings, _ = ebay.search(query, limit=240)
        except Exception as e:
            logger.error("Error fetching '%s': %s", query, e)
            if i < len(QUERIES):
                time.sleep(delay)
            continue

        listings, graded, parallels, no_num = apply_filters(listings, query)
        logger.info(
            "  %d kept — %d graded, %d parallel, %d no card number",
            len(listings), graded, parallels, no_num,
        )

        if listings:
            now = datetime.now(tz=timezone.utc)
            with Session(engine) as session:
                for listing in listings:
                    price_pennies = round(listing.sold_price * 100) if listing.sold_price else None
                    uid = build_unique_id(listing.card_number, year)
                    row = Listing(
                        unique_id=uid,
                        player_name=None,
                        serial=listing.card_number,
                        year=year,
                        set=set_name,
                        price=price_pennies,
                        created_at=now,
                        card_title=listing.title,
                    )
                    upsert_listing(session, row)
                session.commit()
            logger.info("  Wrote %d records.", len(listings))
            total_written += len(listings)

        if i < len(QUERIES):
            time.sleep(delay)

    return total_written
