#!/usr/bin/env bash
# Vérifie que les fichiers essentiels du stack Docker sont présents.

set -euo pipefail

root="${1:-.}"
cd "$root"

required=(
  docker-compose.yml
  backend/Dockerfile
  backend/requirements.txt
  backend/app/main.py
  frontend/Dockerfile
  frontend/package.json
  nginx/nginx.conf
  .env.example
  deploy/remote-deploy.sh
  deploy/generate-dotenv.sh
)

for f in "${required[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "verify-stack: fichier manquant : $f" >&2
    exit 1
  fi
done

echo "verify-stack: OK (${#required[@]} fichiers essentiels)"
