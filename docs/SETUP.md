# Guide d'installation locale — Civitech

> Ce guide permet à n'importe qui (humain ou IA) de lancer le projet en local en moins de 10 minutes.

---

## Prérequis

| Outil | Version minimum | Vérifier |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |

> Docker optionnel pour le dev local — obligatoire pour la prod.

---

## 1. Cloner le projet

```bash
git clone https://github.com/ELYSE-GIT/civitech-govgenz.git
cd civitech-govgenz
```

---

## 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Ouvre `.env` et remplis les valeurs manquantes (marquées `CHANGE_ME`) :

```bash
# Les valeurs réelles sont dans le gestionnaire de secrets du projet
# Demande au responsable technique : les infos DB, SECRET_KEY, etc.
```

> Les vraies valeurs ne sont jamais dans le code ni sur GitHub.  
> Pour y accéder, contacte le responsable du projet.

---

## 3. Lancer le backend

```bash
cd backend

# Créer et activer le virtualenv Python
python3 -m venv .venv
source .venv/bin/activate          # Mac/Linux
# .venv\Scripts\activate           # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur de développement
uvicorn app.main:app --reload --port 8000
```

Backend disponible sur : http://localhost:8000  
Documentation API interactive : http://localhost:8000/docs

---

## 4. Lancer le frontend

Dans un **nouveau terminal** :

```bash
cd frontend

# Installer les dépendances
npm install

# Lancer le serveur de développement
npm run dev
```

Frontend disponible sur : http://localhost:5173

> En mode dev, Vite proxifie automatiquement `/api/*` vers `http://localhost:8000`  
> (configuré dans `frontend/vite.config.js`)

---

## 5. Vérifier que tout fonctionne

```bash
# Health check backend
curl http://localhost:8000/health
# → {"status": "ok", "app": "Civitech GoV Gen Z Madagascar"}

# Stats publiques
curl http://localhost:8000/public/stats
# → {"citizens": ..., "ambassadors": ..., ...}
```

Ouvre http://localhost:5173 dans le navigateur — tu dois voir la page d'accueil Civitech.

---

## 6. Comptes de test

> Les comptes de test sont créés automatiquement au démarrage via `backend/app/seed.py`

| Email | Rôle | Usage |
|---|---|---|
| `admin@civitech.genzgov.org` | admin | Accès complet |
| *(voir .env pour le mot de passe)* | | |

---

## Structure du projet

```
civitech-govgenz/
│
├── backend/                    # API FastAPI (Python)
│   ├── app/
│   │   ├── main.py             # Point d'entrée, CORS, routes
│   │   ├── config.py           # Variables d'env (pydantic-settings)
│   │   ├── database.py         # Connexion MySQL, pool SQLAlchemy
│   │   ├── models/             # Modèles SQLAlchemy (tables DB)
│   │   ├── routers/            # Endpoints API par domaine
│   │   ├── services/           # Logique métier (auth, AI...)
│   │   └── utils/              # Helpers (security, etc.)
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # Application React (Vite)
│   ├── src/
│   │   ├── App.jsx             # Routes React Router
│   │   ├── api/client.js       # Tous les appels API (Axios)
│   │   ├── contexts/           # AuthContext (état utilisateur global)
│   │   ├── components/         # Composants réutilisables
│   │   │   ├── Layout/         # Sidebar, PublicHeader
│   │   │   └── ui/             # Badges, ScoreBar, etc.
│   │   └── pages/
│   │       ├── public/         # Pages sans connexion
│   │       ├── auth/           # Login, Register
│   │       ├── citizen/        # Dashboard, Profil, Alertes...
│   │       └── admin/          # Gestion (Observatoire, Users, etc.)
│   ├── package.json
│   └── Dockerfile
│
├── nginx/
│   ├── nginx.conf              # Config production (avec SSL)
│   └── nginx.dev.conf          # Config développement (port 80 seulement)
│
├── docs/                       # Documentation technique
├── docker-compose.yml          # Production
├── docker-compose.dev.yml      # Développement local
├── .env.example                # Template variables d'environnement
└── .gitignore
```

---

## Dépannage fréquent

### "Module not found" au démarrage backend
```bash
# Vérifier que le venv est activé
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```

### "CORS error" dans le navigateur
```bash
# Vérifier que CORS_ORIGINS dans .env contient bien http://localhost:5173
```

### "Connection refused" sur la DB
```bash
# Vérifier les valeurs DB_HOST, DB_USER, DB_PASSWORD dans .env
# La DB est distante — vérifier la connexion internet
```

### Port 8000 déjà utilisé
```bash
lsof -ti :8000 | xargs kill -9
uvicorn app.main:app --reload
```
