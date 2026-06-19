#!/bin/bash
# ─────────────────────────────────────────────────────────────
# restore-db.sh — Restaurer un backup MySQL
# Usage : ./restore-db.sh /root/backups/civitech_2026-06-08_02-00.sql.gz
#
# ⚠️  ATTENTION : écrase toutes les données actuelles de la DB
# ─────────────────────────────────────────────────────────────

set -e

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage : $0 <chemin_vers_backup.sql.gz>"
  echo ""
  echo "Backups disponibles :"
  ls /root/backups/civitech_*.sql.gz 2>/dev/null | sort -r | head -10
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Fichier introuvable : $BACKUP_FILE"
  exit 1
fi

# Lire le .env
ENV_FILE="/app/civitech/.env"
DB_HOST=$(grep "^DB_HOST=" "$ENV_FILE" | cut -d'=' -f2)
DB_PORT=$(grep "^DB_PORT=" "$ENV_FILE" | cut -d'=' -f2)
DB_NAME=$(grep "^DB_NAME=" "$ENV_FILE" | cut -d'=' -f2)
DB_USER=$(grep "^DB_USER=" "$ENV_FILE" | cut -d'=' -f2)
DB_PASSWORD=$(grep "^DB_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)

echo "⚠️  ATTENTION : cette opération va écraser TOUTES les données de '$DB_NAME'"
echo "Fichier source : $BACKUP_FILE"
echo ""
read -p "Confirmer ? (oui/non) : " CONFIRM

if [ "$CONFIRM" != "oui" ]; then
  echo "Annulé."
  exit 0
fi

echo "[RESTORE] Démarrage : $(date)"

gunzip < "$BACKUP_FILE" | mysql \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --user="$DB_USER" \
  --password="$DB_PASSWORD" \
  "$DB_NAME"

echo "[RESTORE] ✅ Base restaurée depuis $BACKUP_FILE"
echo "[RESTORE] Terminé : $(date)"
