# Architecture technique — Civitech

---

## Vue d'ensemble

```
Internet
    │
    ▼
┌─────────────────────────────────────────────┐
│  Nginx  (port 80 / 443)                     │
│  civitech.genzgov.org                       │
│                                             │
│  /api/*  ──────────────► Backend :8000      │
│  /*      ──────────────► Frontend :80       │
└─────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────────┐
│  FastAPI        │    │  React (fichiers      │
│  Uvicorn        │    │  statiques compilés   │
│  Python 3.11    │    │  par Vite + Nginx)    │
└────────┬────────┘    └──────────────────────┘
         │
         │ SQLAlchemy ORM
         ▼
┌─────────────────┐
│  MySQL          │
│  Serveur dédié  │
│  (distant)      │
└─────────────────┘
```

Tout tourne dans des **conteneurs Docker** reliés par un réseau interne `civitech_net`.  
La base MySQL est **hors Docker** — serveur dédié externe.

---

## Backend — FastAPI

### Organisation des fichiers

```
backend/app/
├── main.py          # App FastAPI, CORS, inclusion des routers, startup seed
├── config.py        # Settings via pydantic-settings (lit le .env)
├── database.py      # Engine SQLAlchemy, pool de connexions, get_db()
│
├── models/          # Tables de la base de données (SQLAlchemy ORM)
│   ├── user.py          # User, UserRole, invited_by (hiérarchie)
│   ├── fact.py          # Fact, FactActor, FactSource, Thread, ThreadFact
│   ├── entity.py        # Entity (politicien, institution, entreprise...)
│   ├── consultation.py  # Consultation, Question, Response
│   ├── alert.py         # Alert citoyenne
│   ├── ambassador.py    # Profil ambassadeur
│   ├── audit.py         # AuditLog (traçabilité des actions admin)
│   ├── sector.py        # Secteurs thématiques
│   └── ai_provider.py   # Configuration des fournisseurs IA
│
├── routers/         # Endpoints API (1 fichier = 1 domaine)
│   ├── auth.py          # POST /auth/login, /auth/register, /auth/me
│   ├── public.py        # GET /public/stats, /public/sectors...
│   ├── facts.py         # CRUD faits + vérification
│   ├── threads.py       # CRUD threads + gestion faits liés
│   ├── entities.py      # CRUD entités
│   ├── consultations.py # CRUD consultations + résultats
│   ├── alerts.py        # CRUD alertes citoyennes
│   ├── ambassadors.py   # Candidatures ambassadeur
│   ├── admin.py         # Users, audit logs, dashboard admin
│   └── ai.py            # Providers IA, insights, import
│
├── services/
│   ├── auth.py          # get_current_user, require_role, get_optional_user
│   └── ai_service.py    # Intégration LLM (OpenAI, Anthropic...)
│
└── utils/
    └── security.py      # hash_password, verify_password, create_token, decode_token
```

### Authentification

```
Login → JWT token (1440 min = 24h)
     → stocké dans localStorage côté client
     → envoyé dans Authorization: Bearer <token>
     → validé par get_current_user() à chaque requête protégée
```

### Hiérarchie des rôles

```python
ROLE_HIERARCHY = {
    "admin":       ["moderator", "z_ambassador", "z_citizen"],
    "moderator":   ["z_ambassador", "z_citizen"],
    "z_ambassador":["z_citizen"],
    "z_citizen":   []
}
# Un rôle ne peut créer que les rôles en dessous de lui
```

### Pool de connexions DB

```python
# database.py — optimisé pour DB distante (170ms latence)
pool_pre_ping = False   # évite +170ms par requête
pool_recycle  = 600     # recycle connexions toutes les 10min
pool_size     = 15      # connexions persistantes
max_overflow  = 10      # connexions supplémentaires en pic
```

### Pattern anti-N+1

Toujours utiliser `selectinload` / `joinedload` pour les relations, jamais de lazy-loading dans les listes :

