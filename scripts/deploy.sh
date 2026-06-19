#!/bin/bash
# ─────────────────────────────────────────────────────────────
# deploy.sh — Déployer la dernière version de main sur le VPS
# Usage : ./scripts/deploy.sh
# ─────────────────────────────────────────────────────────────

set -e

VPS_USER="root"
VPS_IP="82.223.115.159"
APP_DIR="/app/civitech"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║        CIVITECH — Déploiement production            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
if [ "$BRANCH" != "main" ]; then
  echo "⚠️  Branche actuelle : $BRANCH (attendu : main)"
  read -p "Continuer quand même ? (oui/non) : " CONFIRM
  if [ "$CONFIRM" != "oui" ]; then echo "Annulé."; exit 1; fi
fi

echo "▶ Déploiement sur le VPS $VPS_IP..."
ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_IP" "
  set -e
  cd $APP_DIR
  echo '  → git pull'
  git pull
  echo '  → docker compose up --build -d'
  docker compose up --build -d 2>&1 | tail -5
  sleep 3
  docker restart civitech_nginx
  sleep 5
  curl -sf http://localhost/api/health && echo '  ✅ Backend OK' || echo '  ❌ Backend KO'
  docker ps --format '  {{.Names}} → {{.Status}}'
"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ Déploiement terminé → https://civitech.genzgov.org"
echo "════════════════════════════════════════════════════════"
