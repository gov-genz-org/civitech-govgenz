#!/usr/bin/env bash
# Génère un .env complet (écrase le fichier cible — pas d'ajout / fusion).
# Usage : DB_HOST=... SECRET_KEY=... ./deploy/generate-dotenv.sh chemin/vers/.env

set -euo pipefail

out="${1:-.env}"

require() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "generate-dotenv: variable obligatoire manquante : ${name}" >&2
    exit 1
  fi
}

require DB_HOST
require DB_NAME
require DB_USER
require DB_PASSWORD
require SECRET_KEY
require ADMIN_PASSWORD

if [[ "${SECRET_KEY}" == *CHANGE_ME* ]] || [[ "${ADMIN_PASSWORD}" == *CHANGE_ME* ]]; then
  echo "generate-dotenv: SECRET_KEY ou ADMIN_PASSWORD contient un placeholder." >&2
  exit 1
fi

DB_PORT="${DB_PORT:-3306}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@civitech.genzgov.org}"
APP_ENV="${APP_ENV:-production}"
APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
FRONTEND_URL="${FRONTEND_URL:-https://civitech.genzgov.org}"
CORS_ORIGINS="${CORS_ORIGINS:-https://civitech.genzgov.org}"
REDIS_URL="${REDIS_URL:-redis://civitech_redis:6379}"
B2_BUCKET_NAME="${B2_BUCKET_NAME:-civitech}"
B2_ENDPOINT_URL="${B2_ENDPOINT_URL:-https://s3.us-east-005.backblazeb2.com}"
B2_PUBLIC_URL="${B2_PUBLIC_URL:-https://f005.backblazeb2.com/file/civitech}"
SMTP_HOST="${SMTP_HOST:-smtp.gmail.com}"
SMTP_PORT="${SMTP_PORT:-587}"
EMAIL_FROM_NAME="${EMAIL_FROM_NAME:-Civitech — GoV Gen Z Madagascar}"
VITE_API_URL="${VITE_API_URL:-/api}"
ALGORITHM="${ALGORITHM:-HS256}"
ACCESS_TOKEN_EXPIRE_MINUTES="${ACCESS_TOKEN_EXPIRE_MINUTES:-1440}"

mkdir -p "$(dirname "$out")"
rm -f "$out"

{
  echo "# Généré par GitHub Actions (deploy/generate-dotenv.sh) — ne pas fusionner."
  echo "# Commit : ${GITHUB_SHA:-local}"
  echo ""
  echo "DB_HOST=${DB_HOST}"
  echo "DB_PORT=${DB_PORT}"
  echo "DB_NAME=${DB_NAME}"
  echo "DB_USER=${DB_USER}"
  echo "DB_PASSWORD=${DB_PASSWORD}"
  echo ""
  echo "SECRET_KEY=${SECRET_KEY}"
  echo "ALGORITHM=${ALGORITHM}"
  echo "ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES}"
  echo ""
  echo "APP_ENV=${APP_ENV}"
  echo "APP_HOST=${APP_HOST}"
  echo "APP_PORT=${APP_PORT}"
  echo "FRONTEND_URL=${FRONTEND_URL}"
  echo "CORS_ORIGINS=${CORS_ORIGINS}"
  echo ""
  echo "ADMIN_EMAIL=${ADMIN_EMAIL}"
  echo "ADMIN_PASSWORD=${ADMIN_PASSWORD}"
  echo ""
  echo "REDIS_URL=${REDIS_URL}"
  echo ""
  echo "B2_KEY_ID=${B2_KEY_ID:-}"
  echo "B2_APPLICATION_KEY=${B2_APPLICATION_KEY:-}"
  echo "B2_BUCKET_NAME=${B2_BUCKET_NAME}"
  echo "B2_ENDPOINT_URL=${B2_ENDPOINT_URL}"
  echo "B2_PUBLIC_URL=${B2_PUBLIC_URL}"
  echo ""
  echo "SMTP_HOST=${SMTP_HOST}"
  echo "SMTP_PORT=${SMTP_PORT}"
  echo "SMTP_USER=${SMTP_USER:-}"
  echo "SMTP_PASSWORD=${SMTP_PASSWORD:-}"
  echo "EMAIL_FROM_NAME=${EMAIL_FROM_NAME}"
  echo ""
  echo "VITE_API_URL=${VITE_API_URL}"
  echo "VITE_GA_MEASUREMENT_ID=${VITE_GA_MEASUREMENT_ID:-}"
} > "$out"

chmod 600 "$out"
echo "Fichier .env généré (écrasement complet) : ${out}"
