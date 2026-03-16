from __future__ import annotations

import io
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from .aging_engine import AgingEngine, build_ages, ensure_dir
from .schemas import GeneratedImage, GenerationResponse

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOADS_DIR = ensure_dir(BASE_DIR / "uploads")
OUTPUTS_DIR = ensure_dir(BASE_DIR / "outputs")
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = AgingEngine()
    yield


app = FastAPI(title="Face Aging Simulator", version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")
if FRONTEND_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate", response_model=GenerationResponse)
async def generate(
    image: UploadFile = File(...),
    current_age: int = Form(...),
):
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Only JPG and PNG files are supported.")

    if current_age < 0 or current_age > 60:
        raise HTTPException(status_code=400, detail="Current age must be between 0 and 60.")

    data = await image.read()
    try:
        original = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Invalid image: {ex}") from ex

    job_id = str(uuid.uuid4())
    job_upload_dir = ensure_dir(UPLOADS_DIR / job_id)
    job_output_dir = ensure_dir(OUTPUTS_DIR / job_id)

    src_ext = ".jpg" if image.content_type == "image/jpeg" else ".png"
    src_path = job_upload_dir / f"source{src_ext}"
    with src_path.open("wb") as fp:
        fp.write(data)

    ages = build_ages(current_age)
    generated: list[GeneratedImage] = []
    engine: AgingEngine = app.state.engine

    for target_age in ages:
        out = engine.age_face(original, current_age, target_age)
        filename = f"age_{target_age}.png"
        output_path = job_output_dir / filename
        out.save(output_path, format="PNG", optimize=True)
        generated.append(
            GeneratedImage(
                age=target_age,
                url=f"/outputs/{job_id}/{filename}",
                filename=filename,
            )
        )

    zip_filename = f"{job_id}.zip"
    zip_path = OUTPUTS_DIR / zip_filename
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zipf:
        for item in generated:
            file_path = job_output_dir / item.filename
            zipf.write(file_path, arcname=item.filename)

    return GenerationResponse(
        source_age=current_age,
        ages=ages,
        images=generated,
        zip_url=f"/api/download/{zip_filename}",
    )


@app.get("/api/download/{zip_name}")
def download_zip(zip_name: str):
    path = OUTPUTS_DIR / zip_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="ZIP not found")
    return FileResponse(path, media_type="application/zip", filename=zip_name)


@app.delete("/api/job/{job_id}")
def cleanup(job_id: str):
    for root in (UPLOADS_DIR, OUTPUTS_DIR):
        path = root / job_id
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    zip_path = OUTPUTS_DIR / f"{job_id}.zip"
    if zip_path.exists():
        zip_path.unlink()
    return {"deleted": job_id}
