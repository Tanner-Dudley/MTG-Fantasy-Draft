"""
Fetches every legal Commander from Scryfall and caches them in memory.

This replaces Draft.py's get_full_commander_database() but has zero
Streamlit dependency, so it can run inside FastAPI.
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"

_card_cache: list[dict] | None = None


def load_all_commanders() -> list[dict]:
    """
    Fetches every legal commander from Scryfall, paginating through all
    results. The result is cached in-memory so subsequent calls return
    instantly.
    """
    global _card_cache
    if _card_cache is not None:
        return _card_cache

    logger.info("Loading commander database from Scryfall (first request)...")
    all_cards: list[dict] = []
    params = {
        "q": "is:commander f:commander game:paper",
        "unique": "cards",
        "order": "name",
    }

    url = SCRYFALL_SEARCH_URL
    has_more = True

    while has_more:
        resp = requests.get(
            url, params=params if url == SCRYFALL_SEARCH_URL else None
        )
        resp.raise_for_status()
        data = resp.json()
        all_cards.extend(data.get("data", []))

        has_more = data.get("has_more", False)
        if has_more:
            url = data.get("next_page")
            time.sleep(0.1)

    logger.info("Commander database loaded: %d cards", len(all_cards))
    _card_cache = all_cards
    return _card_cache


def get_image_url(card: dict) -> str:
    if "image_uris" in card:
        return card["image_uris"]["normal"]
    elif "card_faces" in card:
        return card["card_faces"][0]["image_uris"]["normal"]
    return (
        "https://cards.scryfall.io/large/front/e/c/"
        "ecbeac44-5271-44e5-a7c0-06a096c5aa06.jpg"
    )