```python
# ❌ Mauvais — 1 requête par fait (N+1)
facts = db.query(Fact).all()
for f in facts:
    print(f.sources)  # déclenche 1 requête par fait

# ✅ Bon — 2 requêtes totales
facts = db.query(Fact).options(selectinload(Fact.sources)).all()
```

---

## Frontend — React

### Organisation des pages

```
src/pages/
├── public/      # Accessibles sans compte
│   ├── HomePage.jsx         # Landing page
│   ├── FactsPage.jsx        # Liste des faits publiés
│   ├── FactDetailPage.jsx   # Détail d'un fait
│   ├── ThreadsPage.jsx      # Liste des threads
│   ├── ThreadDetailPage.jsx # Détail d'un thread
│   ├── EntitiesPage.jsx     # Liste des entités
│   ├── EntityDetailPage.jsx # Profil d'une entité
│   └── VerifyPage.jsx       # Vérification code ambassadeur
│
├── auth/
│   ├── LoginPage.jsx
│   └── RegisterPage.jsx
│
├── citizen/     # Connectés (tous rôles)
│   ├── DashboardPage.jsx         # Dashboard selon le rôle
│   ├── ProfilePage.jsx           # Profil + stats
│   ├── ConsultationsPage.jsx     # Liste consultations
│   ├── ConsultationDetailPage.jsx
│   ├── AlertsPage.jsx
│   ├── CollectePage.jsx          # Soumettre un fait (ambassadeur)
│   ├── AmbassadorApplyPage.jsx   # Candidature ambassadeur
│   └── AmbassadorLandingPage.jsx
│
└── admin/       # Modérateur et admin uniquement
    ├── AdminDashboard.jsx    # Vue d'ensemble + stats
    ├── ObservatoireAdmin.jsx # Entités, Faits, Threads
    ├── ConsultationsAdmin.jsx
    ├── AlertsAdmin.jsx
    ├── UsersAdmin.jsx        # Hiérarchie + audit logs
    ├── AmbassadorsAdmin.jsx
    └── AIAdmin.jsx
```

### Appels API centralisés

Tous les appels API sont dans **`src/api/client.js`** — jamais de `fetch`/`axios` directement dans les composants.

```javascript
// Exemple d'utilisation dans un composant
import { factsApi } from '../../api/client'

const res = await factsApi.list({ limit: 20, sector: 'mines' })
```

### Gestion de l'état global

Un seul Context : `AuthContext` — contient l'utilisateur connecté et le token JWT.  
Accès via `const { user, token, login, logout } = useAuth()`

---

## Base de données — Schéma simplifié

```
users
  └── invited_by → users.id (qui a référé cet utilisateur)

facts
  ├── fact_actors → entities (qui est impliqué)
  ├── fact_sources (preuves, liens)
  └── thread_facts → threads (à quel thread appartient ce fait)

threads
  └── thread_facts → facts (faits liés au thread)

consultations
  ├── questions
  └── responses (réponses des citoyens)

alerts
  └── soumises par users

audit_logs
  └── traçabilité de toutes les actions admin
```

---

## Scoring — Logique éditoriale

Les scores `gravity_score`, `suspicion_score`, `opacity_score` (0-10) sont :
- **Éditoriaux** : fixés manuellement par les modérateurs/admins
- **Auto-calculables** : depuis les faits liés (bouton "Auto-calculer" dans l'admin)
- **Indépendants** : un thread peut avoir un score différent de la moyenne de ses faits

Ce n'est pas algorithmique — c'est une **évaluation humaine documentée**.

---

## Sécurité

| Mécanisme | Implémentation |
|---|---|
| Mots de passe | bcrypt (coût 12) |
| Tokens JWT | python-jose, expire 24h |
| Clés API IA | Fernet (chiffrement symétrique) |
| Secrets | Uniquement dans `.env`, jamais dans le code |
| CORS | Liste blanche explicite dans `CORS_ORIGINS` |
| Rôles | Vérification backend à chaque endpoint sensible |
