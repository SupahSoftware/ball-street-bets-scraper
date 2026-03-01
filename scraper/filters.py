import re
from scraper.ebay import SoldListing

# Matches any 3 consecutive capital letters followed by a grade number, e.g. PSA 10, CGC 9.5, SGC 8
_GRADED = re.compile(r'\b[A-Z]{3}\s*\d+(?:\.\d+)?\b')

# Matches a print run denominator, e.g. /25, /100, /1
_PARALLEL = re.compile(r'/\d+')


def is_graded(title: str) -> bool:
    return bool(_GRADED.search(title))


def is_parallel(title: str) -> bool:
    return bool(_PARALLEL.search(title))


def parse_card_prefix(query: str) -> tuple[str, bool] | None:
    """
    Extract a card number prefix from the search query.

    Returns (prefix, has_dash) or None if no card number is found.

    Examples:
        "#CPA-"  → ("CPA", True)
        "#BPPA"  → ("BPPA", False)
        "#RA-SO" → ("RA", True)
    """
    m = re.search(r'#([A-Za-z]+)(-?)', query)
    if not m:
        return None
    return m.group(1).upper(), m.group(2) == '-'


def find_card_number(title: str, prefix: str, has_dash: bool) -> str | None:
    """
    Search a listing title for a card number matching the given prefix,
    regardless of how the seller formatted it (#, no #, dash, no dash).
    Returns a normalized card number string, or None if not found.

    With dash    — "CPAJB", "CPA-JB", "#CPAJB", "#CPA-JB" → "#CPA-JB"
    Without dash — "BPPAJB", "BPPA-JB", "#BPPAJB", "#BPPA-JB" → "#BPPAJB"
    """
    pattern = re.compile(
        r'(?<![A-Za-z0-9])#?' + re.escape(prefix) + r'-?([A-Za-z0-9]+)',
        re.IGNORECASE,
    )
    m = pattern.search(title)
    if not m:
        return None
    suffix = m.group(1).upper()
    if has_dash:
        return f'#{prefix}-{suffix}'
    else:
        return f'#{prefix}{suffix}'


def apply_filters(
    listings: list[SoldListing],
    query: str = "",
) -> tuple[list[SoldListing], int, int, int]:
    """
    Remove graded and parallel listings. If the query contains a card number
    prefix, also remove listings that don't match it, and normalize the card
    number on listings that do.

    Returns (kept, graded_removed, parallel_removed, no_card_number_removed).
    """
    card_info = parse_card_prefix(query)

    kept = []
    graded_count = 0
    parallel_count = 0
    no_card_number_count = 0

    for listing in listings:
        if is_graded(listing.title):
            graded_count += 1
        elif is_parallel(listing.title):
            parallel_count += 1
        elif card_info:
            prefix, has_dash = card_info
            card_number = find_card_number(listing.title, prefix, has_dash)
            if card_number is None:
                no_card_number_count += 1
            else:
                listing.card_number = card_number
                kept.append(listing)
        else:
            kept.append(listing)

    return kept, graded_count, parallel_count, no_card_number_count
