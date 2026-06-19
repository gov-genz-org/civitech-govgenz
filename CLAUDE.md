# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Projet

**Civitech — GoV Gen Z Madagascar** : plateforme civique de transparence pour documenter, vérifier et publier des faits politiques/économiques malgaches. Stack : FastAPI (Python 3.11) + React 18/Vite + MySQL distant + Docker Compose + Nginx.

- **Production** : https://civitech.genzgov.org (VPS 82.223.115.159)
- **Repo GitHub** : https://github.com/ELYSE-GIT/civitech-govgenz (privé)
- **API Swagger** : https://civitech.genzgov.org/docs

---

## Commandes de développement

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API disponible sur http://localhost:8000 — Swagger sur /docs
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # build de production → frontend/dist/
```

### Docker (développement local)
```bash
cp .env.example .env   # puis remplir les valeurs
docker compose -f docker-compose.dev.yml up --build
```

### Déploiement VPS (production)
```bash
# Toujours dans cet ordre :
git push
sshpass -p 'PASSWORD' ssh root@82.223.115.159 \
  "cd /app/civitech && git pull && docker compose up -d --build"
```
⚠️ Ne jamais modifier le serveur directement sans confirmation. Toujours `git push` AVANT le `git pull` sur le VPS.

---

## Architecture

```
civitech-govgenz/
├── backend/            FastAPI app
│   └── app/
│       ├── main.py         Point d'entrée — routers + startup (seed + Redis)
│       ├── config.py       Settings Pydantic (toutes les vars d'env)
│       ├── database.py     SQLAlchemy engine MySQL (pool optimisé)
│       ├── models/         Modèles SQLAlchemy (ORM)
│       ├── routers/        Routes FastAPI (1 fichier = 1 domaine)
│       ├── services/       Logique métier (auth, email, storage, cache, AI)
│       ├── schemas/        Pydantic schemas (validation)
│       └── seed.py         Données initiales au démarrage
├── frontend/           React SPA
│   └── src/
│       ├── App.jsx         Routing React Router v6 (toutes les routes)
│       ├── api/client.js   Tous les appels API (axios, 1 objet par domaine)
│       ├── contexts/       AuthContext (user, login, logout, rôles)
│       ├── pages/          Organisées par rôle : public/, admin/, citizen/
│       └── components/     ui/ (réutilisables) + Layout/ + shared/
├── nginx/              Config Nginx (prod SSL + dev)
├── docker-compose.yml  Production (4 services)
├── docker-compose.dev.yml  Développement (sans SSL)
├── .env                Variables d'environnement (NE PAS committer)
└── docs/               Documentation technique
```

### Flux de données
```
Browser → Nginx (443) → /api/* → FastAPI backend (8000)
                      → /* → React frontend (nginx:80)
```

### Base de données
MySQL distant (207.174.213.251:3306), **pas de migrations Alembic** — `Base.metadata.create_all()` au démarrage. Les colonnes ajoutées après coup doivent être faites via `ALTER TABLE` directement sur le serveur.

---

## Variables d'environnement (.env à la racine)

| Variable | Usage |
|---|---|
| `DB_PASSWORD` | Mot de passe MySQL |
| `SECRET_KEY` | Signature JWT |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Compte admin créé au seed |
| `B2_KEY_ID` / `B2_APPLICATION_KEY` | Backblaze B2 (upload fichiers) |
| `B2_BUCKET_NAME` / `B2_ENDPOINT_URL` / `B2_PUBLIC_URL` | Config bucket B2 |
| `SMTP_USER` / `SMTP_PASSWORD` | Gmail app password pour magic link |
| `REDIS_URL` | Optionnel — cache Redis |
| `VITE_GA_MEASUREMENT_ID` | Google Analytics (frontend build) |

⚠️ **L'env est lu depuis la racine du projet** par docker-compose.yml, **pas** depuis `backend/.env`.

---

## Rôles utilisateurs

```
superadmin > admin > moderator > z_ambassador > z_citizen
```

- `superadmin` : accès total, passe tous les guards automatiquement
- `admin` / `moderator` : staff — fonctions `is_staff()` / `is_privileged()` dans `services/auth.py`
- `z_ambassador` : peut soumettre des faits, référer des citoyens
- `z_citizen` : lecture + alertes + consultations

Guards backend : `require_superadmin`, `require_admin`, `require_moderator`, `require_ambassador` dans `services/auth.py`. Le superadmin passe toujours.

### Matrice des droits par contenu

| Action | z_citizen | z_ambassador | moderator | admin | superadmin |
|---|---|---|---|---|---|
| Lire faits/threads/entités | ✅ | ✅ | ✅ | ✅ | ✅ |
| Soumettre un fait | ❌ | ✅ | ✅ | ✅ | ✅ |
| Créer thread/entité | ❌ | ❌ | ✅ | ✅ | ✅ |
| Vérifier/publier fait | ❌ | ❌ | ✅ | ✅ | ✅ |
| Soumettre une alerte | ✅ | ✅ | ✅ | ✅ | ✅ |
| Modérer alertes | ❌ | ❌ | ✅ | ✅ | ✅ |
| Gérer consultations | ❌ | ❌ | ✅ | ✅ | ✅ |
| Répondre à une consultation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gérer utilisateurs | ❌ | ❌ | ❌ | ✅ | ✅ |
| Paramètres site | ❌ | ❌ | ❌ | ✅ | ✅ |

Route frontend `/dashboard/collecte` (soumission de faits) : restreinte à `z_ambassador` et au-dessus.

---

## Stockage fichiers (Backblaze B2)

Le bucket `civitech` est **privé**. Les fichiers sont servis via un proxy :
- Upload → clé B2 → URL stockée en base sous la forme `/api/media/{key_encodée}`
- `GET /api/media/{key}` → backend génère une presigned URL (1h) → redirect 302
- `services/storage.py` : `upload_avatar()`, `upload_image()`, `upload_document()`
- Pour passer en public (bucket `allPublic`), le compte B2 doit avoir un historique de paiement

---

## Authentification

Deux modes :
1. **Password** : `POST /auth/login` → JWT (1440 min)
2. **Magic link** : `POST /auth/magic-link` → email avec token → `GET /auth/magic-link/verify?token=...` → JWT

Token stocké en `localStorage` (`civitech_token`). L'intercepteur axios l'injecte automatiquement. Expiration 401 → logout automatique + redirect `/login`.

---

## Modules principaux

### Observatoire (faits, threads, entités)
- **Entité** : personne/institution documentée (politicien, entreprise, ONG…)
- **Fait** : événement documenté avec version officielle vs "dessous de l'iceberg", scores gravité/suspicion/opacité (0-10), acteurs liés, sources
- **Thread** : dossier regroupant des faits liés (narrative)
- Champ `images` (JSON string) sur Fact, Thread, Alert → carousel `ImageCarousel.jsx` (YouTube/Vimeo/MP4/images)

### Réactions
- `POST/GET /reactions/{content_type}/{content_id}` — `content_type` : `fact | alert | thread`
- Toggle : même réaction = annulation, réaction différente = changement
- Composant `ReactionBar.jsx` avec optimistic update

### Paramètres site (SiteSettings)
- Table `site_settings` clé/valeur
- `PUBLIC_KEYS` : accessibles sans auth via `GET /settings/public`
- Éditables dans **Paramètres** (admin) avec sauvegarde par section

### Alertes citoyennes
- Workflow : `pending → under_review → verified → published | rejected`
- Admins/modérateurs peuvent publier directement à la création (`is_public=True`, `status=published`)
- Citoyens soumettent en `pending`

### Ambassadeurs
- `verify_code` généré à la création, visible dans le profil si `status=active`
- Page publique `/verifier` pour vérifier un code
- `GET /public/verify-ambassador/{code}`

### Consultations citoyennes
- Workflow : `draft → active → closed → archived`
- Créées et gérées par modérateurs+ (`require_moderator`)
- Questions CRUD complet : `GET/POST /consultations/{id}/questions`, `PATCH/DELETE /consultations/{id}/questions/{qid}`
- Suppression d'une question réindexe automatiquement les `order_index` restants
- Types de questions : `text`, `yes_no`, `single_choice`, `multiple_choice`, `priority_scale`, `satisfaction_scale`
- Résultats agrégés par question : `GET /consultations/{id}/results`
- Tous les 15 secteurs disponibles pour `sector_main` + multi-secteurs dans `sectors_related`

### Secteurs (15 canoniques)
Source de vérité : `SECTOR_LABELS` dans `src/components/ui/SectorBadge.jsx`
```
legal, economy, food, energy, water, education, health,
infrastructure, digital, territories, environment, mines,
security, citizen, tourism
```
Toujours utiliser `Object.entries(SECTOR_LABELS)` pour les filtres et formulaires — ne jamais définir de tableau local de secteurs.
Composant `SectorPicker` disponible dans `ObservatoireAdmin.jsx` (inline) pour la sélection multiple.

### Diaspora / Géographie
Source de vérité : `src/constants/geo.js`
- `REGIONS_MG` : 24 régions de Madagascar
- `DIASPORA_COUNTRIES` : 16 pays (avec emoji drapeau)
- `REGIONS_WITH_DIASPORA` : combinaison avec séparateurs pour les `<select>`
- `LOCATION_SCOPES` : national/regional/diaspora

Tous les formulaires (profil, faits, alertes, entités, collecte) utilisent ces constantes. Le profil affiche un toggle 🇲🇬 Madagascar / ✈️ Diaspora.

### Types d'entités
Source de vérité : `src/constants/entities.js`
- 7 types nationaux : `politician, institution, company, media, ngo, group, person`
- 5 types internationaux : `ptf, intl_org, embassy, foreign_co, diaspora_org`
- `ENTITY_TYPE_CONFIG` : label + icon + couleur par type

---

## Frontend — conventions

### API client (`src/api/client.js`)
Un objet exporté par domaine : `authApi`, `publicApi`, `factsApi`, `threadsApi`, `entitiesApi`, `alertsApi`, `ambassadorsApi`, `consultationsApi`, `adminApi`, `aiApi`, `reactionsApi`, `uploadApi`, `settingsApi`.

### Routing (`App.jsx`)
- `PublicLayout` : header public + page
- `AppLayout` : sidebar collapsible + page (dashboard/admin)
- `PrivateRoute` : redirect `/login` si non connecté, redirect `/dashboard` si mauvais rôle

### Sidebar
- Collapsible (56px icônes / 256px complet)
- État persisté en `localStorage` (`sidebar_collapsed`)
- Bouton toggle sur le bord droit

### Composants UI réutilisables
| Composant | Usage |
|---|---|
| `ImageCarousel` | Carousel images/vidéos (YouTube, Vimeo, MP4, images) |
| `MediaUploader` | Upload vers B2 + liens vidéo externes |
| `ReactionBar` | Boutons 👍/👎 avec optimistic update |
| `ScoreBar` | Barre de score 0-10 colorée |
| `VerificationBadge` | Badge statut de vérification |
| `FactTypeBadge` | Badge type de fait |
| `IcebergCard` | Carte version officielle vs réelle |
| `SectorBadge` | Badge secteur cliquable — exporte aussi `SECTOR_LABELS` et `SECTOR_ICONS` |

### localStorage keys
| Clé | Usage |
|---|---|
| `civitech_token` | JWT d'authentification |
| `civitech_user` | Objet user sérialisé |
| `sidebar_collapsed` | État de la sidebar |
| `tuto_citizen_v1` | Tuto citoyen (`closed` / `dismissed`) |
| `tuto_ambassador_v1` | Tuto ambassadeur (`closed` / `dismissed`) |
| `tuto_admin_v1` | Tuto admin/modérateur (`closed` / `dismissed`) |

Les tutoriels sont des `TutorialCard` (dans `DashboardPage.jsx`) : collapsibles et définitivement masquables. `dismissed` = masqué définitivement, `closed` = replié mais réouvrable.

### Thème (Tailwind)
Variables CSS custom : `--color-primary`, `--color-accent`, `--color-text`, `--color-muted`, `--color-bg`, `--color-surface`, `--color-border`. Classes utilitaires : `card`, `btn-primary`, `btn-secondary`, `input`, `label`, `section-title`, `badge-sector`.

---

## Infrastructure VPS

- **OS** : Linux, Docker Compose, 4 containers : `civitech_backend`, `civitech_frontend`, `civitech_nginx`, `civitech_redis`
- **SSL** : Let's Encrypt (`/etc/letsencrypt`)
- **Logs** : `docker logs civitech_backend --tail=50`
- **Restart** : `docker compose up -d` (recharge l'env) — ⚠️ `docker compose restart` ne recharge PAS le `.env`
- **Accès DB** depuis le backend** : `docker exec civitech_backend python3 -c "from app.database import SessionLocal; ..."`

---

## Points d'attention

- **Pas de migrations** : toute nouvelle colonne = `ALTER TABLE` manuel sur le serveur + code
- **DB distante** : latence ~170ms/requête → éviter les N+1, utiliser `.join()` ou des requêtes groupées
- **`pool_pre_ping=False`** intentionnel pour éviter le RTT supplémentaire
- **Seed au démarrage** : `seed.py` tourne à chaque boot — idempotent (vérifie avant d'insérer)
- **B2 proxy** : les URLs `/api/media/...` en base sont normales — ne pas les remplacer par des URLs B2 directes tant que le bucket est privé
- **Superadmin** : ne jamais l'afficher dans les listes publiques ou l'exposer dans les stats
- **Secteurs** : toujours importer depuis `SECTOR_LABELS` (SectorBadge) — ne jamais créer un tableau local de secteurs dans une page
- **Géographie** : toujours importer depuis `src/constants/geo.js` — source unique pour régions + diaspora
- **Types d'entités** : toujours importer depuis `src/constants/entities.js`
- **Route collecte** (`/dashboard/collecte`) : restreinte à `z_ambassador`+ côté frontend ET backend (`require_ambassador_or_above`)
