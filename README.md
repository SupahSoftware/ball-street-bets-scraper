# Ball Street Bets Scraper

A tool that scrapes eBay sold listings, stores results in a PostgreSQL database, and syncs data from a local homeserver instance to a remote database on a schedule.

---

## Vision

The end state of this project is a self-hosted service running on a homeserver inside Docker. It will:

- Scrape eBay sold listings on a configurable schedule throughout the day
- Write results to a local PostgreSQL database
- Periodically sync new records to a remote PostgreSQL database
- Be queryable via CLI for ad-hoc lookups and debugging

Both local and remote databases use PostgreSQL so there are no dialect differences, no translation layers, and no surprises when syncing.

---

## Architecture (Planned)

```
┌─────────────────────────────────────────────┐
│              Homeserver (Docker)            │
│                                             │
│  ┌─────────────┐      ┌──────────────────┐  │
│  │   Scraper   │─────>│  Local Postgres  │  │
│  │  (Python)   │      │                  │  │
│  └─────────────┘      └────────┬─────────┘  │
│                                │ scheduled  │
│                                │ sync       │
└────────────────────────────────┼────────────┘
                                 │
                                 ▼
                      ┌──────────────────┐
                      │  Remote Postgres │
                      │  (cloud / VPS)   │
                      └──────────────────┘
```

### Components

| Component | Responsibility |
|---|---|
| **Scraper** | Fetches eBay sold listings pages, parses HTML, extracts structured listing data |
| **Local DB** | PostgreSQL instance running on the homeserver, written to throughout the day |
| **Sync Job** | Scheduled job that pushes new/unsynced local records to the remote DB |
| **Remote DB** | PostgreSQL instance for long-term storage, dashboards, or external tooling |
| **CLI** | Entry point for running scrapes, checking sync status, and querying data |

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.12+ | Best scraping ecosystem, fast iteration |
| HTTP | `httpx` | Async-capable, handles sessions and cookies well |
| HTML Parsing | `BeautifulSoup4` + `lxml` | Fast, battle-tested HTML extraction |
| JS Rendering | `playwright` | Fallback for pages that require JavaScript execution |
| ORM | `SQLAlchemy` | Clean models, DB-agnostic, handles migrations via Alembic |
| Database | PostgreSQL (local + remote) | Same engine everywhere, no translation layer |
| CLI | `typer` | Modern, clean CLI with automatic help text and type validation |
| Scheduling | `APScheduler` | Lightweight in-process scheduler, no extra infrastructure |
| Containerization | Docker + Docker Compose | Reproducible homeserver deployment |

---

## Project Phases

### Phase 1 — CLI Proof of Concept (current)
- Scrape eBay sold listings for a given search term from the command line
- Parse and display structured results (title, sold price, sold date, condition, URL)
- No database, no Docker, no scheduling
- Goal: prove we can reliably extract the data we want

### Phase 2 — Local Database
- Stand up local PostgreSQL
- Store scraped results with deduplication
- Add CLI commands to query stored data

### Phase 3 — Scheduling
- Add APScheduler to run scrapes on a configurable interval throughout the day
- Track what has and hasn't been synced to remote

### Phase 4 — Remote Sync
- Configure remote PostgreSQL connection
- Scheduled sync job pushes unsynced records to remote

### Phase 5 — Docker
- Containerize the scraper and local PostgreSQL with Docker Compose
- Designed to run as a persistent service on a homeserver

---

## Development Setup (Phase 1)

### Prerequisites

- Python 3.12+
- `pip` or `uv` (recommended)

### Install

```bash
# Clone the repo
git clone <repo-url>
cd ball-street-bets-scraper

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# If using playwright for JS rendering
playwright install chromium
```

### Run a scrape

```bash
python -m scraper search "rtx 4090"
```

Options (planned):

```bash
python -m scraper search "rtx 4090" --limit 50
python -m scraper search "rtx 4090" --condition used
python -m scraper search "rtx 4090" --days 30
```

---

## Data Extracted

Each sold listing record captures:

| Field | Description |
|---|---|
| `title` | Listing title |
| `sold_price` | Final sold price (USD) |
| `sold_date` | Date the item sold |
| `condition` | Item condition (New, Used, etc.) |
| `listing_url` | Direct link to the eBay listing |
| `shipping_cost` | Shipping cost if listed |
| `seller` | Seller username |

---

## Repository Structure (Planned)

```
ball-street-bets-scraper/
├── scraper/
│   ├── __init__.py
│   ├── __main__.py        # CLI entry point
│   ├── cli.py             # typer commands
│   ├── ebay.py            # scraping logic
│   ├── models.py          # SQLAlchemy models (Phase 2+)
│   ├── db.py              # database connection (Phase 2+)
│   └── sync.py            # remote sync logic (Phase 4+)
├── tests/
├── docker-compose.yml     # Phase 5
├── Dockerfile             # Phase 5
├── requirements.txt
└── README.md
```

---

## Notes

- eBay sold listings are accessible without authentication but may require rate limiting and polite delays to avoid being blocked
- The scraper targets the `/sch/` endpoint with `LH_Sold=1&LH_Complete=1` query parameters, which filters to completed/sold listings
- Playwright is available as a fallback if eBay begins requiring JavaScript execution to render listing results
