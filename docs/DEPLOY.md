# Guide de déploiement — Civitech

---

## Infos serveur

| Élément | Valeur |
|---|---|
| VPS OS | Ubuntu 24.04.4 LTS |
| Docker | 29.1.3 |
| Docker Compose | v5.1.4 |
| Code sur le VPS | `/app/civitech/` |
| Backup v0 | `/app/civitech-v0-backup/` |
| Fichier .env prod | `/app/civitech/.env` (jamais sur GitHub) |

> Les credentials SSH et DB ne sont **jamais** dans ce fichier.  
> Demande-les au responsable technique du projet.

---

## Premier déploiement (depuis zéro)

```bash
# 1. Se connecter au VPS
ssh root@<VPS_IP>

# 2. Cloner le repo
git clone https://github.com/ELYSE-GIT/civitech-govgenz.git /app/civitech
cd /app/civitech

# 3. Créer le .env de production
cp .env.example .env
nano .env  # remplir toutes les valeurs CHANGE_ME

# 4. Lancer
docker compose up --build -d

# 5. Vérifier
docker ps
curl http://localhost/api/health
```

---

## Déploiement d'une mise à jour

```bash
# Sur le VPS
cd /app/civitech
git pull
docker compose up --build -d

# ⚠️ OBLIGATOIRE — redémarrer Nginx après chaque rebuild
docker restart civitech_nginx

# Vérification
docker ps
curl http://localhost/api/health
```

Durée : ~3-5 minutes (rebuild des images).

> **Pourquoi le `docker restart civitech_nginx` ?**
> Quand `docker compose up --build -d` recrée les conteneurs (backend, frontend, redis),
> ils reçoivent de **nouvelles adresses IP** internes dans le réseau Docker.
> Nginx garde les anciennes IPs en mémoire → il ne trouve plus le frontend → **502 Bad Gateway**.
> Le redémarrer force la résolution DNS interne et corrige le problème instantanément.
> Le script `scripts/deploy.sh` le fait automatiquement.

---

## Architecture des conteneurs

```
civitech_nginx     → port 80 + 443 (public)
civitech_frontend  → port 80 interne (React statique)
civitech_backend   → port 8000 interne + externe (FastAPI)
root-n8n-1         → port 5678 (automation, NE PAS TOUCHER)
```

> n8n tourne indépendamment de Civitech — ne jamais `docker compose down` sans précaution.

---

## SSL / HTTPS

Le certificat SSL est géré par **Let's Encrypt + Certbot**.

```bash
# Renouveler le certificat (si expiré)
certbot renew

# Vérifier la date d'expiration
certbot certificates
```

Le nginx.conf monte `/etc/letsencrypt` en lecture seule.

---

## Variables d'environnement de production

Voir `.env.example` pour la liste complète.

Variables critiques à ne jamais laisser vides :
- `DB_PASSWORD` — mot de passe MySQL
- `SECRET_KEY` — clé JWT (min 32 caractères aléatoires)
- `ADMIN_PASSWORD` — mot de passe admin initial
- `CORS_ORIGINS` — domaines autorisés (séparés par virgule)

---

## Backup automatique de la base de données

Un cron job tourne chaque nuit sur le VPS :

```bash
# Voir le cron
crontab -l

# Contenu du script de backup
cat /root/scripts/backup-db.sh
```

Les backups sont stockés dans `/root/backups/` (30 jours de rétention).

### Restaurer un backup

```bash
# Lister les backups disponibles
ls /root/backups/

# Restaurer (remplace toutes les données actuelles !)
gunzip < /root/backups/civitech_2026-06-08.sql.gz | \
  mysql -h DB_HOST -u DB_USER -p DB_NAME
```

---

## Logs

```bash
# Logs en temps réel de tous les conteneurs
docker compose logs -f

# Logs d'un conteneur spécifique
docker logs civitech_backend --tail 100
docker logs civitech_nginx --tail 50

# Logs Nginx sur disque
ls /var/lib/docker/volumes/civitech-govgenz_nginx_logs/
```

---

## Rollback d'urgence

```bash
# Option 1 — Revenir au commit précédent
git log --oneline -5
git reset --hard <COMMIT_ID>
git push --force origin main
docker compose up --build -d

# Option 2 — Restaurer le backup v0 complet
docker compose down
rm -rf /app/civitech
cp -r /app/civitech-v0-backup /app/civitech
docker compose up --build -d
```
