# Documentation API — Civitech

> Documentation interactive disponible sur : https://civitech.genzgov.org/docs  
> En local : http://localhost:8000/docs

---

## Authentification

Toutes les routes protégées nécessitent un header :
```
Authorization: Bearer <JWT_TOKEN>
```

Obtenir un token :
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=email@exemple.com&password=motdepasse
```

---

## Routes publiques (sans authentification)

| Méthode | Route | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/public/stats` | Stats globales de la plateforme |
| GET | `/public/sectors` | Liste des secteurs thématiques |
| GET | `/public/consultations` | Consultations actives |
| GET | `/public/alerts` | Alertes publiées |
| GET | `/public/verify-ambassador/{code}` | Vérifier un code ambassadeur |
| GET | `/entities/` | Liste des entités |
| GET | `/entities/{slug}` | Détail d'une entité |
| GET | `/facts/` | Liste des faits publiés |
| GET | `/facts/{slug}` | Détail d'un fait |
| GET | `/threads/` | Liste des threads publiés |
| GET | `/threads/{slug}` | Détail d'un thread |

### Paramètres de pagination (GET listes)

```
?skip=0&limit=20     → pagination
?search=terme        → recherche texte
?sector=mines        → filtrer par secteur
```

---

## Routes authentifiées — Citoyen

| Méthode | Route | Description |
|---|---|---|
| GET | `/auth/me` | Profil de l'utilisateur connecté |
| GET | `/consultations/` | Liste des consultations |
| POST | `/consultations/{id}/respond` | Répondre à une consultation |
| GET | `/alerts/` | Liste des alertes |
| POST | `/alerts/` | Soumettre une alerte |
| GET | `/alerts/my-alerts` | Mes alertes |

---

## Routes authentifiées — Ambassadeur (`z_ambassador`+)

| Méthode | Route | Description |
|---|---|---|
| POST | `/facts/` | Soumettre un fait (en attente de validation) |
| GET | `/facts/my/submitted` | Mes faits soumis |
| POST | `/facts/{id}/sources` | Ajouter une source à un fait |
| GET | `/ambassadors/my-profile` | Mon profil ambassadeur |

---

## Routes authentifiées — Modérateur (`moderator`+)

| Méthode | Route | Description |
|---|---|---|
| GET | `/facts/pending` | Faits en attente de validation |
| PATCH | `/facts/{id}` | Modifier un fait |
| PATCH | `/facts/{id}/verify` | Changer le statut de vérification |
| POST | `/facts/{id}/actors` | Ajouter un acteur à un fait |
| DELETE | `/facts/{id}` | Supprimer un fait |
| GET | `/threads/pending/list` | Threads non publiés |
| POST | `/threads/` | Créer un thread |
| PATCH | `/threads/{id}` | Modifier un thread |
| POST | `/threads/{id}/facts` | Lier un fait à un thread |
| DELETE | `/threads/{id}/facts/{fact_id}` | Délier un fait |
| DELETE | `/threads/{id}` | Supprimer un thread |
| POST | `/entities/` | Créer une entité |
| PATCH | `/entities/{id}` | Modifier une entité |
| DELETE | `/entities/{id}` | Supprimer une entité |
| GET | `/admin/users` | Liste des utilisateurs |
| GET | `/admin/audit-logs` | Journal d'activité |
| POST | `/admin/users` | Créer un utilisateur |
| DELETE | `/admin/users/{id}` | Désactiver un utilisateur |

---

## Routes authentifiées — Admin uniquement

| Méthode | Route | Description |
|---|---|---|
| GET | `/admin/dashboard` | Stats admin complètes |
| GET | `/admin/users/{id}/referred` | Utilisateurs référés par un user |
| GET | `/ai/providers` | Fournisseurs IA configurés |
| POST | `/ai/providers/{name}` | Configurer un fournisseur IA |
| GET | `/ai/insights` | Générer des insights IA |

---

## Codes de statut de vérification

| Code | Signification |
|---|---|
| `unverified` | Non vérifié (défaut) |
| `in_review` | En cours d'examen |
| `verified` | Vérifié par l'équipe |
| `disputed` | Contesté / en débat |
| `false` | Démenti / faux |

---

## Exemples de requêtes

### Créer un fait (ambassadeur)

```json
POST /facts/
Authorization: Bearer <token>

{
  "title": "Signature d'un contrat minier sans appel d'offres",
  "fact_type": "transaction",
  "event_date": "2026-03-15",
  "location": "Antananarivo",
  "sector_codes": "mines,economy",
  "gravity_score": 7.5,
  "suspicion_score": 8.0,
  "opacity_score": 9.0,
  "official_version": "Contrat signé dans l'intérêt national",
  "real_version": "Pas de mise en concurrence, bénéficiaire lié au pouvoir",
  "actors": [
    {"entity_id": 12, "role": "principal"}
  ],
  "sources": [
    {
      "source_type": "document",
      "title": "Contrat publié par l'ONG Transparence",
      "url": "https://exemple.org/contrat.pdf",
      "reliability_score": 8.0
    }
  ]
}
```

### Vérifier un fait (modérateur)

```json
PATCH /facts/42/verify
Authorization: Bearer <token>

{
  "status": "verified",
  "note": "Sources croisées avec archives officielles"
}
```
