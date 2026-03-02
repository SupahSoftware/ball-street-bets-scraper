import os
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from scraper.models import Base, Listing


def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return create_engine(url)


def create_tables(engine) -> None:
    Base.metadata.create_all(engine)


def upsert_listing(session: Session, listing: Listing) -> None:
    """Insert or update a listing. Last write of the day wins."""
    stmt = (
        insert(Listing)
        .values(
            unique_id=listing.unique_id,
            player_name=listing.player_name,
            serial=listing.serial,
            year=listing.year,
            set=listing.set,
            price=listing.price,
            created_at=listing.created_at,
            card_title=listing.card_title,
        )
        .on_conflict_do_update(
            index_elements=["unique_id"],
            set_={
                "player_name": listing.player_name,
                "price": listing.price,
                "created_at": listing.created_at,
                "card_title": listing.card_title,
            },
        )
    )
    session.execute(stmt)


def fetch_recent(engine, limit: int) -> list[Listing]:
    with Session(engine) as session:
        return (
            session.query(Listing)
            .order_by(Listing.created_at.desc())
            .limit(limit)
            .all()
        )
