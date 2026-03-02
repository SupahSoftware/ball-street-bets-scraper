import re
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Listing(Base):
    __tablename__ = "listings"

    unique_id: Mapped[str] = mapped_column(String, primary_key=True)
    player_name: Mapped[str | None] = mapped_column(String, nullable=True)
    serial: Mapped[str | None] = mapped_column(String, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    set: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # pennies
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    card_title: Mapped[str] = mapped_column(Text, nullable=False)


def build_unique_id(serial: str | None, year: int | None, today: date | None = None) -> str:
    """
    Build the unique_id for a listing.
    Format: "{year}-{serialNoChars}-{mmddyyyy}"
    Example: "2025-CPAJB-03012026"
    """
    if today is None:
        today = date.today()
    serial_clean = re.sub(r"[^A-Za-z0-9]", "", serial or "").upper()
    year_part = str(year) if year else "0000"
    date_part = today.strftime("%m%d%Y")
    return f"{year_part}-{serial_clean}-{date_part}"
