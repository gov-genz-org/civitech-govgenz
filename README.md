# Civitech — GoV Gen Z Madagascar

> Plateforme civique analytique pour collecter, vérifier et visualiser la voix des citoyens malgaches.

---

## Présentation rapide

**Civitech** permet à la société civile de documenter, structurer et rendre accessibles les faits politiques, économiques et sociaux de Madagascar — avec un système de vérification par niveaux.

```
Collecte  →  Vérification  →  Validation  →  Publication
(terrain)    (modérateur)     (admin)         (public)
```

### 4 rôles utilisateur

| Rôle | Peut faire |
|---|---|
| `z_citizen` | Consulter, voter, soumettre des alertes |
| `z_ambassador` | + Soumettre des faits, référer des citoyens |
| `moderator` | + Vérifier, publier, gérer le contenu |
| `admin` | Tout + gestion des utilisateurs et de la plateforme |

---

## Stack technique

| Couche | Technologie |
|---|---|
| Backend API | FastAPI (Python 3.11) |
| Base de données | MySQL 5.7 (serveur distant) |
| Frontend | React 18 + Vite 5 + Tailwind CSS |
| Conteneurs | Docker + Docker Compose |
| Reverse proxy | Nginx |
| Versioning | Git + GitHub (repo privé) |

---

## Documentation

| Guide | Description |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Installation et lancement en local |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture technique détaillée |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Déploiement sur le VPS |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | Branches Git, conventions, bonnes pratiques |
| [docs/CI-CD.md](docs/CI-CD.md) | Pipeline GitHub Actions, secrets, déploiement VPS |
| [docs/API.md](docs/API.md) | Routes API backend documentées |
| [CHANGELOG.md](CHANGELOG.md) | Historique des versions |

---

## Démarrage rapide (développement local)

```bash
# 1. Cloner le projet
git clone https://github.com/ELYSE-GIT/civitech-govgenz.git
cd civitech-govgenz

# 2. Configurer les variables d'environnement
cp .env.example .env
# → Édite .env avec tes vraies valeurs (voir docs/SETUP.md)

# 3. Lancer le backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 4. Lancer le frontend (autre terminal)
cd frontend
npm install
npm run dev
```

Frontend → http://localhost:5173
API docs → http://localhost:8000/docs

---

## Variables d'environnement requises

Voir [.env.example](.env.example) pour la liste complète.  
**Ne jamais commiter le fichier `.env`** — il est dans `.gitignore`.

---

## Infos importantes pour reprendre ce projet

- Les credentials (DB, VPS, secrets) sont **uniquement** dans `.env` — jamais dans le code
- Le `.env` de production est sur le VPS dans `/app/civitech/.env`
- La base de données MySQL est **externe** au VPS (serveur dédié)
- Un backup automatique de la DB tourne chaque nuit (voir [docs/DEPLOY.md](docs/DEPLOY.md))
- Toute nouvelle feature doit passer par une branche `feature/xxx` (voir [docs/WORKFLOW.md](docs/WORKFLOW.md))

---

## Liens utiles

- Repo GitHub : https://github.com/ELYSE-GIT/civitech-govgenz
- API Swagger (prod) : https://civitech.genzgov.org/docs
- Organisation : GoV Gen Z Madagascar
