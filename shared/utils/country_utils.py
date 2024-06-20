from typing import Any, List

import pycountry


def retrieve_existing_countries(name: str) -> List[Any]:
    """Retrieves a list of existing countries that match the given name using fuzzy search."""

    try:
        existing_countries = pycountry.countries.search_fuzzy(name)
    except LookupError:
        existing_countries = []
    return existing_countries
