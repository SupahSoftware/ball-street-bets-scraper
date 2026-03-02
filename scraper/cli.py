import csv

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from scraper import ebay
from scraper.filters import apply_filters

app = typer.Typer(help="eBay sold listings scraper.")
console = Console()


@app.callback()
def main():
    """eBay sold listings scraper."""


@app.command()
def search(
    query: str = typer.Argument(..., help="Search term, e.g. '2025 Bowman #CPA-'"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max number of results to return"),
    filter: str = typer.Option(None, "--filter", "-f", help="Only show listings whose title contains this string (case-insensitive)"),
    debug: bool = typer.Option(False, "--debug", help="Dump raw HTML to debug.html for inspection"),
):
    """Search eBay sold listings and display results. Does not write to the database."""
    console.print(f"\n[bold]Searching eBay sold listings for:[/bold] [cyan]{query}[/cyan]\n")

    with console.status("Fetching results..."):
        try:
            listings, raw_html = ebay.search(query, limit=limit)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    listings, graded_removed, parallel_removed, no_serial_removed = apply_filters(listings, query)

    if filter:
        listings = [l for l in listings if filter.lower() in l.title.lower()]
        console.print(f"[dim]Filtered to titles containing:[/dim] [cyan]{filter}[/cyan]\n")

    if not listings:
        console.print("[yellow]No sold listings found.[/yellow]")
        raise typer.Exit()

    table = Table(box=box.SIMPLE_HEAD, show_lines=False)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Title", style="white", max_width=50, no_wrap=False)
    table.add_column("Sold Price", style="green", justify="right", width=12)
    table.add_column("Sold Date", style="blue", width=16)
    for i, listing in enumerate(listings, start=1):
        price = f"${listing.sold_price:,.2f}" if listing.sold_price else "—"
        table.add_row(str(i), listing.title, price, listing.sold_date or "—")

    console.print(table)
    console.print(f"[dim]{len(listings)} result(s) returned[/dim]")
    console.print(f"[dim]{graded_removed} graded cards removed[/dim]")
    console.print(f"[dim]{parallel_removed} parallel cards removed[/dim]")
    console.print(f"[dim]{no_serial_removed} removed (no card number found)[/dim]")

    if debug:
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(raw_html)
        with open("table_debug.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["#", "Card Number", "Title", "Sold Price", "Sold Date", "URL"])
            for i, listing in enumerate(listings, start=1):
                price = f"${listing.sold_price:,.2f}" if listing.sold_price else ""
                writer.writerow([i, listing.card_number or "", listing.title, price, listing.sold_date or "", listing.url])
        console.print("[dim]Raw HTML written to debug.html[/dim]")
        console.print("[dim]Table written to table_debug.csv[/dim]")
    console.print()


@app.command()
def run(
    delay: float = typer.Option(5.0, "--delay", help="Seconds to wait between queries"),
):
    """Run all configured queries and write results to the database."""
    from scraper.runner import run_queries
    from scraper.queries import QUERIES

    console.print(f"\n[bold]Running {len(QUERIES)} queries[/bold] ({delay}s delay between each)\n")
    try:
        total = run_queries(delay=delay)
    except RuntimeError as e:
        console.print(f"[red]DB error:[/red] {e}")
        raise typer.Exit(1)
    console.print(f"\n[bold]Done.[/bold] {total} total records written.\n")


@app.command()
def dump(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of most recent records to show"),
):
    """Print the most recent records from the database."""
    from scraper.db import get_engine, fetch_recent

    try:
        engine = get_engine()
    except RuntimeError as e:
        console.print(f"[red]DB error:[/red] {e}")
        raise typer.Exit(1)

    rows = fetch_recent(engine, limit)

    if not rows:
        console.print("[yellow]No records found.[/yellow]")
        raise typer.Exit()

    table = Table(box=box.SIMPLE_HEAD, show_lines=False)
    table.add_column("unique_id", style="dim", no_wrap=True)
    table.add_column("serial", style="cyan", width=12)
    table.add_column("year", width=6)
    table.add_column("set", width=14)
    table.add_column("price", style="green", justify="right", width=10)
    table.add_column("created_at", style="blue", width=20)
    table.add_column("title", style="white", max_width=45, no_wrap=False)

    for row in rows:
        price = f"${row.price / 100:,.2f}" if row.price is not None else "—"
        created = row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else "—"
        table.add_row(
            row.unique_id,
            row.serial or "—",
            str(row.year) if row.year else "—",
            row.set or "—",
            price,
            created,
            row.card_title,
        )

    console.print(table)
    console.print(f"[dim]{len(rows)} record(s)[/dim]\n")
