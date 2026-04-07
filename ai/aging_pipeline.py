from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image

try:
    from facenet_pytorch import InceptionResnetV1, MTCNN
    import torch
except Exception:  # pragma: no cover - optional dependency fallback
    MTCNN = None
    InceptionResnetV1 = None
    torch = None


@dataclass
class AgeResult:
    age: int
    image_path: Path


class FaceAgingPipeline:
    """
    End-to-end age progression pipeline.

    Pipeline stages:
    1) face detection
    2) alignment (MTCNN landmarks)
    3) normalization to 512x512
    4) identity embedding extraction
    5) latent encoding (simulated)
    6) age direction manipulation
    7) reconstruction to 1024x1024
    """

    def __init__(self, device: str = "cpu") -> None:
        self.device = device
        self.mtcnn = None
        self.id_model = None

        if MTCNN is not None and torch is not None:
            selected_device = device if (device == "cpu" or torch.cuda.is_available()) else "cpu"
            self.mtcnn = MTCNN(keep_all=False, device=selected_device)
            self.id_model = InceptionResnetV1(pretrained="vggface2").eval().to(selected_device)
            self.device = selected_device

    def detect_and_align(self, image: Image.Image) -> Image.Image:
        if self.mtcnn is None:
            # Fallback: center crop if MTCNN is unavailable.
            arr = np.array(image.convert("RGB"))
            h, w, _ = arr.shape
            size = min(h, w)
            y0 = (h - size) // 2
            x0 = (w - size) // 2
            return Image.fromarray(arr[y0 : y0 + size, x0 : x0 + size])

        boxes, _ = self.mtcnn.detect(image)
        arr = np.array(image.convert("RGB"))

        if boxes is None or len(boxes) == 0:
            h, w, _ = arr.shape
            size = min(h, w)
            y0 = (h - size) // 2
            x0 = (w - size) // 2
            return Image.fromarray(arr[y0 : y0 + size, x0 : x0 + size])

        x1, y1, x2, y2 = boxes[0]
        h, w, _ = arr.shape
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        bw = (x2 - x1) * 1.5
        bh = (y2 - y1) * 1.7

        nx1 = int(max(0, cx - bw / 2))
        ny1 = int(max(0, cy - bh / 2))
        nx2 = int(min(w, cx + bw / 2))
        ny2 = int(min(h, cy + bh / 2))

        face = arr[ny1:ny2, nx1:nx2]
        return Image.fromarray(face)

    def normalize(self, image: Image.Image, size: int = 512) -> Image.Image:
        return image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)

    def extract_identity_embedding(self, image: Image.Image) -> np.ndarray:
        if self.id_model is None or torch is None:
            arr = np.array(image.resize((64, 64), Image.Resampling.BILINEAR), dtype=np.float32)
            return arr.mean(axis=(0, 1))

        tensor = self.mtcnn(image)
        if tensor is None:
            arr = np.array(image.resize((64, 64), Image.Resampling.BILINEAR), dtype=np.float32)
            return arr.mean(axis=(0, 1))

        with torch.no_grad():
            emb = self.id_model(tensor.unsqueeze(0).to(self.device)).cpu().numpy()[0]
        return emb

    def latent_encode(self, image: Image.Image, embedding: np.ndarray) -> Dict[str, np.ndarray]:
        arr = np.array(image, dtype=np.float32) / 255.0
        return {
            "image": arr,
            "identity": embedding.astype(np.float32),
        }

    def apply_age_direction(self, latent: Dict[str, np.ndarray], current_age: int, target_age: int) -> np.ndarray:
        img = (latent["image"] * 255.0).astype(np.uint8)
        age_gap = max(0, target_age - current_age)

        # Skin tone and contrast shifts
        lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.addWeighted(l, 1.0 - min(0.25, age_gap * 0.01), np.zeros_like(l), 0, 0)
        b = cv2.addWeighted(b, 1.0 + min(0.12, age_gap * 0.005), np.zeros_like(b), 0, 0)
        aged = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)

        # Wrinkle-like high-frequency structure
        gray = cv2.cvtColor(aged, cv2.COLOR_RGB2GRAY)
        wrinkle_strength = min(0.35, age_gap * 0.01)
        detail = cv2.Laplacian(gray, cv2.CV_8U, ksize=3)
        detail = cv2.cvtColor(detail, cv2.COLOR_GRAY2RGB)
        aged = cv2.addWeighted(aged, 1.0, detail, wrinkle_strength, 0)

        # Slight sagging simulation with vertical warp
        h, w, _ = aged.shape
        map_y, map_x = np.indices((h, w), dtype=np.float32)
        sag = min(8.0, age_gap * 0.2)
        map_y = map_y - (np.sin((map_x / w) * np.pi) * sag)
        aged = cv2.remap(aged, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        # Hair graying approximation (upper region desaturation)
        upper = aged[: h // 4, :, :].astype(np.float32)
        gray_mix = cv2.cvtColor(upper.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        gray_mix = np.stack([gray_mix, gray_mix, gray_mix], axis=2).astype(np.float32)
        mix_ratio = min(0.5, age_gap * 0.015)
        aged[: h // 4, :, :] = np.clip(upper * (1 - mix_ratio) + gray_mix * mix_ratio, 0, 255).astype(np.uint8)

        # Preserve identity by blending with source latent image
        source = (latent["image"] * 255.0).astype(np.uint8)
        alpha = min(0.45, 0.15 + age_gap * 0.005)
        aged = cv2.addWeighted(aged, 1.0 - alpha, source, alpha, 0)

        return aged

    def reconstruct(self, aged_arr: np.ndarray, final_size: int = 1024) -> Image.Image:
        return Image.fromarray(aged_arr).resize((final_size, final_size), Image.Resampling.LANCZOS)

    def generate_age_targets(self, current_age: int, max_age: int = 60) -> List[int]:
        if current_age >= max_age:
            return [max_age]

        ages = list(range(current_age + 3, max_age + 1, 3))
        if ages and ages[-1] != max_age:
            ages.append(max_age)
        elif not ages:
            ages = [max_age]
        return ages

    def run(self, image_path: Path, current_age: int, output_dir: Path) -> List[AgeResult]:
        output_dir.mkdir(parents=True, exist_ok=True)
        source = Image.open(image_path).convert("RGB")
        aligned = self.detect_and_align(source)
        normalized = self.normalize(aligned, 512)
        embedding = self.extract_identity_embedding(normalized)
        latent = self.latent_encode(normalized, embedding)

        results: List[AgeResult] = []
        for age in self.generate_age_targets(current_age=current_age, max_age=60):
            aged_arr = self.apply_age_direction(latent, current_age=current_age, target_age=age)
            reconstructed = self.reconstruct(aged_arr, 1024)
            out_path = output_dir / f"age_{age}.png"
            reconstructed.save(out_path, format="PNG", optimize=True)
            results.append(AgeResult(age=age, image_path=out_path))

        return results
