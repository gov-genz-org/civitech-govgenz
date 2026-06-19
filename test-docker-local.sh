#!/bin/bash
# ─────────────────────────────────────────────────────────────
# TEST DOCKER COMPOSE EN LOCAL
# Usage : ./test-docker-local.sh
# ─────────────────────────────────────────────────────────────

set -e

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.dev.yml"
BASE_URL="http://localhost"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   CIVITECH — Test Docker Compose (mode local)       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# 1. Vérif Docker
echo "▶ Vérification Docker..."
docker info > /dev/null 2>&1 || { echo "❌ Docker n'est pas lancé. Ouvre Docker Desktop d'abord."; exit 1; }
echo "  Docker OK ✅"

# 2. Build
echo ""
echo "▶ Build des images (peut prendre 2-3 minutes)..."
$COMPOSE build

# 3. Démarrage
echo ""
echo "▶ Démarrage des conteneurs..."
$COMPOSE up -d

# 4. Attente backend
echo ""
echo "▶ Attente du démarrage backend..."
for i in $(seq 1 20); do
  if curl -sf "$BASE_URL/api/health" > /dev/null 2>&1; then
    echo "  Backend OK ✅ ($BASE_URL/api/health)"
    break
  fi
  if [ $i -eq 20 ]; then
    echo "  ❌ Backend ne répond pas après 40s"
    echo "  Logs backend:"
    docker logs civitech_backend --tail 30
    exit 1
  fi
  echo "  Attente... ($i/20)"
  sleep 2
done

# 5. Tests de routes
echo ""
echo "▶ Test des routes principales..."

check() {
  local desc="$1"
  local url="$2"
  local expected="$3"
  local result=$(curl -sf "$url" 2>/dev/null | head -c 200)
  if echo "$result" | grep -q "$expected"; then
    echo "  ✅ $desc"
  else
    echo "  ❌ $desc — attendu: '$expected'"
    echo "     Réponse: $result"
  fi
}

check "Health check"           "$BASE_URL/api/health"          "ok"
check "API root"               "$BASE_URL/api/"                "Civitech"
check "Stats publiques"        "$BASE_URL/api/public/stats"    "facts"
check "Liste entités"          "$BASE_URL/api/entities/"       "items"
check "Liste faits"            "$BASE_URL/api/facts/"          "items"
check "Liste threads"          "$BASE_URL/api/threads/"        "items"
check "Frontend (React SPA)"   "$BASE_URL/"                    "html"

# 6. Résumé
echo ""
echo "▶ État des conteneurs:"
docker compose ps

echo ""
echo "────────────────────────────────────────────────────────"
echo "  Frontend  → $BASE_URL"
echo "  API docs  → $BASE_URL/docs"
echo "  Health    → $BASE_URL/api/health"
echo "────────────────────────────────────────────────────────"
echo ""
echo "Pour arrêter : docker compose down"
echo ""
