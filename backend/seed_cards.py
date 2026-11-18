"""
One-time script that downloads every legal Commander from Scryfall
and stores them in the cards table.

Run from the project root:
    python -m backend.seed_cards

Takes ~30-60 seconds on the first run (network-bound).
Safe to re-run -- existing cards are updated in place.
"""

import logging
import sys

from .card_loader import get_image_url, load_all_commanders
from .database import SessionLocal, init_db
from .models import Card

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def seed():
    init_db()
    db = SessionLocal()

    logger.info("Fetching commanders from Scryfall...")
    try:
        cards = load_all_commanders()
    except Exception as e:
        logger.error("Failed to fetch cards: %s", e)
        sys.exit(1)

    logger.info("Writing %d cards to database...", len(cards))
    for i, card_data in enumerate(cards):
        card = Card(
            id=card_data["id"],
            name=card_data["name"],
            set_code=card_data.get("set", ""),
            rarity=card_data.get("rarity", ""),
            color_identity=card_data.get("color_identity", []),
            image_url=get_image_url(card_data),
            scryfall_data=card_data,
        )
        db.merge(card)

        if (i + 1) % BATCH_SIZE == 0:
            db.commit()
            logger.info("  ...%d / %d", i + 1, len(cards))

    db.commit()

    count = db.query(Card).count()
    logger.info("Done! %d cards now in database.", count)
    db.close()


if __name__ == "__main__":
    seed()
