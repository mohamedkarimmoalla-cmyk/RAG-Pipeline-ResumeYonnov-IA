# Yonnov'IA — configuration de déploiement (Team07-E26)

Ce dossier contient la configuration de déploiement du projet Yonnov'IA : les fichiers d'environnement et les fichiers Docker, tels qu'utilisés par le backend et le frontend. Le code applicatif lui-même (backend FastAPI, frontend React, migrations Alembic) n'est pas dans ce dossier.

## Contenu

| Fichier ici | Destination réelle dans le projet |
|---|---|
| `backend.env.example` | `backend/.env.example` (à renommer `.env`) |
| `backend.Dockerfile` | `backend/Dockerfile` |
| `backend.dockerignore` | `backend/.dockerignore` |
| `frontend.env.example` | `frontend/.env.example` (à renommer `.env`) |
| `frontend.Dockerfile` | `frontend/Dockerfile` |
| `frontend.docker-compose.yml` | `frontend/docker-compose.yml` |
| `frontend.nginx.default.conf` | `frontend/nginx/default.conf` |

Aucun fichier `.env` réel n'est inclus — uniquement les `.env.example` à compléter.

## Variables liées à l'instance commune

| Variable | Fichier | Détail |
|---|---|---|
| `DATABASE_URL` | backend | URL de connexion PostgreSQL (`postgresql://user:pass@host:port/db`). Obligatoire — le backend ne démarre pas sans elle. |
| `CORS_ORIGINS` | backend | URL(s) publique(s) du frontend déployé. |
| `OLLAMA_HOST` | backend | Adresse du serveur Ollama si celui-ci n'est pas sur `localhost` par rapport au backend. |
| `VITE_API_BASE_URL` | frontend | URL publique du backend. Injectée au moment du build Docker du frontend, pas modifiable au runtime. |

## Dépendance externe : Ollama

Le pipeline appelle un serveur Ollama local pour générer les résumés :
- Ollama doit être joignable à l'adresse renseignée dans `OLLAMA_HOST`.
- Modèle `qwen2.5:3b` pré-téléchargé (obligatoire, utilisé pour chaque résumé).
- Modèle `qwen2.5vl:7b` nécessaire uniquement si `ENABLE_LLM_JUDGE=true` (désactivé par défaut).

## Base de données

Les migrations sont pilotées par variable d'environnement (aucune URL en dur dans le code). Une fois `DATABASE_URL` renseignée, depuis le dossier `backend/` :

```
alembic upgrade head
```

Driver requis : PostgreSQL (`psycopg2-binary`, pas de support SQLite en production).

## Docker

- Le frontend dispose d'un `Dockerfile` et d'un `docker-compose.yml` prêts à l'emploi (build Nginx, port par défaut 8080 → 80).
- Le backend dispose désormais d'un `Dockerfile` (`backend/Dockerfile`, image `python:3.12-slim`, expose le port 8000, healthcheck sur `/health`). Build : `docker build -t yonnovia-backend backend/`. Alternative sans conteneur : `python run.py` depuis `backend/`.

## CORS et CSP à synchroniser

L'URL du frontend doit être mise à jour à la fois dans `CORS_ORIGINS` (backend) et dans la CSP `connect-src` codée en dur dans `frontend/nginx/default.conf`. Mettre à jour un seul des deux casse les appels API du frontend déployé.

## Ports par défaut

| Service | Port |
|---|---|
| Backend (API) | 8000 |
| Frontend (build Docker/Nginx) | 8080 → 80 dans le conteneur |
| Frontend (dev, Vite) | 5173 |

## Secrets

Aucune clé API, token ou secret n'est utilisé ou stocké dans le code de ce projet.

## Serveur cible (Xeon E-2386G, 32 Go ECC, 2×512 Go NVMe Soft RAID)

- Pas de GPU : l'inférence Ollama tourne en CPU. `ENABLE_LLM_JUDGE=false` recommandé sur ce serveur (le modèle juge `qwen2.5vl:7b` serait sensiblement plus lent sans GPU).
- RAM largement suffisante pour `qwen2.5:3b` + Postgres + backend/frontend.
- Niveau de RAID à préciser : RAID1 (redondance, ~512 Go utilisables) vs RAID0 (~1 To utilisables, aucune tolérance de panne). Ce serveur héberge à la fois la base de données et les fichiers uploadés/générés.
- Le backend démarre en un seul worker Uvicorn (pas de Gunicorn ni de `--workers`) : les traitements de plusieurs utilisateurs simultanés seront traités en série côté Ollama plutôt qu'en parallèle.
