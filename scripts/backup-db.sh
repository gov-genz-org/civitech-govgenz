#!/bin/bash
# ─────────────────────────────────────────────────────────────
# backup-db.sh — Backup automatique MySQL pour Civitech
# Lancé chaque nuit par cron : 0 2 * * * /root/scripts/backup-db.sh
#
# Ce script :
#   1. Exporte la base MySQL en fichier .sql.gz
#   2. Garde les 30 derniers jours
#   3. Affiche un résumé dans les logs
# ─────────────────────────────────────────────────────────────

set -e

# ── Config (lu depuis le .env du projet) ─────────────────────
ENV_FILE="/app/civitech/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "[BACKUP ERROR] Fichier .env introuvable : $ENV_FILE"
  exit 1
fi

# Lire les variables du .env
DB_HOST=$(grep "^DB_HOST=" "$ENV_FILE" | cut -d'=' -f2)
DB_PORT=$(grep "^DB_PORT=" "$ENV_FILE" | cut -d'=' -f2)
DB_NAME=$(grep "^DB_NAME=" "$ENV_FILE" | cut -d'=' -f2)
DB_USER=$(grep "^DB_USER=" "$ENV_FILE" | cut -d'=' -f2)
DB_PASSWORD=$(grep "^DB_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)

# ── Répertoire de sauvegarde ──────────────────────────────────
BACKUP_DIR="/root/backups"
mkdir -p "$BACKUP_DIR"

# ── Nom du fichier avec horodatage ────────────────────────────
DATE=$(date +"%Y-%m-%d_%H-%M")
FILENAME="civitech_${DATE}.sql.gz"
FILEPATH="$BACKUP_DIR/$FILENAME"

# ── Backup ────────────────────────────────────────────────────
echo "[BACKUP] $(date) — Démarrage backup $DB_NAME"

mysqldump \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --user="$DB_USER" \
  --password="$DB_PASSWORD" \
  --single-transaction \
  --routines \
  --triggers \
  --add-drop-table \
  "$DB_NAME" | gzip > "$FILEPATH"

SIZE=$(du -sh "$FILEPATH" | cut -f1)
echo "[BACKUP] Fichier créé : $FILEPATH ($SIZE)"

# ── Nettoyage — garder seulement les 30 derniers jours ────────
find "$BACKUP_DIR" -name "civitech_*.sql.gz" -mtime +30 -delete
COUNT=$(ls "$BACKUP_DIR"/civitech_*.sql.gz 2>/dev/null | wc -l)
echo "[BACKUP] Backups conservés : $COUNT fichiers"

echo "[BACKUP] ✅ Terminé — $(date)"
