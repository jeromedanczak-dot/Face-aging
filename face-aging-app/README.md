# Face Aging Simulator

Application full-stack prête à exécuter en local et à déployer en ligne.

## Ce qui est livré

- **Frontend** React + Vite + Tailwind (upload drag & drop, preview, input âge, galerie, downloads)
- **Backend** FastAPI + PyTorch (API de génération, ZIP, cleanup)
- **Pipeline IA** MTCNN + génération d'âge (diffusion si disponible, fallback déterministe sinon)
- **Packaging** Docker + Docker Compose + script ZIP release

## Structure

```text
face-aging-app/
  frontend/
  backend/
  ai/
  uploads/
  outputs/
  Dockerfile
  docker-compose.yml
  render.yaml
  scripts_package_release.sh
```

## Lancer en local (sans Docker)

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend disponible sur `http://localhost:5173`.

## Lancer en local (Docker recommandé)

```bash
docker compose up --build
```

Puis ouvre `http://localhost:8000` (frontend servi directement par FastAPI en mode production build).

## Déploiement en ligne (Render)

Ce repo inclut déjà `render.yaml`. Tu peux déployer en quelques clics:

1. Pousser ce dossier vers ton dépôt GitHub.
2. Aller sur Render > New > Blueprint.
3. Sélectionner le repo.
4. Render détectera `render.yaml` et déploiera le service Docker.
5. Render te donnera une URL publique du type:
   - `https://face-aging-simulator.onrender.com`

## Générer une archive téléchargeable (ZIP)

```bash
./scripts_package_release.sh
```

Le ZIP est généré ici:

```text
release/face-aging-simulator-v1.1.0.zip
```

## API

### `POST /api/generate`

Form-data:
- `image`: jpg/png
- `current_age`: entier `[0, 60]`

Retourne:
- images générées tous les 3 ans jusqu'à 60
- URL de téléchargement ZIP

### `GET /api/download/{zip_name}`

Télécharge toutes les images générées dans un ZIP.

## Notes importantes

- Sortie image: **1024x1024** par tranche d’âge.
- Si le modèle diffusion n’est pas chargeable (VRAM/modèle indisponible), le moteur passe automatiquement en fallback pour assurer un résultat.
- Le GPU est utilisé automatiquement quand disponible.
