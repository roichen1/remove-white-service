from __future__ import annotations

import io
import os
from collections import deque
from typing import Optional

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from PIL import Image, ImageFilter

app = FastAPI(title="Remove White Background API", version="1.0.0")


def _background_like(
    rgba: np.ndarray,
    threshold: int,
    color_tolerance: int,
) -> np.ndarray:
    """Return mask of pixels that are near-white and near-neutral."""
    rgb = rgba[..., :3].astype(np.int16)
    alpha = rgba[..., 3] > 0

    brightness = rgb.mean(axis=2)
    spread = rgb.max(axis=2) - rgb.min(axis=2)

    mask = (brightness >= threshold) & (spread <= color_tolerance) & alpha
    return mask


def _edge_connected(mask: np.ndarray) -> np.ndarray:
    """Keep only mask components connected to image borders."""
    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    def add(y: int, x: int) -> None:
        if mask[y, x] and not visited[y, x]:
            visited[y, x] = True
            q.append((y, x))

    for x in range(w):
        add(0, x)
        add(h - 1, x)
    for y in range(h):
        add(y, 0)
        add(y, w - 1)

    neighbors = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]

    while q:
        y, x = q.popleft()
        for dy, dx in neighbors:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))

    return visited


def _apply_white_dehalo(rgb: np.ndarray, alpha_01: np.ndarray) -> np.ndarray:
    """Remove white fringe by unmixing colors against a white background."""
    safe_alpha = np.clip(alpha_01, 1e-6, 1.0)[..., None]
    rgb_f = rgb.astype(np.float32)
    corrected = (rgb_f - 255.0 * (1.0 - safe_alpha)) / safe_alpha
    corrected = np.clip(corrected, 0, 255)
    corrected[alpha_01 <= 0.0] = 0
    return corrected.astype(np.uint8)


def remove_white_background(
    image_bytes: bytes,
    threshold: int = 245,
    color_tolerance: int = 18,
    edge_only: bool = True,
    feather: float = 0.8,
    dehalo: bool = True,
) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as im:
        rgba_img = im.convert("RGBA")

    rgba = np.array(rgba_img)
    candidate = _background_like(rgba, threshold=threshold, color_tolerance=color_tolerance)
    bg_mask = _edge_connected(candidate) if edge_only else candidate

    alpha = rgba[..., 3].copy()
    alpha[bg_mask] = 0

    if feather > 0:
        alpha_img = Image.fromarray(alpha, mode="L").filter(ImageFilter.GaussianBlur(radius=feather))
        alpha = np.array(alpha_img)

    rgb = rgba[..., :3]
    alpha_01 = alpha.astype(np.float32) / 255.0

    if dehalo:
        rgb = _apply_white_dehalo(rgb, alpha_01)

    out = np.dstack([rgb, alpha.astype(np.uint8)])
    out_img = Image.fromarray(out, mode="RGBA")

    buffer = io.BytesIO()
    out_img.save(buffer, format="PNG")
    return buffer.getvalue()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/")
def root() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "message": "POST a file to /remove-white as multipart/form-data",
            "example": {
                "endpoint": "/remove-white",
                "method": "POST",
                "form_fields": {
                    "file": "<binary image>",
                    "threshold": 245,
                    "color_tolerance": 18,
                    "edge_only": True,
                    "feather": 0.8,
                    "dehalo": True,
                },
            },
        }
    )


@app.post("/remove-white")
async def remove_white(
    file: UploadFile = File(...),
    threshold: int = Form(245),
    color_tolerance: int = Form(18),
    edge_only: bool = Form(True),
    feather: float = Form(0.8),
    dehalo: bool = Form(True),
) -> Response:
    if not (0 <= threshold <= 255):
        raise HTTPException(status_code=400, detail="threshold must be between 0 and 255")
    if not (0 <= color_tolerance <= 255):
        raise HTTPException(status_code=400, detail="color_tolerance must be between 0 and 255")
    if not (0 <= feather <= 20):
        raise HTTPException(status_code=400, detail="feather must be between 0 and 20")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="empty file")

    try:
        result = remove_white_background(
            image_bytes=image_bytes,
            threshold=threshold,
            color_tolerance=color_tolerance,
            edge_only=edge_only,
            feather=feather,
            dehalo=dehalo,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"processing failed: {exc}") from exc

    return Response(content=result, media_type="image/png")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
