#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="$HOME/backups"
KEEP_DAYS=7

main() {
    cd "$(dirname "$0")"
    mkdir -p "$BACKUP_DIR"

    local file="$BACKUP_DIR/mtgdraft-$(date +%F).sql.gz"
    docker compose exec -T db pg_dump -U mtg mtgdraft | gzip > "$file.tmp"
    mv "$file.tmp" "$file"

    find "$BACKUP_DIR" -name 'mtgdraft-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
}

main