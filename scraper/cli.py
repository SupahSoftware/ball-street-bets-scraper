import csv
import re
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
    query: str = typer.Argument(..., help="Search term, e.g. 'rtx 4090'"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max number of results to return"),
    filter: str = typer.Option(None, "--filter", "-f", help="Only show listings whose title contains this string (case-insensitive)"),
    debug: bool = typer.Option(False, "--debug", help="Dump raw HTML to debug.html for inspection"),
):
    """Search eBay sold listings and display results."""
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
        table.add_row(
            str(i),
            listing.title,
            price,
            listing.sold_date or "—",
        )

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
        console.print(f"[dim]Raw HTML written to debug.html[/dim]")
        console.print(f"[dim]Table written to table_debug.csv[/dim]")
    console.print()
