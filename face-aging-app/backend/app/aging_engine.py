from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from facenet_pytorch import MTCNN
from PIL import Image, ImageEnhance, ImageFilter

LOGGER = logging.getLogger(__name__)


@dataclass
class AgingConfig:
    output_size: int = 1024
    face_size: int = 512
    seed: int = 1234


class AgingEngine:
    """
    Real-image aging pipeline:
    1) MTCNN face detection & alignment
    2) Optional diffusion model for age progression
    3) Identity-preserving post-processing and upscaling to 1024

    If diffusion model cannot be loaded, falls back to deterministic biological-aging filters.
    """

    def __init__(self, config: Optional[AgingConfig] = None) -> None:
        self.config = config or AgingConfig()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.mtcnn = MTCNN(keep_all=False, device=self.device)
        self.pipeline = self._load_diffusion_pipeline()

    def _load_diffusion_pipeline(self):
        model_id = os.getenv("AGING_DIFFUSION_MODEL", "timbrooks/instruct-pix2pix")
        try:
            from diffusers import StableDiffusionInstructPix2PixPipeline, EulerAncestralDiscreteScheduler

            dtype = torch.float16 if self.device == "cuda" else torch.float32
            pipe = StableDiffusionInstructPix2PixPipeline.from_pretrained(
                model_id,
                torch_dtype=dtype,
                safety_checker=None,
            )
            pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
            pipe = pipe.to(self.device)
            pipe.set_progress_bar_config(disable=True)
            LOGGER.info("Loaded diffusion pipeline: %s", model_id)
            return pipe
        except Exception as ex:
            LOGGER.warning("Could not load diffusion model, using fallback filters: %s", ex)
            return None

    def detect_and_crop_face(self, image: Image.Image) -> Image.Image:
        rgb = np.array(image.convert("RGB"))
        boxes, _ = self.mtcnn.detect(rgb)
        if boxes is None or len(boxes) == 0:
            return image.convert("RGB").resize((self.config.face_size, self.config.face_size), Image.Resampling.LANCZOS)

        x1, y1, x2, y2 = boxes[0]
        h, w = rgb.shape[:2]
        box_w, box_h = x2 - x1, y2 - y1
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        side = max(box_w, box_h) * 1.9
        left = max(int(cx - side / 2), 0)
        top = max(int(cy - side / 2), 0)
        right = min(int(cx + side / 2), w)
        bottom = min(int(cy + side / 2), h)
        cropped = image.convert("RGB").crop((left, top, right, bottom))
        return cropped.resize((self.config.face_size, self.config.face_size), Image.Resampling.LANCZOS)

    def _age_prompt(self, target_age: int) -> str:
        return (
            f"photorealistic portrait of the same person at age {target_age}, "
            "preserve identity, natural skin pores, subtle wrinkles, realistic biological aging, "
            "no cartoon, no illustration, studio portrait"
        )

    def _generate_diffusion(self, image: Image.Image, target_age: int, strength: float) -> Image.Image:
        generator = torch.Generator(device=self.device).manual_seed(self.config.seed + target_age)
        output = self.pipeline(
            prompt=self._age_prompt(target_age),
            image=image,
            num_inference_steps=30,
            image_guidance_scale=1.4,
            guidance_scale=7.0,
            generator=generator,
        ).images[0]
        return self._blend_identity(image, output, strength)

    def _blend_identity(self, source: Image.Image, aged: Image.Image, aging_strength: float) -> Image.Image:
        src = source.resize((self.config.face_size, self.config.face_size), Image.Resampling.LANCZOS)
        gen = aged.resize((self.config.face_size, self.config.face_size), Image.Resampling.LANCZOS)
        # Keep high-frequency identity traits from source while preserving age changes
        src_np = np.array(src)
        gen_np = np.array(gen)

        src_blur = cv2.GaussianBlur(src_np, (0, 0), 3)
        high = cv2.addWeighted(src_np, 1.7, src_blur, -0.7, 0)

        alpha = float(np.clip(0.35 + aging_strength * 0.4, 0.35, 0.8))
        mixed = cv2.addWeighted(gen_np, alpha, high, 1 - alpha, 0)
        return Image.fromarray(np.clip(mixed, 0, 255).astype(np.uint8))

    def _fallback_aging(self, image: Image.Image, source_age: int, target_age: int) -> Image.Image:
        factor = max((target_age - source_age) / max(1, 60 - source_age), 0)
        out = image.copy().convert("RGB")

        # Skin desaturation and tone shift
        out = ImageEnhance.Color(out).enhance(1.0 - 0.25 * factor)
        out = ImageEnhance.Contrast(out).enhance(1.0 + 0.2 * factor)
        out = ImageEnhance.Sharpness(out).enhance(1.0 + 0.8 * factor)

        # Wrinkle simulation by edge-enhanced texture overlay
        gray = out.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(radius=1.2))
        edges_np = np.array(edges, dtype=np.float32)
        wrinkles = np.clip((edges_np * (1.4 + factor)).astype(np.uint8), 0, 255)
        wrinkles_rgb = np.stack([wrinkles] * 3, axis=-1)

        base = np.array(out, dtype=np.float32)
        texture_strength = 0.08 + 0.28 * factor
        base = base * (1.0 - texture_strength) + wrinkles_rgb * texture_strength + (12 * factor)

        # Hair graying on upper region
        h, w, _ = base.shape
        yy = np.linspace(1.0, 0.0, h).reshape(h, 1, 1)
        gray_mask = np.clip((yy - 0.55) * 3.5, 0.0, 1.0) * max(0.0, (target_age - 35) / 25)
        luminance = np.mean(base, axis=2, keepdims=True)
        gray_tone = np.repeat(luminance, 3, axis=2)
        base = base * (1 - gray_mask * 0.5) + gray_tone * (gray_mask * 0.5)

        aged = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
        return aged

    def age_face(self, input_image: Image.Image, source_age: int, target_age: int) -> Image.Image:
        aligned = self.detect_and_crop_face(input_image)
        age_delta = max(target_age - source_age, 0)
        strength = min(age_delta / 40.0, 1.0)

        if self.pipeline is not None:
            try:
                aged = self._generate_diffusion(aligned, target_age, strength)
            except Exception as ex:
                LOGGER.warning("Diffusion generation failed, fallback used: %s", ex)
                aged = self._fallback_aging(aligned, source_age, target_age)
        else:
            aged = self._fallback_aging(aligned, source_age, target_age)

        return aged.resize((self.config.output_size, self.config.output_size), Image.Resampling.LANCZOS)


def build_ages(current_age: int, max_age: int = 60, step: int = 3) -> list[int]:
    ages = []
    age = current_age + step
    while age < max_age:
        ages.append(age)
        age += step
    if current_age < max_age:
        ages.append(max_age)
    return ages


def ensure_dir(path: str | Path) -> Path:
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj
