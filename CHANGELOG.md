# Changelog — Civitech GoV Gen Z Madagascar

Toutes les modifications notables sont documentées ici.  
Format : [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

---

## [1.2.0] — 2026-06-08

### Ajouté
- **Réactions** 👍/👎 sur faits, alertes et threads — toggle, optimistic update, désactivé si non connecté (`ReactionBar.jsx`, `reactions.py`, table `reactions`)
- **Upload fichiers B2** : avatars (crop 400×400), images (resize 1920px), documents PDF/Word via `POST /upload/*` — service `storage.py` + `MediaUploader.jsx`
- **Carousel images/vidéos** : `ImageCarousel.jsx` détecte YouTube, Vimeo, MP4, images — champ `images` (JSON) sur Fact, Thread, Alert
- **Photo de profil** : overlay caméra dans ProfilePage, upload direct vers B2
- **MediaUploader admin** : formulaires FactForm, ThreadForm et AlertCreateForm avec upload images/vidéos
- **Création d'alerte admin** : bouton "Créer" dans AlertsAdmin, publication directe sans workflow citoyen
- **Alertes publiques** : page `/alertes` avec filtres (sévérité, secteur, recherche) + `ReactionBar`
- **Réseaux sociaux** : Instagram, TikTok, YouTube, LinkedIn, govgenz.org configurables en admin — footer dynamique
- **SiteSettings CMS** : sauvegarde par section dans l'admin, bannière cookie configurable
- **Proxy média B2** : `GET /api/media/{key}` génère une presigned URL (1h) pour bucket privé — `router/media.py`
- **Sidebar collapsible** : bouton toggle, état persisté en localStorage, icônes seules en mode réduit
- **Données de démonstration** : seed avec 17 utilisateurs, entités, faits, threads, alertes, consultations Madagascar-cohérents
- **Ambassadeurs** : affichage nom/avatar corrigé, `verify_code` visible dans le profil si statut actif
- **Superadmin** : accès complet à tous les champs utilisateur via `GET /admin/users/{id}`

### Corrigé
- **B2 images 401** : migration des URLs directes B2 vers le proxy `/api/media/`
- **Alertes page publique** : route `/alertes` manquante dans App.jsx
- **Ambassadeurs "Sans nom"** : join User dans `list_ambassadors`
- **Variables B2** dans `.env` racine (pas `backend/.env`) — docker-compose lit la racine
- **Cookie consent** : `activateGA()` appelé directement si `cookie_consent_required=false`

---

## [1.1.0] — 2026-06-08

### Ajouté
- **Threads admin** : gestion complète des threads avec expand/collapse
- **Fact linking** : lier/délier des faits à un thread depuis l'admin
- **Auto-scoring** : calcul automatique gravité/suspicion depuis les faits liés
- **ThreadForm** : champs scoring (gravité, suspicion), statut de vérification, is_published
- **Hiérarchie utilisateurs** : admin > modérateur > z-ambassador > z-citizen
- **Création de profils** : chaque rôle peut créer des profils en dessous de lui
- **Audit logs** : traçabilité de toutes les actions admin avec acteur, rôle, action, cible
- **Faits soumis** : ambassadeurs voient leurs faits soumis dans leur profil
- **Référés** : ambassadeurs voient leurs citoyens référés
- **Consultations admin** : page de gestion complète avec résultats visuels (graphiques)
- **Page Collecte** : formulaire de soumission de faits pour ambassadeurs
- **Endpoint** `GET /facts/my/submitted` — faits soumis par l'utilisateur
- **Endpoint** `POST /admin/users` — créer un utilisateur avec vérification hiérarchique
- **Endpoint** `DELETE /admin/users/{id}` — désactivation soft (is_active=False)
- **Endpoint** `GET /admin/users/{id}/referred` — utilisateurs référés
- **Endpoint** `GET /consultations/admin/all` — liste admin avec stats agrégées
- **Endpoint** `GET /consultations/{id}/results` — résultats par question
- **Colonne** `invited_by` sur la table `users` (traçabilité référencement)
- **Docker Compose** : fichier dev séparé, nginx.dev.conf sans SSL
- **GitHub** : repo privé créé, premier push, workflow de déploiement

### Amélioré
- **Performance DB** : élimination des N+1 sur `/facts/`, `/threads/`, `/audit-logs/`, `/consultations/`
- **Pool connexions** : `pool_pre_ping=False`, `pool_recycle=600` → -170ms par requête
- **Auth** : suppression du `db.commit()` sur `last_login` → -170ms par requête authentifiée
- **Sidebar** : lien Consultations corrigé (`/admin/consultations`)
- **DashboardPage** : lien "Soumettre un fait" corrigé (`/dashboard/collecte`)

### Corrigé
- **ProfilePage.jsx** : erreur de syntaxe JSX ligne 113 (parenthèse manquante dans `.map()`)
- **Engine connect listener** : suppression du listener qui causait `InvalidRequestError` au démarrage
- **Stats grid** : ternaire React mal parenthésé dans ProfilePage

---

## [1.0.0] — 2026-06-05

### Ajouté (version initiale)
- Architecture complète FastAPI + React + MySQL + Docker + Nginx
- Module Observatoire : entités, faits, threads avec scoring éditorial
- Module Transparence : vérification des faits (version officielle vs dessous iceberg)
- Module Consultations : sondages avec 6 types de questions
- Module Alertes citoyennes
- Module Ambassadeurs : candidature, QR code, vérification
- Module IA : configuration de fournisseurs, insights, import de faits
- Système d'authentification JWT avec 4 niveaux de rôles
- Interface admin complète (dashboard, observatoire, consultations, alertes, IA)
- Interface citoyenne (dashboard adaptatif selon le rôle)
- Pages publiques (accueil, faits, threads, entités, vérification)
- Thème clair/sombre
- 69 routes API documentées via Swagger
- Seed automatique au démarrage (admin + données de base)

---

## À venir

- `feature/google-analytics` — Tracking visiteurs et insights comportementaux
- `feature/redis-cache` — Cache en mémoire pour réduire la latence DB distante
- `feature/backup-auto` — Backup automatique nightly de la base MySQL
- `feature/ssl-auto` — Renouvellement automatique certificat Let's Encrypt
- `feature/github-actions` — Déploiement automatique sur git push
