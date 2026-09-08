# YONNOVIA PDF Intelligence — Frontend

Application React connectée au backend FastAPI pour importer, traiter, afficher et télécharger les synthèses scientifiques.

## Développement

Prérequis : Node.js 22+ et npm.

```bash
npm install
npm run dev
```

L’application est disponible sur `http://localhost:5173`.
Le backend est attendu par défaut sur `http://localhost:8000`. Pour utiliser une autre URL, copiez `.env.example` vers `.env` et modifiez `VITE_API_BASE_URL`.

## Vérification

```bash
npm run lint
npm run build
npm run preview
```

## Production avec Nginx

Prérequis : Docker.

```bash
docker compose up --build -d
```

L’application est servie sur `http://localhost:8080`. Pour changer le port :

```bash
FRONTEND_PORT=8081 VITE_API_BASE_URL=http://localhost:8000 docker compose up --build -d
```

Le conteneur inclut une route de santé sur `/healthz`, la compression gzip, le cache longue durée des ressources versionnées, un fallback SPA et des en-têtes de sécurité.
