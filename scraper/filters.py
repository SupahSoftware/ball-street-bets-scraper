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


def apply_filters(listings: list[SoldListing]) -> tuple[list[SoldListing], int, int]:
    """
    Remove graded and parallel listings.
    Returns (kept, graded_removed_count, parallel_removed_count).
    """
    kept = []
    graded_count = 0
    parallel_count = 0

    for listing in listings:
        if is_graded(listing.title):
            graded_count += 1
        elif is_parallel(listing.title):
            parallel_count += 1
        else:
            kept.append(listing)

    return kept, graded_count, parallel_count
