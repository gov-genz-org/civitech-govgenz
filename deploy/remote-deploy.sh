#!/usr/bin/env bash
# Déploiement distant via SSH (appelé depuis GitHub Actions).
# Variables requises : VPS_USER, VPS_HOST, VPS_APP_DIR, GIT_SHA

set -euo pipefail

: "${VPS_USER:?VPS_USER requis}"
: "${VPS_HOST:?VPS_HOST requis}"
: "${VPS_APP_DIR:?VPS_APP_DIR requis}"
: "${GIT_SHA:?GIT_SHA requis}"

ssh -o StrictHostKeyChecking=yes "${VPS_USER}@${VPS_HOST}" bash -s <<EOF
set -euo pipefail
cd "${VPS_APP_DIR}"

echo "→ git fetch origin main"
git fetch origin main

echo "→ git reset --hard ${GIT_SHA}"
git reset --hard "${GIT_SHA}"

echo "→ docker compose up --build -d"
docker compose up --build -d

echo "→ docker restart civitech_nginx"
sleep 3
docker restart civitech_nginx

sleep 5
if curl -sf http://localhost/api/health > /dev/null; then
  echo "✅ Backend OK"
else
  echo "❌ Backend health check failed"
  docker ps --format '{{.Names}} → {{.Status}}'
  exit 1
fi

docker ps --format '  {{.Names}} → {{.Status}}'
EOF

echo "✅ Déploiement VPS terminé (${GIT_SHA:0:7})"
