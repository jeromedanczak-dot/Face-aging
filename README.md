# Face Aging AI

Face Aging AI is a full-stack local web application for portrait-based facial age progression.

## Features

- Drag-and-drop JPG/PNG upload.
- Current age input.
- Automatic face detection, crop, and alignment (MTCNN, with safe fallback).
- AI-inspired age progression pipeline with identity-preserving transforms every 3 years up to age 60.
- 1024x1024 generated outputs.
- Gallery results with per-image download.
- Download all generated images as ZIP.

## Project Structure

- `frontend/` React + TailwindCSS UI
- `backend/` FastAPI API server
- `ai/` aging pipeline and face preprocessing
- `uploads/` input files grouped by run
- `outputs/` generated files grouped by run

## Backend Setup

```bash
pip install -r requirements.txt
python backend/main.py
```

Backend URL: `http://localhost:8000`

## Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend URL: `http://localhost:3000`

If needed, set API URL:

```bash
REACT_APP_API_URL=http://localhost:8000 npm start
```

## API

### `POST /generate`

Form data:
- `image`: JPG/PNG
- `current_age`: integer between 0 and 60

Returns:
- `images`: age-labeled URLs
- `zip_url`: batch ZIP output URL

### `GET /download/{run_id}/{filename}`

Downloads a generated image.

## Notes

- GPU acceleration is used automatically when available in `torch`.
- The age progression engine is implemented as a modular pipeline so advanced latent/diffusion models can be plugged in later without changing API/UI.
