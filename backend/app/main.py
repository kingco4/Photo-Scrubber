from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import pytesseract
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image


app = FastAPI(title="Scubber API", version="0.1.0")

# Allow local dev frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Utilities ---


def _pil_to_bgr(pil_img: Image.Image) -> np.ndarray:
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    arr = np.array(pil_img)  # RGB
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _bgr_to_png_bytes(bgr: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError("Failed to encode image as PNG.")
    return buf.tobytes()


def _blur_region(bgr: np.ndarray, x: int, y: int, w: int, h: int, k: int) -> None:
    # clamp
    H, W = bgr.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(W, x + w), min(H, y + h)
    if x2 <= x1 or y2 <= y1:
        return
    roi = bgr[y1:y2, x1:x2]
    # kernel size must be odd and >= 3
    k = max(3, int(k) | 1)
    bgr[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (k, k), 0)


@dataclass
class Options:
    blur_people: bool
    remove_text: bool
    blur_strength: int
    # whether to prefer full-body detector (slower) in addition to face detection
    detect_bodies: bool


# --- Scrubbers ---


def scrub_text(bgr: np.ndarray) -> np.ndarray:
    """Detect text with Tesseract and inpaint it."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # Tesseract works best on slightly processed images
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 7, 50, 50)
    # Keep original RGB for OCR (better on color sometimes)
    data = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT)

    mask = np.zeros(gray.shape, dtype=np.uint8)

    n = len(data.get("text", []))
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        conf_str = data.get("conf", ["-1"])[i]
        try:
            conf = float(conf_str)
        except Exception:
            conf = -1.0

        # Filter: real text + decent confidence
        if not txt or conf < 60:
            continue

        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        # expand a little to avoid leaving halos
        pad = max(2, int(min(w, h) * 0.15))
        x2 = max(0, x - pad)
        y2 = max(0, y - pad)
        w2 = min(mask.shape[1] - x2, w + 2 * pad)
        h2 = min(mask.shape[0] - y2, h + 2 * pad)
        cv2.rectangle(mask, (x2, y2), (x2 + w2, y2 + h2), 255, thickness=-1)

    if mask.max() == 0:
        return bgr

    # Inpaint using Telea method
    inpainted = cv2.inpaint(bgr, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    return inpainted


def scrub_people(bgr: np.ndarray, blur_strength: int, detect_bodies: bool) -> np.ndarray:
    """Blur likely background people. Uses face detection (fast) and optional HOG person detector."""
    out = bgr.copy()

    # Face detector (Haar cascade)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
    for (x, y, w, h) in faces:
        # expand slightly to cover hair/edges
        pad = int(0.25 * w)
        _blur_region(out, x - pad, y - pad, w + 2 * pad, h + 2 * pad, blur_strength)

    if detect_bodies:
        # HOG person detector (slower, but good enough for simple cases)
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        # Downscale for speed
        scale = 0.75 if max(out.shape[:2]) > 900 else 1.0
        small = cv2.resize(out, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale != 1.0 else out
        rects, weights = hog.detectMultiScale(small, winStride=(8, 8), padding=(8, 8), scale=1.05)

        for (x, y, w, h), wt in zip(rects, weights):
            if wt < 0.5:
                continue
            # map back to original coords
            if scale != 1.0:
                x, y, w, h = int(x / scale), int(y / scale), int(w / scale), int(h / scale)
            _blur_region(out, x, y, w, h, blur_strength)

    return out


def process_image(pil_img: Image.Image, opts: Options) -> np.ndarray:
    bgr = _pil_to_bgr(pil_img)

    if opts.remove_text:
        bgr = scrub_text(bgr)

    if opts.blur_people:
        bgr = scrub_people(bgr, blur_strength=opts.blur_strength, detect_bodies=opts.detect_bodies)

    return bgr


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    blur_people: bool = Form(True),
    remove_text: bool = Form(True),
    blur_strength: int = Form(31),
    detect_bodies: bool = Form(False),
):
    # Basic validation
    blur_strength = int(blur_strength)
    blur_strength = max(3, min(151, blur_strength))

    raw = await file.read()
    pil = Image.open(io.BytesIO(raw))

    opts = Options(
        blur_people=bool(blur_people),
        remove_text=bool(remove_text),
        blur_strength=blur_strength,
        detect_bodies=bool(detect_bodies),
    )

    out_bgr = process_image(pil, opts)
    png = _bgr_to_png_bytes(out_bgr)
    return Response(content=png, media_type="image/png")
