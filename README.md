# Ball Street Bets Scraper

A self-hosted service that scrapes eBay sold listings for sports cards, stores results in PostgreSQL, and is designed to run as a daily scheduled job inside Docker on a homeserver.

---

## Vision

The end state is a Docker Compose service running on a homeserver that:

- Runs a daily cron at **10:00 AM America/Chicago** and scrapes all configured queries
- Applies filters to remove graded cards, parallels, and off-topic listings
- Writes filtered results to a local PostgreSQL database (one record per card per day — last write of day wins)
- Is queryable via CLI for ad-hoc lookups and debugging

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Homeserver (Docker)            │
│                                             │
│  ┌─────────────┐      ┌──────────────────┐  │
│  │   Scraper   │─────>│  Local Postgres  │  │
│  │  (Python)   │      │                  │  │
│  └─────────────┘      └──────────────────┘  │
└─────────────────────────────────────────────┘
```

Remote sync is a future phase (see below).

### Components

| Component | Responsibility |
|---|---|
| **Scraper** | Fetches eBay sold listings via Playwright, parses HTML, extracts structured data |
| **Filters** | Removes graded cards, numbered parallels (/XX), and listings missing a card number |
| **Query List** | Manually maintained list of search queries, one file, updated each season |
| **Local DB** | PostgreSQL, written to daily by the cron job |
| **CLI** | Ad-hoc scrapes (no DB write), DB dumps, and debugging |

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ |
| HTML Parsing | BeautifulSoup4 + lxml |
| JS Rendering | Playwright (Chromium) + playwright-stealth |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| CLI | typer + rich |
| Scheduling | APScheduler |
| Containerization | Docker + Docker Compose |

---

## Project Phases

### Phase 1 — CLI Proof of Concept ✅ Done
- Playwright scraper with stealth
- Filters: graded cards, numbered parallels, missing card number
- CLI `search` command with `--debug`, `--limit`, `--filter`
- No database, no scheduling, no Docker

### Phase 2 — PostgreSQL + Query List ✅ Done
- `scraper/queries.py` — flat list of all search queries, manually maintained
- `scraper/models.py` — SQLAlchemy model for the `listings` table
- `scraper/db.py` — connection setup, upsert logic
- CLI `run` command — loops all queries, filters, writes to DB
- CLI `dump` command — prints most recent N records from DB

### Phase 3 — Docker + Daily Cron ✅ Done
- `Dockerfile` + `docker-compose.yml`
- APScheduler cron at 10:00 AM America/Chicago
- Iterates all queries with a 5-second delay between each
- Scraper and Postgres run as separate services in the same Compose stack

### Phase 4 — Remote Sync (future)
- Scheduled push of new records to a remote PostgreSQL instance
- Same schema both sides, no translation layer

---

## Database Schema

Table: `listings`

| Column | Type | Notes |
|---|---|---|
| `unique_id` | text (PK) | `{year}-{serialNoChars}-{mmddyyyy}` — e.g. `2025-CPAJB-03012026` |
| `player_name` | text | See known gaps below |
| `serial` | text | Full card number string, e.g. `#CPA-JB` |
| `year` | int | Card year, taken from the query |
| `set` | text | e.g. `Bowman`, `Topps Chrome` |
| `price` | int | Sale price in pennies (e.g. `$3.59` → `359`) |
| `created_at` | timestamp | Date this row was written, not the eBay sold date |
| `card_title` | text | Raw listing title as scraped |

**Upsert behavior:** one record per `unique_id` per day. If a card is seen multiple times in a day, the last write wins (`ON CONFLICT DO UPDATE`).

---

## Query List

Queries live in `scraper/queries.py` as a plain Python list. New entries are added manually each season as new sets drop (e.g. each year of Bowman, Topps Chrome, etc.).

```python
QUERIES = [
    "2025 Bowman #CPA-",
    "2025 Topps Chrome #USC",
    # add new seasons here
]
```

---

## CLI Usage

### Ad-hoc search (no DB write)
```bash
python -m scraper search "2025 Bowman #CPA-" --limit 50
python -m scraper search "2025 Bowman #CPA-" --debug --limit 240
```

### Run all queries and write to DB
```bash
python -m scraper run
```

### Dump recent DB records
```bash
python -m scraper dump
python -m scraper dump --limit 50
```

---

## Repository Structure

```
ball-street-bets-scraper/
├── scraper/
│   ├── __init__.py
│   ├── __main__.py        # CLI entry point
│   ├── cli.py             # typer commands (search, run, dump)
│   ├── ebay.py            # scraping + HTML parsing
│   ├── filters.py         # graded/parallel/card-number filtering
│   ├── runner.py          # core query loop, shared by CLI and scheduler
│   ├── scheduler.py       # APScheduler cron — Docker container entrypoint
│   ├── queries.py         # query list, edit this each season
│   ├── models.py          # SQLAlchemy model + unique_id builder
│   └── db.py              # DB connection, upsert, fetch
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
└── README.md
```

---

## Known Gaps

### Parallel filtering — named parallels without /XX
The current filter catches numbered parallels (e.g. `/25`, `/50`) via regex. It does **not** catch named parallels (e.g. "Gold Raywave", "Black Wave") that don't include a print run denominator. This is a known gap. Filtering by color words alone risks removing players with color last names (Black, Green, Gold, etc.). A curated per-set parallel keyword list is the likely approach but is deferred.

### player_name column
Extracting a reliable player name from eBay listing titles is fragile due to inconsistent seller formatting. Options include title parsing, a card-number-to-player lookup table, or leaving the column NULL and filling it later. This is deferred — the column will be NULL until a reliable approach is implemented.

---

## Notes

- eBay sold listings are accessible without authentication
- The scraper uses Playwright with stealth to handle JS-rendered pages
- A 5-second delay between queries keeps the daily cron well within polite scraping norms
- Results are capped at 240 per query (one eBay page max); multi-page support is not implemented
- If a query returns zero results, this may indicate eBay HTML structure has changed — check `--debug` output
