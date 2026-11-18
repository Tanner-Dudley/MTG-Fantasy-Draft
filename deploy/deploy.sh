#!/usr/bin/env bash
set -euo pipefail

main() {
    cd "$(dirname "$0")"
    git pull --ff-only
    docker compose pull app
    docker compose up -d
    docker image prune -f
}

main