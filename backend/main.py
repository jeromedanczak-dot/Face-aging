from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import List
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai.aging_pipeline import FaceAgingPipeline

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

app = FastAPI(title="Face Aging AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = FaceAgingPipeline()

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


class GeneratedImage(BaseModel):
    age: int
    url: str
    filename: str


class GenerateResponse(BaseModel):
    run_id: str
    images: List[GeneratedImage]
    zip_url: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
async def generate(image: UploadFile = File(...), current_age: int = Form(...)) -> GenerateResponse:
    if current_age < 0 or current_age > 60:
        raise HTTPException(status_code=400, detail="current_age must be between 0 and 60")

    if image.content_type not in {"image/jpeg", "image/jpg", "image/png"}:
        raise HTTPException(status_code=400, detail="Only JPG and PNG files are supported")

    run_id = str(uuid.uuid4())
    run_upload_dir = UPLOAD_DIR / run_id
    run_output_dir = OUTPUT_DIR / run_id
    run_upload_dir.mkdir(parents=True, exist_ok=True)
    run_output_dir.mkdir(parents=True, exist_ok=True)

    suffix = ".png" if image.content_type == "image/png" else ".jpg"
    input_path = run_upload_dir / f"input{suffix}"

    with input_path.open("wb") as f:
        shutil.copyfileobj(image.file, f)

    results = pipeline.run(input_path, current_age=current_age, output_dir=run_output_dir)

    generated = [
        GeneratedImage(
            age=item.age,
            url=f"/outputs/{run_id}/{item.image_path.name}",
            filename=item.image_path.name,
        )
        for item in results
    ]

    zip_path = run_output_dir / "all_images.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for result in results:
            zf.write(result.image_path, arcname=result.image_path.name)

    return GenerateResponse(
        run_id=run_id,
        images=generated,
        zip_url=f"/outputs/{run_id}/{zip_path.name}",
    )


@app.get("/download/{run_id}/{filename}")
def download(run_id: str, filename: str) -> FileResponse:
    file_path = OUTPUT_DIR / run_id / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
