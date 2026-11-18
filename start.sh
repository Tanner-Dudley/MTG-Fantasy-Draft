#!/usr/bin/env bash
# Startup script for production (Render, Railway, etc.)
# Seeds the card database if empty, then starts the server.

set -e

echo "=== Checking card database ==="
python -c "
from backend.database import SessionLocal, init_db
from backend.models import Card
init_db()
db = SessionLocal()
count = db.query(Card).count()
db.close()
if count == 0:
    print(f'No cards found. Seeding...')
    from backend.seed_cards import seed
    seed()
else:
    print(f'{count} cards already in database. Skipping seed.')
"

echo "=== Starting server ==="
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
