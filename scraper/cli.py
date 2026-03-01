import re
import typer
from rich.console import Console
from rich.table import Table
from rich import box

from scraper import ebay

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

    if debug:
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(raw_html)
        serials = {m.group() for l in listings for m in re.finditer(r'#[A-Za-z0-9\-]+', l.title)}
        console.print(f"[dim]Raw HTML written to debug.html[/dim]")
        console.print(f"[dim]{len(serials)} unique serial(s) found[/dim]")
    console.print()
