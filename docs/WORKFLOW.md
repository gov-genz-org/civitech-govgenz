# Workflow Git — Civitech

> Comment travailler sur ce projet sans casser la production.

---

## Branches

```
main          → production (ce qui tourne sur le VPS)
develop       → intégration (features finies, pas encore déployées)
feature/xxx   → une feature en cours de développement
hotfix/xxx    → correction urgente d'un bug en prod
```

### Règle principale

```
On ne pousse JAMAIS directement sur main
sauf pour les hotfixes critiques.
```

---

## Cycle de vie d'une feature

```bash
# 1. Partir toujours de main à jour
git checkout main
git pull

# 2. Créer une branche pour ta feature
git checkout -b feature/google-analytics
# ou
git checkout -b feature/redis-cache
# ou
git checkout -b feature/ssl-certbot

# 3. Travailler, committer au fur et à mesure
git add .
git commit -m "feat(analytics): ajout Google Analytics 4"

# 4. Pousser la branche sur GitHub
git push origin feature/google-analytics

# 5. Quand c'est prêt → merger dans main
git checkout main
git merge feature/google-analytics
git push

# 6. Déployer sur le VPS
ssh root@VPS_IP
cd /app/civitech
git pull
docker compose up --build -d

# 7. Supprimer la branche (nettoyage)
git branch -d feature/google-analytics
git push origin --delete feature/google-analytics
```

---

## Hotfix — Bug urgent en production

```bash
# 1. Partir de main (= production)
git checkout main
git pull

# 2. Créer une branche hotfix
git checkout -b hotfix/login-crash

# 3. Corriger le bug
git add .
git commit -m "fix(auth): correction crash login token expiré"

# 4. Merger dans main ET dans develop
git checkout main
git merge hotfix/login-crash
git push

git checkout develop
git merge hotfix/login-crash
git push

# 5. Déployer immédiatement
ssh root@VPS_IP "cd /app/civitech && git pull && docker compose up --build -d"

# 6. Supprimer la branche
git branch -d hotfix/login-crash
```

---

## Conventions de commits

Format : `type(scope): description courte`

| Type | Usage | Exemple |
|---|---|---|
| `feat` | Nouvelle fonctionnalité | `feat(threads): scoring auto depuis faits liés` |
| `fix` | Correction de bug | `fix(auth): token expiré ne redirige pas` |
| `perf` | Amélioration performance | `perf(db): élimination N+1 sur liste faits` |
| `refactor` | Refactoring sans bug fix | `refactor(admin): extraction composant ThreadForm` |
| `docs` | Documentation | `docs: mise à jour DEPLOY.md` |
| `chore` | Config, dépendances | `chore: mise à jour requirements.txt` |
| `style` | CSS, formatage | `style(admin): uniformisation boutons` |

**Règles :**
- Toujours en minuscules
- Pas de point final
- Description en français (projet malgache)
- Maximum 72 caractères

---

## Script de déploiement rapide

```bash
# Sur le VPS — déployer la dernière version de main
cd /app/civitech
git pull
docker compose up --build -d
docker ps  # vérifier que tout est UP
```

Ou depuis le Mac (si sshpass installé) :
```bash
./scripts/deploy.sh
```

---

## Branches en cours / roadmap

| Branche | Feature | Statut |
|---|---|---|
| `main` | Version production | ✅ Déployée |
| `feature/google-analytics` | Tracking visiteurs | 📋 Planifiée |
| `feature/redis-cache` | Cache pour DB distante | 📋 Planifiée |
| `feature/backup-auto` | Backup DB automatique | 📋 Planifiée |
| `feature/ssl-auto` | Renouvellement SSL auto | 📋 Planifiée |

---

## Que faire si on casse la prod ?

```bash
# Voir l'historique des commits
git log --oneline -10

# Revenir à un commit précédent (ex: bd2cf94)
git checkout main
git reset --hard bd2cf94
git push --force origin main

# Sur le VPS
git pull
docker compose up --build -d
```

Ou restaurer le backup v0 :
```bash
# Sur le VPS
docker compose down
rm -rf /app/civitech
cp -r /app/civitech-v0-backup /app/civitech
docker compose up --build -d
```
