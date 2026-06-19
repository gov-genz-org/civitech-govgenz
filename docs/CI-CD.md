# CI/CD — Civitech

Pipeline GitHub Actions : tests → build Docker → **déploiement SSH sur le VPS** à chaque push sur `main`.

Dépôt : [gov-genz-org/civitech-govgenz](https://github.com/gov-genz-org/civitech-govgenz)

> **Différence avec govgenz-ci** : pas de serveur staging — un seul environnement `production`. Le code est déployé sur le VPS via `git fetch` + `docker compose up --build`.

---

## Workflow

```text
feature/* / fix/* / hotfix/*  ──push──►  ci/test + ci/build  (pas de deploy)

PR vers main                  ──►       ci/test + ci/build  (pas de deploy)

push main                     ──►       ci/test → ci/build → deploy/production
```

| Check GitHub (ruleset) | Job | Contenu |
|------------------------|-----|---------|
| `ci/test` | `test` | Backend Python (compile + config) + frontend `npm ci` + `npm run build` |
| `ci/build` | `build` | Validation `docker compose config` + artefact stack |
| — | `deploy/production` | SSH → VPS → `git reset` → `docker compose up --build` → health check |

Fichier workflow : [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

---

## Prérequis VPS (une seule fois)

### 1. Code cloné sur le serveur

```bash
ssh root@<VPS_IP>
mkdir -p /app/civitech
cd /app/civitech
git clone https://github.com/gov-genz-org/civitech-govgenz.git .
```

### 2. Clé de déploiement Git sur le VPS (repo privé)

Le job CI fait un `git fetch` **depuis le VPS**. Il faut une clé SSH en lecture seule :

```bash
# Sur le VPS
ssh-keygen -t ed25519 -f ~/.ssh/civitech_deploy -N "" -C "civitech-vps-deploy"
cat ~/.ssh/civitech_deploy.pub
```

Sur GitHub : **Settings → Deploy keys → Add deploy key** (lecture seule), coller la clé publique.

```bash
# Sur le VPS — configurer git pour utiliser cette clé
cat >> ~/.ssh/config <<'EOF'
Host github.com
  IdentityFile ~/.ssh/civitech_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config

# Tester
cd /app/civitech && git fetch origin main
```

### 3. Fichier `.env` sur le VPS (mode manuel — recommandé au départ)

```bash
cd /app/civitech
cp .env.example .env
nano .env   # remplir toutes les valeurs CHANGE_ME
```

### 4. Premier lancement Docker

```bash
docker compose up --build -d
docker restart civitech_nginx
curl http://localhost/api/health
```

### 5. Clé SSH pour GitHub Actions → VPS

Sur **votre Mac** (ou machine de confiance) :

```bash
ssh-keygen -t ed25519 -f ~/.ssh/civitech_github_actions -N "" -C "civitech-gha-deploy"
```

Sur le **VPS** :

```bash
cat >> ~/.ssh/authorized_keys <<'EOF'
<contenu de civitech_github_actions.pub>
EOF
```

La clé **privée** (`civitech_github_actions`) va dans le secret GitHub `VPS_SSH_PRIVATE_KEY`.

---

## Configuration GitHub

### Étape 1 — Créer l'environment `production`

**Settings → Environments → New environment** → nom : `production`

Optionnel : activer **Required reviewers** pour valider chaque deploy manuellement.

### Étape 2 — Secrets (onglet Secrets de l'environment `production`)

| Secret | Obligatoire | Description |
|--------|-------------|-------------|
| `VPS_SSH_PRIVATE_KEY` | **Oui** | Clé privée ED25519 (contenu complet du fichier `.pem` / clé sans passphrase) |
| `VPS_HOST` | **Oui** | IP ou hostname du VPS (ex. `82.223.115.159`) |
| `VPS_USER` | **Oui** | Utilisateur SSH (ex. `root`) |
| `DB_HOST` | Si `DEPLOY_GENERATE_ENV=true` | Hôte MySQL distant |
| `DB_NAME` | Si auto `.env` | Nom de la base |
| `DB_USER` | Si auto `.env` | Utilisateur MySQL |
| `DB_PASSWORD` | Si auto `.env` | Mot de passe MySQL |
| `SECRET_KEY` | Si auto `.env` | Clé JWT (`openssl rand -hex 32`) |
| `ADMIN_PASSWORD` | Si auto `.env` | Mot de passe admin initial |
| `ADMIN_EMAIL` | Non | Défaut : `admin@civitech.genzgov.org` |
| `REDIS_URL` | Non | Défaut : `redis://civitech_redis:6379` |
| `B2_KEY_ID` | Non | Backblaze B2 |
| `B2_APPLICATION_KEY` | Non | Backblaze B2 |
| `B2_BUCKET_NAME` | Non | Défaut : `civitech` |
| `B2_ENDPOINT_URL` | Non | URL endpoint B2 |
| `B2_PUBLIC_URL` | Non | URL publique B2 |
| `SMTP_USER` | Non | Gmail pour magic link |
| `SMTP_PASSWORD` | Non | App password Gmail (16 car.) |
| `SMTP_HOST` | Non | Défaut : `smtp.gmail.com` |
| `SMTP_PORT` | Non | Défaut : `587` |
| `VITE_GA_MEASUREMENT_ID` | Non | Google Analytics (format `G-XXXXXXXX`) |

### Étape 3 — Variables (onglet Variables de l'environment `production`)

| Variable | Obligatoire | Valeur exemple |
|----------|-------------|----------------|
| `VPS_APP_DIR` | **Oui** | `/app/civitech` |
| `APP_URL` | **Oui** | `https://civitech.genzgov.org` (pour le health check post-deploy) |
| `DEPLOY_GENERATE_ENV` | Non | `true` pour générer et pousser le `.env` depuis les secrets ; absent = `.env` VPS préservé |
| `APP_ENV` | Non | `production` |
| `FRONTEND_URL` | Non | `https://civitech.genzgov.org` |
| `CORS_ORIGINS` | Non | `https://civitech.genzgov.org` |
| `VITE_API_URL` | Non | `/api` |
| `EMAIL_FROM_NAME` | Non | `Civitech — GoV Gen Z Madagascar` |

---

## Deux modes pour le `.env`

| Mode | `DEPLOY_GENERATE_ENV` | Comportement |
|------|----------------------|--------------|
| **Manuel** (défaut) | absent ou ≠ `true` | Le `.env` sur le VPS n'est **pas touché** par le CI. Seul le code est mis à jour. |
| **Automatique** | `true` | Le workflow génère `.env` via [`deploy/generate-dotenv.sh`](../deploy/generate-dotenv.sh), l'envoie par `scp`, puis lance Docker. |

### Mode manuel (recommandé pour démarrer)

1. Créer `.env` à la main sur le VPS (voir [SETUP.md](SETUP.md)).
2. Ne **pas** définir `DEPLOY_GENERATE_ENV` (ou le laisser vide).
3. Configurer uniquement les secrets SSH : `VPS_SSH_PRIVATE_KEY`, `VPS_HOST`, `VPS_USER`.
4. Configurer les variables : `VPS_APP_DIR`, `APP_URL`.

### Mode automatique

1. Renseigner **tous** les secrets application listés ci-dessus dans l'environment `production`.
2. Définir `DEPLOY_GENERATE_ENV` = `true`.
3. À chaque deploy, le `.env` VPS est **écrasé** par la version générée depuis GitHub.

> ⚠️ Changer `SECRET_KEY` déconnecte tous les utilisateurs. Ne pas régénérer sans raison.

---

## Ruleset de branche `main` (recommandé)

Comme sur govgenz-ci, protéger `main` :

**Settings → Rules → Rulesets → New ruleset**

| Règle | Valeur |
|-------|--------|
| Branches cibles | `main` |
| Require status checks | `ci/test`, `ci/build` |
| Require pull request | optionnel (1 approbation si équipe) |
| Restrict pushes | admins uniquement ou via PR |

---

## Déclenchement manuel

**Actions → CI → Run workflow** → branche `main` → exécute test + build + deploy.

Utile pour redéployer sans nouveau commit.

---

## Ce qui se passe lors d'un deploy

1. Le runner GitHub génère éventuellement le `.env` (si `DEPLOY_GENERATE_ENV=true`).
2. Connexion SSH au VPS avec `VPS_SSH_PRIVATE_KEY`.
3. Sur le VPS :
   - `git fetch origin main`
   - `git reset --hard <SHA du commit>`
   - `docker compose up --build -d`
   - `docker restart civitech_nginx` (évite le 502 après rebuild)
4. Health check externe : `GET ${APP_URL}/api/health` → HTTP 200.

---

## Dépannage

### `git fetch` échoue sur le VPS

→ Vérifier la deploy key GitHub (lecture seule) et `~/.ssh/config` sur le VPS.

### Health check 502 après deploy

```bash
ssh root@<VPS_IP>
docker restart civitech_nginx
docker logs civitech_backend --tail=50
```

### Backend ne démarre pas

```bash
docker logs civitech_backend --tail=100
# Vérifier .env : DB_HOST, DB_PASSWORD, SECRET_KEY, ADMIN_PASSWORD
```

### `npm run build` échoue en CI

→ Le frontend doit compiler (`frontend/src/pages/` et `components/` complets). Vérifier localement : `cd frontend && npm ci && npm run build`.

### `.env.example` modifié

Le CI affiche un warning sur les PR — mettre à jour les secrets GitHub et `deploy/generate-dotenv.sh` si besoin.

---

## Checklist première mise en service CI/CD

- [ ] VPS : code cloné dans `/app/civitech`
- [ ] VPS : deploy key GitHub configurée (`git fetch` OK)
- [ ] VPS : `.env` créé et `docker compose up` fonctionne
- [ ] VPS : clé publique GitHub Actions dans `authorized_keys`
- [ ] GitHub : environment `production` créé
- [ ] GitHub : secrets `VPS_SSH_PRIVATE_KEY`, `VPS_HOST`, `VPS_USER`
- [ ] GitHub : variables `VPS_APP_DIR`, `APP_URL`
- [ ] GitHub : ruleset `main` avec `ci/test` + `ci/build`
- [ ] Push sur `main` → workflow vert → site accessible

---

## Comparaison govgenz-ci / civitech

| | govgenz-ci | civitech |
|---|-----------|----------|
| Hébergement | FTP mutualisé | VPS Docker |
| Staging | `develop` → FTP staging | ❌ pas de staging |
| Production | `main` → FTP | `main` → SSH + Docker |
| `.env` | Généré ou manuel sur FTP | Généré (scp) ou manuel sur VPS |
| Release tags | Automatiques (`v*`) | Non (ajout possible plus tard) |
